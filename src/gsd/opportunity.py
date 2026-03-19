from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from gsd.data import validate_columns_exist


def parse_women_values(values: str | list[str]) -> set[str]:
    if isinstance(values, str):
        parts = [item.strip().lower() for item in values.split(",")]
    else:
        parts = [str(item).strip().lower() for item in values]

    parsed = {item for item in parts if item}
    if not parsed:
        raise ValueError("At least one women value must be provided.")

    return parsed


def infer_women_mask(gender_series: pd.Series, women_values: set[str]) -> pd.Series:
    normalized = gender_series.fillna("unknown").astype(str).str.strip().str.lower()
    return normalized.isin(women_values)


def _build_feature_pipeline(
    dataframe: pd.DataFrame,
) -> Pipeline:
    numeric_features = dataframe.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_features = [column for column in dataframe.columns if column not in numeric_features]

    transformers: list[tuple[str, Pipeline, list[str]]] = []

    if numeric_features:
        numeric_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]
        )
        transformers.append(("numeric", numeric_pipeline, numeric_features))

    if categorical_features:
        categorical_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore")),
            ]
        )
        transformers.append(("categorical", categorical_pipeline, categorical_features))

    if not transformers:
        raise ValueError("Unable to build feature transformers for the provided data.")

    return Pipeline(
        steps=[
            ("preprocessor", ColumnTransformer(transformers=transformers)),
            ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )


def _resolve_positive_class(classes: list[Any], positive_class: Any | None) -> Any:
    if positive_class is not None:
        by_string = {str(value): value for value in classes}
        if str(positive_class) not in by_string:
            available = ", ".join(str(value) for value in classes)
            raise ValueError(
                "Provided positive_class is not present in target classes. "
                f"Available classes: {available}"
            )
        return by_string[str(positive_class)]

    if len(classes) != 2:
        available = ", ".join(str(value) for value in classes)
        raise ValueError(
            "positive_class must be provided when target has more than two classes. "
            f"Available classes: {available}"
        )

    preferred = {
        "1",
        "true",
        "yes",
        "y",
        "positive",
        "success",
    }
    for value in classes:
        if str(value).strip().lower() in preferred:
            return value

    return classes[-1]


def _trend_slope_per_year(dataframe: pd.DataFrame, time_column: str) -> float:
    with_time = dataframe.copy()
    with_time["_parsed_time"] = pd.to_datetime(with_time[time_column], errors="coerce")
    with_time = with_time.dropna(subset=["_parsed_time"])

    if len(with_time) < 3 or with_time["_parsed_time"].nunique() < 2:
        return 0.0

    x_values = with_time["_parsed_time"].map(pd.Timestamp.toordinal).astype(float)
    y_values = with_time["_target_positive"].astype(float)

    slope_per_day = float(np.polyfit(x_values, y_values, 1)[0])
    return slope_per_day * 365.0


def build_predictive_opportunity_map(
    dataframe: pd.DataFrame,
    *,
    target_column: str,
    gender_column: str,
    segment_columns: list[str],
    women_values: set[str],
    time_column: str | None = None,
    min_group_size: int = 20,
    positive_class: Any | None = None,
    include_gender_feature: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not segment_columns:
        raise ValueError("At least one segment column is required.")

    required_columns = [target_column, gender_column, *segment_columns]
    if time_column:
        required_columns.append(time_column)
    validate_columns_exist(dataframe, required_columns)

    working = dataframe.dropna(subset=[target_column, gender_column]).copy()
    if working.empty:
        raise ValueError("No rows remain after dropping missing target/gender values.")

    women_mask = infer_women_mask(working[gender_column], women_values)
    women_rows = int(women_mask.sum())
    if women_rows == 0:
        raise ValueError(
            "No rows matched women_values in the gender column. "
            "Update --women-values to match your dataset labels."
        )

    excluded_columns = [target_column]
    if not include_gender_feature:
        excluded_columns.append(gender_column)

    feature_frame = working.drop(columns=excluded_columns)
    if feature_frame.shape[1] == 0:
        raise ValueError("No usable features remain after dropping configured columns.")

    model = _build_feature_pipeline(feature_frame)
    model.fit(feature_frame, working[target_column])

    classes = model.named_steps["classifier"].classes_.tolist()
    positive_value = _resolve_positive_class(classes, positive_class)
    positive_index = classes.index(positive_value)

    probabilities = model.predict_proba(feature_frame)[:, positive_index]
    target_positive = (working[target_column] == positive_value).astype(int)

    scored = working.copy()
    scored["_is_woman"] = women_mask.astype(int)
    scored["_target_positive"] = target_positive
    scored["_predicted_positive_rate"] = probabilities

    overall_grouped = scored.groupby(segment_columns, dropna=False).agg(
        n_total=(target_column, "size"),
        women_count=("_is_woman", "sum"),
    )

    women_grouped = scored[women_mask].groupby(segment_columns, dropna=False).agg(
        n_women=(target_column, "size"),
        women_positive_rate=("_target_positive", "mean"),
        predicted_positive_rate=("_predicted_positive_rate", "mean"),
    )

    opportunity = overall_grouped.join(women_grouped, how="left").fillna(
        {
            "n_women": 0,
            "women_positive_rate": 0.0,
            "predicted_positive_rate": 0.0,
        }
    )

    opportunity["n_women"] = opportunity["n_women"].astype(int)
    opportunity["women_share"] = np.where(
        opportunity["n_total"] > 0,
        opportunity["women_count"] / opportunity["n_total"],
        0.0,
    )
    opportunity["opportunity_gap"] = (
        opportunity["predicted_positive_rate"] - opportunity["women_positive_rate"]
    )

    if time_column:
        trends = (
            scored[women_mask]
            .groupby(segment_columns, dropna=False)
            .apply(lambda frame: _trend_slope_per_year(frame, time_column), include_groups=False)
            .rename("women_yearly_trend")
        )
        opportunity = opportunity.join(trends, how="left")
    else:
        opportunity["women_yearly_trend"] = 0.0

    filtered = opportunity[opportunity["n_women"] >= min_group_size].copy()
    if filtered.empty:
        raise ValueError(
            "No segments met the minimum women group size threshold. "
            "Lower --min-group-size or add more data."
        )

    gap_component = filtered["opportunity_gap"].clip(lower=0.0, upper=1.0)
    trend_component = filtered["women_yearly_trend"].fillna(0.0).clip(lower=0.0, upper=1.0)

    filtered["opportunity_score"] = (
        0.50 * filtered["predicted_positive_rate"]
        + 0.30 * gap_component
        + 0.15 * filtered["women_share"].clip(lower=0.0, upper=1.0)
        + 0.05 * trend_component
    )

    filtered = filtered.sort_values("opportunity_score", ascending=False)
    filtered["opportunity_rank"] = np.arange(1, len(filtered) + 1)

    map_frame = filtered.reset_index()

    summary = {
        "rows_total": int(len(working)),
        "women_rows": women_rows,
        "groups_after_threshold": int(len(map_frame)),
        "target_column": target_column,
        "gender_column": gender_column,
        "segment_columns": segment_columns,
        "time_column": time_column,
        "positive_class": str(positive_value),
        "min_group_size": int(min_group_size),
        "include_gender_feature": include_gender_feature,
    }

    return map_frame, summary
