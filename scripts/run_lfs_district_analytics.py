"""
Women Labor Opportunity Signals — Rwanda LFS 2022
=================================================
Builds a clean district-level women labor profile from the Rwanda Labour Force
Survey 2022 Stata file.

Usage:
    python scripts/run_lfs_district_analytics.py

Outputs:
    data/processed/lfs_2022_women_district_labor.csv
    data/processed/lfs_2022_women_district_labor_summary.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

RAW_PATH = Path("data/raw/RW_LFS2022.dta")
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV = OUT_DIR / "lfs_2022_women_district_labor.csv"
OUT_JSON = OUT_DIR / "lfs_2022_women_district_labor_summary.json"

PROVINCE_MAP = {
    "kigali city": "Kigali",
    "kigali": "Kigali",
    "eastern province": "East",
    "east": "East",
    "northern province": "North",
    "north": "North",
    "southern province": "South",
    "south": "South",
    "western province": "West",
    "west": "West",
}


def _normalize_text(value: object) -> str | None:
    if pd.isna(value):
        return None
    cleaned = " ".join(str(value).strip().split())
    return cleaned or None


def _normalize_province(value: object) -> str | None:
    cleaned = _normalize_text(value)
    if cleaned is None:
        return None
    return PROVINCE_MAP.get(cleaned.lower())


def _normalize_district(value: object) -> str | None:
    cleaned = _normalize_text(value)
    if cleaned is None:
        return None
    return cleaned.title()


def _weighted_rate(mask: pd.Series, weights: pd.Series) -> float:
    valid = mask.notna() & weights.notna()
    if not valid.any():
        return float("nan")
    weight_sum = float(weights[valid].sum())
    if weight_sum <= 0:
        return float("nan")
    return float(np.average(mask[valid].astype(float), weights=weights[valid]))


def _weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    valid = values.notna() & weights.notna()
    if not valid.any():
        return float("nan")
    weight_sum = float(weights[valid].sum())
    if weight_sum <= 0:
        return float("nan")
    return float(np.average(values[valid].astype(float), weights=weights[valid]))


def _minmax(series: pd.Series, *, invert: bool = False) -> pd.Series:
    clean = pd.to_numeric(series, errors="coerce")
    min_value = clean.min(skipna=True)
    max_value = clean.max(skipna=True)

    if pd.isna(min_value) or pd.isna(max_value) or max_value <= min_value:
        normalized = pd.Series(np.repeat(0.5, len(clean)), index=clean.index, dtype=float)
    else:
        normalized = (clean - min_value) / (max_value - min_value)

    normalized = normalized.clip(lower=0.0, upper=1.0)
    if invert:
        normalized = 1.0 - normalized
    return normalized


def _summarize_district(frame: pd.DataFrame) -> pd.Series:
    weight = frame["_weight"].copy()
    status_label = frame["_status_label"]

    status_available = status_label.notna()
    status_weight = weight[status_available]

    summary: dict[str, float | int] = {
        "lfs_n_women_16_plus": int(len(frame)),
        "lfs_weighted_women_16_plus": float(weight.sum(skipna=True)),
        "lfs_n_women_labor_rows": int(status_available.sum()),
    }

    if status_available.any() and float(status_weight.sum(skipna=True)) > 0:
        employed = status_label[status_available].eq("employed")
        unemployed = status_label[status_available].eq("unemployed")
        out_lf = status_label[status_available].eq("out of labour force")

        summary["lfs_women_employment_rate"] = _weighted_rate(employed, status_weight)
        summary["lfs_women_unemployment_rate"] = _weighted_rate(unemployed, status_weight)
        summary["lfs_women_out_of_labor_force_rate"] = _weighted_rate(out_lf, status_weight)
        summary["lfs_women_labor_force_participation_rate"] = (
            summary["lfs_women_employment_rate"] + summary["lfs_women_unemployment_rate"]
        )
    else:
        summary["lfs_women_employment_rate"] = float("nan")
        summary["lfs_women_unemployment_rate"] = float("nan")
        summary["lfs_women_out_of_labor_force_rate"] = float("nan")
        summary["lfs_women_labor_force_participation_rate"] = float("nan")

    tru_label = frame["_tru_label"]
    tru_available = tru_label.notna()
    tru_weight = weight[tru_available]
    if tru_available.any() and float(tru_weight.sum(skipna=True)) > 0:
        time_under = tru_label[tru_available].eq("time related underemployed")
        summary["lfs_women_time_underemployment_rate"] = _weighted_rate(time_under, tru_weight)
    else:
        summary["lfs_women_time_underemployment_rate"] = float("nan")

    cash = pd.to_numeric(frame["cash"], errors="coerce")
    summary["lfs_women_mean_monthly_cash_income"] = _weighted_mean(cash, weight)
    summary["lfs_women_median_monthly_cash_income"] = float(cash.dropna().median()) if cash.notna().any() else float("nan")

    usual_hours = pd.to_numeric(frame["usual_h"], errors="coerce")
    summary["lfs_women_mean_usual_hours"] = _weighted_mean(usual_hours, weight)

    return pd.Series(summary)


def _attach_risk_score(district_df: pd.DataFrame) -> pd.DataFrame:
    output = district_df.copy()

    unemployment_component = _minmax(output["lfs_women_unemployment_rate"])
    out_lf_component = _minmax(output["lfs_women_out_of_labor_force_rate"])
    underemployment_component = _minmax(output["lfs_women_time_underemployment_rate"])
    income_risk_component = _minmax(output["lfs_women_mean_monthly_cash_income"], invert=True)

    output["lfs_labor_risk_score"] = (
        0.40 * unemployment_component
        + 0.30 * out_lf_component
        + 0.20 * underemployment_component
        + 0.10 * income_risk_component
    )

    output = output.sort_values("lfs_labor_risk_score", ascending=False).reset_index(drop=True)
    output["lfs_labor_risk_rank"] = np.arange(1, len(output) + 1)
    return output


def main() -> None:
    print("Loading LFS 2022 source file...")
    source = pd.read_stata(RAW_PATH, convert_categoricals=True)

    required_columns = ["province", "code_dis", "A01", "A04", "status1", "TRU", "weight2", "cash", "usual_h"]
    missing = [column for column in required_columns if column not in source.columns]
    if missing:
        raise ValueError(f"Missing required columns in LFS source: {', '.join(missing)}")

    working = source.copy()
    working["province_name"] = working["province"].apply(_normalize_province)
    working["district_name"] = working["code_dis"].apply(_normalize_district)

    working["_sex_label"] = working["A01"].astype("string").str.strip().str.lower()
    women = working[working["_sex_label"] == "female"].copy()

    women["age_years"] = pd.to_numeric(women["A04"], errors="coerce")
    women = women[women["age_years"] >= 16].copy()

    women["_weight"] = pd.to_numeric(women["weight2"], errors="coerce")
    women["_weight"] = women["_weight"].where(women["_weight"] > 0)

    women["_status_label"] = women["status1"].astype("string").str.strip().str.lower()
    women["_status_label"] = women["_status_label"].replace({"": pd.NA})

    women["_tru_label"] = women["TRU"].astype("string").str.strip().str.lower()
    women["_tru_label"] = women["_tru_label"].replace({"": pd.NA})

    district = (
        women.dropna(subset=["province_name", "district_name"])
        .groupby(["province_name", "district_name"], dropna=False, observed=True)
        .apply(_summarize_district, include_groups=False)
        .reset_index()
    )

    district = _attach_risk_score(district)
    district = district.sort_values("lfs_labor_risk_rank").reset_index(drop=True)

    district.to_csv(OUT_CSV, index=False)

    summary = {
        "source_file": str(RAW_PATH),
        "rows_total": int(len(source)),
        "women_rows_total": int((working["_sex_label"] == "female").sum()),
        "women_rows_16_plus": int(len(women)),
        "districts": int(district["district_name"].nunique()),
        "avg_women_employment_rate": float(round(district["lfs_women_employment_rate"].mean(skipna=True), 4)),
        "avg_women_unemployment_rate": float(round(district["lfs_women_unemployment_rate"].mean(skipna=True), 4)),
        "avg_women_labor_force_participation_rate": float(
            round(district["lfs_women_labor_force_participation_rate"].mean(skipna=True), 4)
        ),
        "avg_women_mean_monthly_cash_income": float(round(district["lfs_women_mean_monthly_cash_income"].mean(skipna=True), 2)),
        "top_10_women_labor_risk_districts": district.head(10)["district_name"].tolist(),
    }

    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"District labor file saved: {OUT_CSV}")
    print(f"Summary file saved: {OUT_JSON}")
    print("Top 10 women labor-risk districts:")
    print(district.head(10)[["province_name", "district_name", "lfs_labor_risk_score", "lfs_labor_risk_rank"]].to_string(index=False))


if __name__ == "__main__":
    main()
