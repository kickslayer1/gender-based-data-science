from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from gsd.data import validate_columns_exist
from gsd.opportunity import infer_women_mask


def _resolve_location_columns(
    *,
    province_column: str | None,
    district_column: str | None,
    sector_column: str,
) -> list[str]:
    columns = [column for column in [province_column, district_column, sector_column] if column]
    if not columns:
        raise ValueError("At least one location column is required.")
    return columns


def _default_feature_columns(
    dataframe: pd.DataFrame,
    *,
    excluded_columns: list[str],
) -> list[str]:
    features = [column for column in dataframe.columns if column not in set(excluded_columns)]
    if not features:
        raise ValueError("No feature columns found for trust computation.")
    return features


def build_rwanda_sector_visibility_table(
    dataframe: pd.DataFrame,
    *,
    gender_column: str,
    women_values: set[str],
    sector_column: str,
    district_column: str | None = None,
    province_column: str | None = None,
    feature_columns: list[str] | None = None,
    target_column: str | None = None,
    min_women_count: int = 30,
    min_feature_count: int = 8,
    trust_threshold: float = 0.70,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    location_columns = _resolve_location_columns(
        province_column=province_column,
        district_column=district_column,
        sector_column=sector_column,
    )

    required_columns = [gender_column, *location_columns]
    if target_column:
        required_columns.append(target_column)
    validate_columns_exist(dataframe, required_columns)

    if min_women_count <= 0:
        raise ValueError("min_women_count must be greater than zero.")
    if min_feature_count <= 0:
        raise ValueError("min_feature_count must be greater than zero.")

    excluded_for_features = [gender_column, *location_columns]
    if target_column:
        excluded_for_features.append(target_column)

    if feature_columns is None:
        feature_columns = _default_feature_columns(
            dataframe,
            excluded_columns=excluded_for_features,
        )
    else:
        validate_columns_exist(dataframe, feature_columns)

    feature_count_total = len(feature_columns)
    if feature_count_total == 0:
        raise ValueError("At least one feature column is required.")

    working = dataframe.dropna(subset=[gender_column]).copy()
    if working.empty:
        raise ValueError("No rows remain after dropping missing gender values.")

    women_mask = infer_women_mask(working[gender_column], women_values)
    women_rows = int(women_mask.sum())
    if women_rows == 0:
        raise ValueError(
            "No rows matched women_values in the gender column. "
            "Update women values to match your labels."
        )

    working["_is_woman"] = women_mask.astype(int)

    grouped = working.groupby(location_columns, dropna=False).agg(
        n_total=(gender_column, "size"),
        women_count=("_is_woman", "sum"),
    )
    grouped["women_share"] = np.where(
        grouped["n_total"] > 0,
        grouped["women_count"] / grouped["n_total"],
        0.0,
    )

    women_only = working[women_mask].copy()
    women_only["_available_feature_count"] = women_only[feature_columns].notna().sum(axis=1)
    women_only["_feature_coverage_ratio_row"] = (
        women_only["_available_feature_count"] / float(feature_count_total)
    )

    women_grouped = women_only.groupby(location_columns, dropna=False).agg(
        n_women=(gender_column, "size"),
        avg_available_features=("_available_feature_count", "mean"),
        feature_coverage_ratio=("_feature_coverage_ratio_row", "mean"),
    )

    if target_column:
        women_grouped["women_target_rate"] = (
            women_only.groupby(location_columns, dropna=False)[target_column].mean()
        )

    visibility = grouped.join(women_grouped, how="left").fillna(
        {
            "n_women": 0,
            "avg_available_features": 0.0,
            "feature_coverage_ratio": 0.0,
        }
    )

    visibility["n_women"] = visibility["n_women"].astype(int)
    visibility["sample_trust_score"] = (
        visibility["n_women"] / float(min_women_count)
    ).clip(lower=0.0, upper=1.0)

    visibility["feature_count_trust_score"] = min(
        1.0,
        feature_count_total / float(min_feature_count),
    )
    visibility["feature_coverage_trust_score"] = visibility["feature_coverage_ratio"].clip(
        lower=0.0,
        upper=1.0,
    )

    # Weighted toward feature quality and count to emphasize data trustworthiness.
    visibility["trust_score"] = (
        0.45 * visibility["feature_coverage_trust_score"]
        + 0.25 * visibility["feature_count_trust_score"]
        + 0.30 * visibility["sample_trust_score"]
    )

    visibility["trusted"] = visibility["trust_score"] >= trust_threshold
    visibility["visibility_score"] = 0.60 * visibility["women_share"] + 0.40 * visibility["trust_score"]

    visibility = visibility.reset_index().sort_values(
        ["visibility_score", "trust_score", "n_women"],
        ascending=False,
    )

    summary = {
        "rows_total": int(len(working)),
        "women_rows": women_rows,
        "groups_total": int(len(visibility)),
        "trusted_groups": int(visibility["trusted"].sum()),
        "feature_count_total": int(feature_count_total),
        "location_columns": location_columns,
        "gender_column": gender_column,
        "target_column": target_column,
        "min_women_count": int(min_women_count),
        "min_feature_count": int(min_feature_count),
        "trust_threshold": float(trust_threshold),
        "mean_trust_score": float(visibility["trust_score"].mean()),
    }

    return visibility, summary
