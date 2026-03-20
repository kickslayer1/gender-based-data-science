import json
from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path
import re

import altair as alt
import pandas as pd
import streamlit as st

OPPORTUNITY_PATH = Path("data/processed/women_opportunity_districts.csv")
CFSVA_POLICY_PATH = Path("data/processed/cfsva_2015_district_policy_risk.csv")
OPPORTUNITY_SUMMARY_PATH = Path("data/processed/women_opportunity_summary.json")
CFSVA_POLICY_SUMMARY_PATH = Path("data/processed/cfsva_2015_district_policy_risk_summary.json")
LFS_DISTRICT_PATH = Path("data/processed/lfs_2022_women_district_labor.csv")
LFS_DISTRICT_SUMMARY_PATH = Path("data/processed/lfs_2022_women_district_labor_summary.json")
VULNERABILITY_PATH = Path("data/processed/district_vulnerability_index.csv")
VULNERABILITY_SUMMARY_PATH = Path("data/processed/district_vulnerability_index_summary.json")

UI_THEME = {
    "page_bg": "#f4efe6",
    "surface": "#fffdf8",
    "surface_alt": "#f7efe1",
    "border": "#dccfbe",
    "text": "#1f2937",
    "muted": "#5b6472",
    "accent": "#b45309",
    "accent_secondary": "#0f766e",
    "danger": "#be123c",
    "neutral": "#94a3b8",
}
PROVINCE_COLORS = {
    "Kigali": "#b45309",
    "East": "#0f766e",
    "North": "#2563eb",
    "South": "#be123c",
    "West": "#3f6212",
    "Unknown": "#64748b",
}
COMPONENT_COLORS = {
    "fi_modsev_rate": "#b45309",
    "poor_borderline_rate": "#be123c",
    "stunting_rate": "#0f766e",
    "underweight_rate": "#2563eb",
    "wasting_rate": "#64748b",
    "economic_stress_index": "#b45309",
    "nutrition_risk_index": "#be123c",
    "labor_market_risk_index": "#0f766e",
}
METRIC_LABEL_OVERRIDES = {
    "opportunity_score": "DHS gender responsive budgeting score",
    "opportunity_rank": "DHS gender responsive budgeting rank",
    "women_positive_rate": "Women poverty rate",
    "predicted_positive_rate": "Predicted poverty rate",
    "no_edu_rate": "Women no-education rate",
    "rural_share": "Rural share",
    "fi_modsev_rate": "Moderate/severe food insecurity",
    "poor_borderline_rate": "Poor/borderline food consumption",
    "stunting_rate": "Child stunting rate",
    "underweight_rate": "Child underweight rate",
    "wasting_rate": "Child wasting rate",
    "policy_priority_score": "Gender responsive budgeting score",
    "priority_rank": "Gender responsive budgeting rank",
    "local_sample_rows": "Local sample rows",
    "lfs_labor_risk_score": "Women labor risk score (LFS 2022)",
    "lfs_labor_risk_rank": "Women labor risk rank (LFS 2022)",
    "lfs_women_employment_rate": "Women employment rate (LFS)",
    "lfs_women_unemployment_rate": "Women unemployment rate (LFS)",
    "lfs_women_out_of_labor_force_rate": "Women out of labor force rate (LFS)",
    "lfs_women_labor_force_participation_rate": "Women labor-force participation (LFS)",
    "lfs_women_time_underemployment_rate": "Women time underemployment rate (LFS)",
    "lfs_women_mean_monthly_cash_income": "Women mean monthly cash income (LFS)",
    "lfs_women_median_monthly_cash_income": "Women median monthly cash income (LFS)",
    "lfs_women_mean_usual_hours": "Women usual work hours (LFS)",
    "lfs_n_women_16_plus": "Women 16+ records (LFS)",
    "lfs_weighted_women_16_plus": "Women 16+ weighted sample (LFS)",
    "lfs_n_women_labor_rows": "Women labor-status rows (LFS)",
    "vulnerability_index": "District vulnerability index",
    "vulnerability_rank": "District vulnerability rank",
    "vulnerability_tier": "Vulnerability tier",
    "economic_stress_index": "Economic stress index (DHS)",
    "nutrition_risk_index": "Nutrition risk index (CFSVA)",
    "labor_market_risk_index": "Labor-market risk index (LFS)",
    "available_domain_count": "Available domains",
    "economic_metrics_available": "Economic metrics available",
    "nutrition_metrics_available": "Nutrition metrics available",
    "labor_metrics_available": "Labor metrics available",
}
COLUMN_LABEL_OVERRIDES = {
    "province_name": "Province",
    "district_name": "District",
    "district_label": "District",
    "label": "District",
    "n_women_15_49": "Women 15-49",
    "n_mothers": "Mothers covered",
    "n_children": "Children covered",
    "local_data_present": "Local data attached",
    "lfs_n_women_16_plus": "Women 16+ records (LFS)",
    "lfs_weighted_women_16_plus": "Women 16+ weighted sample (LFS)",
    "vulnerability_rank": "Vulnerability rank",
    "vulnerability_tier": "Vulnerability tier",
    "vulnerability_index": "Vulnerability index",
    "economic_stress_index": "Economic stress index (DHS)",
    "nutrition_risk_index": "Nutrition risk index (CFSVA)",
    "labor_market_risk_index": "Labor-market risk index (LFS)",
}
ACTION_THRESHOLDS = {
    "policy_priority_score": 0.35,
    "women_positive_rate": 0.35,
    "no_edu_rate": 0.12,
    "stunting_rate": 0.35,
    "poor_borderline_rate": 0.35,
    "rural_share": 0.80,
}
ALL_FILTER_OPTION = "All"
UNDERLINE_RED_RGB = (255, 133, 151)
UNDERLINE_GREEN_RGB = (118, 222, 167)

PROVINCE_NAME_TO_CANONICAL = {
    "kigali": "Kigali",
    "kigali city": "Kigali",
    "east": "East",
    "eastern province": "East",
    "north": "North",
    "northern province": "North",
    "south": "South",
    "southern province": "South",
    "west": "West",
    "western province": "West",
}

DISTRICT_TO_PROVINCE = {
    "nyarugenge": "Kigali",
    "gasabo": "Kigali",
    "kicukiro": "Kigali",
    "nyanza": "South",
    "gisagara": "South",
    "nyaruguru": "South",
    "huye": "South",
    "nyamagabe": "South",
    "ruhango": "South",
    "muhanga": "South",
    "kamonyi": "South",
    "karongi": "West",
    "rutsiro": "West",
    "rubavu": "West",
    "nyabihu": "West",
    "ngororero": "West",
    "rusizi": "West",
    "nyamasheke": "West",
    "rulindo": "North",
    "gakenke": "North",
    "musanze": "North",
    "burera": "North",
    "gicumbi": "North",
    "rwamagana": "East",
    "nyagatare": "East",
    "gatsibo": "East",
    "kayonza": "East",
    "kirehe": "East",
    "ngoma": "East",
    "bugesera": "East",
}
CANONICAL_DISTRICT_NAMES = {name: name.title() for name in DISTRICT_TO_PROVINCE}


@st.cache_data(show_spinner=False)
def _load_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def _load_json_summary(path: str) -> dict[str, object]:
    with Path(path).open(encoding="utf-8") as source:
        return json.load(source)


def _coerce_numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    output = frame.copy()
    for column in columns:
        if column in output.columns:
            output[column] = pd.to_numeric(output[column], errors="coerce")
    return output


def _normalize_district_value(value: object) -> str | None:
    if pd.isna(value):
        return None

    cleaned = str(value).strip().lower()
    cleaned = re.sub(r"[_-]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.replace("district of ", "")
    if cleaned.endswith(" district"):
        cleaned = cleaned[:-9]

    return CANONICAL_DISTRICT_NAMES.get(cleaned)


def _normalize_province_value(value: object) -> str | None:
    if pd.isna(value):
        return None

    cleaned = " ".join(str(value).strip().split())
    if not cleaned:
        return None

    lowered = cleaned.lower()
    return PROVINCE_NAME_TO_CANONICAL.get(lowered)


def _attach_province_from_district(frame: pd.DataFrame, district_column: str) -> pd.DataFrame:
    output = frame.copy()
    province_values = (
        output[district_column]
        .apply(_normalize_district_value)
        .fillna(output[district_column])
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .map(DISTRICT_TO_PROVINCE)
        .fillna("Unknown")
    )
    output["province_name"] = province_values
    return output


@st.cache_data(show_spinner=False)
def _load_combined_baseline(opportunity_path: str, cfsva_path: str) -> pd.DataFrame:
    dhs = _coerce_numeric(
        _load_data(opportunity_path),
        [
            "n_women_15_49",
            "women_positive_rate",
            "predicted_positive_rate",
            "opportunity_score",
            "opportunity_rank",
            "no_edu_rate",
            "rural_share",
        ],
    )

    cfsva = _coerce_numeric(
        _attach_province_from_district(_load_data(cfsva_path), district_column="S0_D_Dist"),
        [
            "n_mothers",
            "fi_modsev_rate",
            "poor_borderline_rate",
            "n_children",
            "stunting_rate",
            "wasting_rate",
            "underweight_rate",
            "policy_priority_score",
            "priority_rank",
        ],
    )
    cfsva = cfsva.rename(columns={"S0_D_Dist": "district_name", "province_name": "province_name_cfsva"})

    baseline = dhs.merge(cfsva, on="district_name", how="outer", suffixes=("", "_cfsva"))
    if "province_name_cfsva" in baseline.columns:
        if "province_name" in baseline.columns:
            baseline["province_name"] = baseline["province_name"].fillna(baseline["province_name_cfsva"])
        else:
            baseline["province_name"] = baseline["province_name_cfsva"]
        baseline = baseline.drop(columns=["province_name_cfsva"])

    baseline["district_name"] = baseline["district_name"].apply(lambda value: _normalize_district_value(value) or value)
    baseline["province_name"] = baseline["province_name"].fillna(
        baseline["district_name"].astype(str).str.lower().map(DISTRICT_TO_PROVINCE)
    )

    return baseline.sort_values(["province_name", "district_name"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def _load_lfs_district_signals(path: str) -> pd.DataFrame:
    lfs = _coerce_numeric(
        _load_data(path),
        [
            "lfs_n_women_16_plus",
            "lfs_weighted_women_16_plus",
            "lfs_n_women_labor_rows",
            "lfs_women_employment_rate",
            "lfs_women_unemployment_rate",
            "lfs_women_out_of_labor_force_rate",
            "lfs_women_labor_force_participation_rate",
            "lfs_women_time_underemployment_rate",
            "lfs_women_mean_monthly_cash_income",
            "lfs_women_median_monthly_cash_income",
            "lfs_women_mean_usual_hours",
            "lfs_labor_risk_score",
            "lfs_labor_risk_rank",
        ],
    )

    if "district_name" in lfs.columns:
        lfs["district_name"] = lfs["district_name"].apply(lambda value: _normalize_district_value(value) or value)

    if "province_name" in lfs.columns:
        normalized = lfs["province_name"].apply(_normalize_province_value)
        lfs["province_name"] = normalized.fillna(
            lfs["district_name"].astype(str).str.lower().map(DISTRICT_TO_PROVINCE)
        )
    else:
        lfs["province_name"] = lfs["district_name"].astype(str).str.lower().map(DISTRICT_TO_PROVINCE)

    lfs = _collapse_lfs_rows_by_district(lfs)
    return lfs.sort_values(["province_name", "district_name"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def _load_vulnerability_index(path: str) -> pd.DataFrame:
    vulnerability = _load_data(path)
    numeric_columns = [
        "n_women_15_49",
        "n_mothers",
        "n_children",
        "women_positive_rate",
        "no_edu_rate",
        "rural_share",
        "fi_modsev_rate",
        "poor_borderline_rate",
        "stunting_rate",
        "underweight_rate",
        "wasting_rate",
        "lfs_women_unemployment_rate",
        "lfs_women_out_of_labor_force_rate",
        "lfs_women_time_underemployment_rate",
        "lfs_women_mean_monthly_cash_income",
        "economic_stress_index",
        "nutrition_risk_index",
        "labor_market_risk_index",
        "available_domain_count",
        "economic_metrics_available",
        "nutrition_metrics_available",
        "labor_metrics_available",
        "vulnerability_index",
        "vulnerability_rank",
    ]
    numeric_columns.extend(
        [column for column in vulnerability.columns if str(column).startswith("norm_")]
    )
    vulnerability = _coerce_numeric(vulnerability, numeric_columns)

    if "district_name" in vulnerability.columns:
        vulnerability["district_name"] = vulnerability["district_name"].apply(
            lambda value: _normalize_district_value(value) or value
        )

    if "province_name" in vulnerability.columns:
        normalized = vulnerability["province_name"].apply(_normalize_province_value)
        vulnerability["province_name"] = normalized.fillna(
            vulnerability["district_name"].astype(str).str.lower().map(DISTRICT_TO_PROVINCE)
        )
    else:
        vulnerability["province_name"] = vulnerability["district_name"].astype(str).str.lower().map(DISTRICT_TO_PROVINCE)

    return vulnerability.sort_values(["province_name", "district_name"]).reset_index(drop=True)


def _collapse_lfs_rows_by_district(lfs_df: pd.DataFrame) -> pd.DataFrame:
    if lfs_df.empty or "district_name" not in lfs_df.columns:
        return lfs_df

    metric_columns = [
        "lfs_n_women_16_plus",
        "lfs_weighted_women_16_plus",
        "lfs_n_women_labor_rows",
        "lfs_women_employment_rate",
        "lfs_women_unemployment_rate",
        "lfs_women_out_of_labor_force_rate",
        "lfs_women_labor_force_participation_rate",
        "lfs_women_time_underemployment_rate",
        "lfs_women_mean_monthly_cash_income",
        "lfs_women_median_monthly_cash_income",
        "lfs_women_mean_usual_hours",
        "lfs_labor_risk_score",
        "lfs_labor_risk_rank",
    ]
    available_metrics = [column for column in metric_columns if column in lfs_df.columns]
    if not available_metrics:
        return lfs_df.drop_duplicates(subset=["district_name"]).reset_index(drop=True)

    collapsed = lfs_df.copy()
    collapsed = collapsed.dropna(subset=available_metrics, how="all")
    if collapsed.empty:
        collapsed = lfs_df.copy()

    collapsed["_lfs_row_completeness"] = collapsed[available_metrics].notna().sum(axis=1)
    sort_columns = ["_lfs_row_completeness"]
    ascending = [False]
    if "lfs_n_women_16_plus" in collapsed.columns:
        sort_columns.append("lfs_n_women_16_plus")
        ascending.append(False)
    collapsed = collapsed.sort_values(sort_columns, ascending=ascending)
    collapsed = collapsed.drop_duplicates(subset=["district_name"], keep="first")
    return collapsed.drop(columns=["_lfs_row_completeness"]).reset_index(drop=True)


def _merge_opportunity_with_lfs(opportunity_df: pd.DataFrame, lfs_df: pd.DataFrame) -> pd.DataFrame:
    lfs_joinable = _collapse_lfs_rows_by_district(lfs_df)
    lfs_joinable = lfs_joinable.drop(columns=["province_name"], errors="ignore")
    merged = opportunity_df.merge(lfs_joinable, on="district_name", how="left")
    return merged


def _slugify_column(name: str) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", str(name).strip().lower())
    return cleaned.strip("_") or "metric"


def _metric_label(metric: str) -> str:
    if metric in METRIC_LABEL_OVERRIDES:
        return METRIC_LABEL_OVERRIDES[metric]

    cleaned = metric
    for prefix in ["local_avg_", "local_sum_"]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    return cleaned.replace("_", " ").title()


def _metric_format(metric: str) -> str:
    if metric.endswith("_rank"):
        return ","
    if metric.startswith("lfs_n_") or metric == "lfs_weighted_women_16_plus":
        return ","
    if metric.endswith("_monthly_cash_income"):
        return ".0f"
    if metric.endswith("_usual_hours"):
        return ".1f"
    if metric.startswith("n_") or metric in {"n_mothers", "n_children", "n_women_15_49", "local_sample_rows"}:
        return ","
    if "rate" in metric or "share" in metric or "percent" in metric:
        return ".1%"
    return ".3f"


def _format_metric_value(metric: str, value: object) -> str:
    if pd.isna(value):
        return "n/a"

    fmt = _metric_format(metric)
    if fmt == ",":
        return f"{int(round(float(value))):,}"
    if fmt == ".1%":
        return f"{float(value):.1%}"
    return f"{float(value):.3f}"


def _format_whole_number(value: object) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{int(round(float(value))):,}"


def _column_label(column: str) -> str:
    if column in COLUMN_LABEL_OVERRIDES:
        return COLUMN_LABEL_OVERRIDES[column]
    if column.startswith("local_avg_"):
        return f"Local avg: {_metric_label(column)}"
    return _metric_label(column)


def _province_color_scale() -> alt.Scale:
    return alt.Scale(
        domain=list(PROVINCE_COLORS.keys()),
        range=[PROVINCE_COLORS[name] for name in PROVINCE_COLORS],
    )


def _component_color_scale(components: list[str]) -> alt.Scale:
    return alt.Scale(
        domain=[_metric_label(component) for component in components],
        range=[COMPONENT_COLORS.get(component, UI_THEME["accent_secondary"]) for component in components],
    )


def _shared_priority_districts(
    opportunity_summary: dict[str, object],
    cfsva_summary: dict[str, object],
) -> list[str]:
    opportunity_hotspots = [str(value) for value in opportunity_summary.get("top_5_opportunity_districts", [])]
    cfsva_hotspots = {str(value) for value in cfsva_summary.get("top_10_districts", [])}
    return [district for district in opportunity_hotspots if district in cfsva_hotspots]


def _district_options_for_province(baseline_df: pd.DataFrame, province_name: str | None) -> list[str]:
    if not province_name:
        return []

    return sorted(
        baseline_df.loc[baseline_df["province_name"] == province_name, "district_name"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )


def _build_metric_quality_table(local_df: pd.DataFrame, metric_columns: list[str]) -> pd.DataFrame:
    total_rows = max(len(local_df), 1)
    rows: list[dict[str, object]] = []

    for column in metric_columns:
        raw_values = local_df[column]
        numeric_values = pd.to_numeric(raw_values, errors="coerce")
        rows.append(
            {
                "metric_name": column,
                "rows_with_values": int(raw_values.notna().sum()),
                "numeric_rows": int(numeric_values.notna().sum()),
                "lost_after_coercion": int(max(raw_values.notna().sum() - numeric_values.notna().sum(), 0)),
                "numeric_share": float(numeric_values.notna().sum() / total_rows),
            }
        )

    return pd.DataFrame(rows)


def _with_all_filter_option(values: list[str]) -> list[str]:
    if not values:
        return []
    return [ALL_FILTER_OPTION, *values]


def _resolve_all_filter_selection(selected_values: list[str], available_values: list[str]) -> list[str]:
    if not available_values:
        return []
    if not selected_values or ALL_FILTER_OPTION in selected_values:
        return available_values
    return [value for value in selected_values if value in available_values]


def _prepare_all_filter_state(key: str, available_values: list[str]) -> None:
    previous_key = f"{key}__previous"

    if not available_values:
        st.session_state[key] = []
        st.session_state[previous_key] = []
        return

    current_values = st.session_state.get(key)
    if not isinstance(current_values, list) or not current_values:
        st.session_state[key] = [ALL_FILTER_OPTION]
        st.session_state[previous_key] = [ALL_FILTER_OPTION]
        return

    previous_values = st.session_state.get(previous_key, [])
    if not isinstance(previous_values, list):
        previous_values = []

    filtered_values = [
        value for value in current_values if value == ALL_FILTER_OPTION or value in available_values
    ]

    if ALL_FILTER_OPTION in filtered_values and len(filtered_values) > 1:
        if ALL_FILTER_OPTION in previous_values:
            filtered_values = [value for value in filtered_values if value != ALL_FILTER_OPTION]
        else:
            filtered_values = [ALL_FILTER_OPTION]

    resolved_values = filtered_values or [ALL_FILTER_OPTION]
    st.session_state[key] = resolved_values
    st.session_state[previous_key] = list(resolved_values)


def _render_app_styles() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background:
                radial-gradient(circle at top right, rgba(180, 83, 9, 0.08), transparent 30%),
                linear-gradient(180deg, {UI_THEME['page_bg']} 0%, #fbf7f0 42%, #f7f0e5 100%);
            color: {UI_THEME['text']};
        }}
        [data-testid="stAppViewContainer"] > .main .block-container {{
            max-width: 1320px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #fffdfa 0%, #f4eadb 100%);
            border-right: 1px solid {UI_THEME['border']};
        }}
        h1, h2, h3 {{
            font-family: "Palatino Linotype", "Book Antiqua", Georgia, serif;
            letter-spacing: -0.02em;
            color: {UI_THEME['text']};
        }}
        div[data-testid="stMetric"] {{
            background: rgba(255, 253, 248, 0.92);
            border: 1px solid {UI_THEME['border']};
            border-radius: 18px;
            padding: 1rem 1rem 0.9rem 1rem;
            box-shadow: 0 18px 36px rgba(15, 23, 42, 0.05);
        }}
        div[data-testid="stMetricLabel"] {{
            color: {UI_THEME['muted']};
            font-weight: 600;
        }}
        div[data-testid="stMetricValue"] {{
            color: {UI_THEME['text']};
        }}
        div.stDownloadButton > button,
        div.stButton > button {{
            border-radius: 999px;
            border: 1px solid {UI_THEME['accent']};
            background: linear-gradient(135deg, #fff9ef 0%, #f8e0ab 100%);
            color: {UI_THEME['text']};
            font-weight: 600;
        }}
        .app-hero {{
            border: 1px solid {UI_THEME['border']};
            border-radius: 28px;
            padding: 1.55rem 1.7rem;
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.96) 0%, rgba(252, 243, 227, 0.98) 56%, rgba(233, 247, 243, 0.96) 100%);
            box-shadow: 0 28px 56px rgba(15, 23, 42, 0.08);
            margin-bottom: 1.15rem;
        }}
        .app-hero__eyebrow {{
            color: {UI_THEME['accent']};
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.72rem;
            font-weight: 700;
            margin-bottom: 0.45rem;
        }}
        .app-hero__title {{
            font-family: "Palatino Linotype", "Book Antiqua", Georgia, serif;
            color: {UI_THEME['text']};
            font-size: 2.25rem;
            line-height: 1.05;
            max-width: 13ch;
            margin-bottom: 0.6rem;
        }}
        .app-hero__body {{
            color: {UI_THEME['muted']};
            font-size: 1rem;
            line-height: 1.55;
            max-width: 68ch;
        }}
        .app-pill-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-top: 0.95rem;
        }}
        .app-pill {{
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 0.36rem 0.7rem;
            border: 1px solid rgba(180, 83, 9, 0.18);
            background: rgba(255, 250, 240, 0.92);
            color: {UI_THEME['text']};
            font-size: 0.84rem;
            font-weight: 600;
        }}
        .app-note-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 0.85rem;
            margin-top: 1rem;
        }}
        .app-note-card {{
            border-radius: 20px;
            padding: 1rem 1rem 0.95rem 1rem;
            border: 1px solid rgba(15, 118, 110, 0.14);
            background: rgba(255, 255, 255, 0.86);
        }}
        .app-note-label {{
            color: {UI_THEME['muted']};
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.35rem;
        }}
        .app-note-value {{
            color: {UI_THEME['text']};
            font-size: 1.04rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }}
        .app-note-copy {{
            color: {UI_THEME['muted']};
            line-height: 1.45;
            font-size: 0.92rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_app_header(
    active_view: str,
    opportunity_summary: dict[str, object],
    cfsva_summary: dict[str, object],
) -> None:
    shared_hotspots = _shared_priority_districts(opportunity_summary, cfsva_summary)
    spotlight_districts = shared_hotspots or [str(value) for value in opportunity_summary.get("top_5_opportunity_districts", [])[:3]]
    spotlight_text = ", ".join(spotlight_districts) if spotlight_districts else "Processed district baselines are ready to review."

    pill_text = [
        f"DHS districts {_format_whole_number(opportunity_summary.get('districts'))}",
        f"Women poverty avg {_format_metric_value('women_positive_rate', opportunity_summary.get('poverty_rate_women'))}",
        f"Avg gender responsive budgeting score {_format_metric_value('policy_priority_score', cfsva_summary.get('avg_policy_priority_score'))}",
        f"Avg stunting {_format_metric_value('stunting_rate', cfsva_summary.get('avg_stunting'))}",
    ]
    pill_markup = "".join(f"<span class='app-pill'>{escape(text)}</span>" for text in pill_text)

    st.markdown(
        f"""
        <div class="app-hero">
            <div class="app-hero__eyebrow">Rwanda Gender Data Visibility Intelligence Platform</div>
            <div class="app-hero__title">Decision-ready district targeting for CSOs and policy teams</div>
            <div class="app-hero__body">
                Blend DHS gender responsive budgeting signals, CFSVA nutrition risk, and session-level field uploads into one workflow that answers where to act first and why.
            </div>
            <div class="app-pill-row">{pill_markup}</div>
            <div class="app-note-grid">
                <div class="app-note-card">
                    <div class="app-note-label">Cross-baseline hotspot watchlist</div>
                    <div class="app-note-value">{escape(spotlight_text)}</div>
                    <div class="app-note-copy">Districts that recur across both baselines are the fastest candidates for field validation, partner outreach, and action planning.</div>
                </div>
                <div class="app-note-card">
                    <div class="app-note-label">Active workflow</div>
                    <div class="app-note-value">{escape(active_view)}</div>
                    <div class="app-note-copy">Navigation and filters stay fixed in the sidebar so you can move between ranking views, district briefs, and local-donation merges without losing context.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if active_view == "DHS Gender Responsive Budgeting View":
        top1, top2, top3, top4 = st.columns(4)
        top1.metric("Districts covered", _format_whole_number(opportunity_summary.get("districts") or cfsva_summary.get("districts")))
        top2.metric("Women 15-49 analyzed", _format_whole_number(opportunity_summary.get("women_15_49")))
        top3.metric("Mother survey rows", _format_whole_number(cfsva_summary.get("mother_rows")))
        top4.metric("Child survey rows", _format_whole_number(cfsva_summary.get("child_rows")))


def _clamp_to_unit_interval(value: float) -> float:
    return max(0.0, min(1.0, value))


def _interpolate_rgb_color(start_rgb: tuple[int, int, int], end_rgb: tuple[int, int, int], ratio: float) -> str:
    ratio = _clamp_to_unit_interval(ratio)
    red = int(round(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio))
    green = int(round(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio))
    blue = int(round(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio))
    return f"#{red:02x}{green:02x}{blue:02x}"


def _district_metric_rectangle_color(
    value: object,
    *,
    min_value: float,
    max_value: float,
    low_is_risk: bool,
) -> str:
    if pd.isna(value) or pd.isna(min_value) or pd.isna(max_value):
        return "#9ca3af"

    if max_value <= min_value:
        ratio = 0.5
    else:
        ratio = (float(value) - float(min_value)) / (float(max_value) - float(min_value))
    ratio = _clamp_to_unit_interval(ratio)

    if low_is_risk:
        return _interpolate_rgb_color(UNDERLINE_RED_RGB, UNDERLINE_GREEN_RGB, ratio)
    return _interpolate_rgb_color(UNDERLINE_GREEN_RGB, UNDERLINE_RED_RGB, ratio)


def _render_metric_underline(
    metric_name: str,
    value: object,
    baseline_df: pd.DataFrame,
    *,
    low_is_risk: bool,
) -> None:
    if metric_name not in baseline_df.columns:
        return

    metric_series = pd.to_numeric(baseline_df[metric_name], errors="coerce")
    min_value = metric_series.min(skipna=True)
    max_value = metric_series.max(skipna=True)
    metric_color = _district_metric_rectangle_color(
        value,
        min_value=float(min_value) if pd.notna(min_value) else float("nan"),
        max_value=float(max_value) if pd.notna(max_value) else float("nan"),
        low_is_risk=low_is_risk,
    )

    st.markdown(
        (
            f"<div style='margin-top:-14px;margin-bottom:2px;height:4px;"
            f"border-radius:4px;background:{metric_color};'></div>"
        ),
        unsafe_allow_html=True,
    )


def _render_metric_underline_legend() -> None:
    st.markdown(
        (
            f"<div style='border:1px solid {UI_THEME['border']};border-radius:14px;padding:10px 8px;background:{UI_THEME['surface']};'>"
            f"<div style='font-size:0.70rem;color:{UI_THEME['muted']};font-weight:700;margin-bottom:6px;'>Legend</div>"
            "<div style='display:flex;align-items:stretch;gap:8px;'>"
            "<div style='width:10px;height:88px;border-radius:6px;"
            f"background:linear-gradient(to bottom,{_interpolate_rgb_color(UNDERLINE_RED_RGB, UNDERLINE_RED_RGB, 0)} 0%,{_interpolate_rgb_color(UNDERLINE_GREEN_RGB, UNDERLINE_GREEN_RGB, 0)} 100%);'></div>"
            "<div style='display:flex;flex-direction:column;justify-content:space-between;"
            f"font-size:0.68rem;color:{UI_THEME['muted']};line-height:1.2;'>"
            "<span>higher concern</span>"
            "<span>lower concern</span>"
            "</div>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_sorted_metric_bar_chart(
    dataframe: pd.DataFrame,
    *,
    label_column: str,
    district_column: str,
    province_column: str,
    metric_column: str,
) -> None:
    plot_df = dataframe[[label_column, district_column, province_column, metric_column]].copy()
    plot_df = plot_df.dropna(subset=[metric_column])

    chart = (
        alt.Chart(plot_df)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X(
                f"{label_column}:N",
                sort=alt.EncodingSortField(field=metric_column, order="descending"),
                title="District",
            ),
            y=alt.Y(f"{metric_column}:Q", title=_metric_label(metric_column)),
            color=alt.Color(f"{province_column}:N", title="Province", scale=_province_color_scale()),
            tooltip=[
                alt.Tooltip(f"{district_column}:N", title="District"),
                alt.Tooltip(f"{province_column}:N", title="Province"),
                alt.Tooltip(f"{metric_column}:Q", title=_metric_label(metric_column), format=_metric_format(metric_column)),
            ],
        )
        .properties(height=360)
        .configure_view(strokeWidth=0)
        .configure_axis(labelColor=UI_THEME["muted"], titleColor=UI_THEME["muted"], gridColor="#eadfce")
        .configure_legend(labelColor=UI_THEME["muted"], titleColor=UI_THEME["text"], orient="bottom")
    )
    st.altair_chart(chart, width="stretch")


def _render_ranked_component_chart(
    dataframe: pd.DataFrame,
    *,
    label_column: str,
    district_column: str,
    components: list[str],
) -> None:
    order = dataframe[label_column].astype(str).tolist()
    long_df = dataframe[[label_column, district_column, *components]].melt(
        id_vars=[label_column, district_column],
        value_vars=components,
        var_name="component",
        value_name="value",
    )
    long_df["component_label"] = long_df["component"].map(_metric_label)

    chart = (
        alt.Chart(long_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{label_column}:N", sort=order, title="District"),
            y=alt.Y("value:Q", title="Rate"),
            color=alt.Color("component_label:N", title="Risk component", scale=_component_color_scale(components)),
            tooltip=[
                alt.Tooltip(f"{district_column}:N", title="District"),
                alt.Tooltip("component_label:N", title="Component"),
                alt.Tooltip("value:Q", title="Rate", format=".1%"),
            ],
        )
        .properties(height=360)
        .configure_view(strokeWidth=0)
        .configure_axis(labelColor=UI_THEME["muted"], titleColor=UI_THEME["muted"], gridColor="#eadfce")
        .configure_legend(labelColor=UI_THEME["muted"], titleColor=UI_THEME["text"], orient="bottom")
    )
    st.altair_chart(chart, width="stretch")


def _sidebar_navigation() -> str:
    with st.sidebar:
        st.header("Navigation")
        view = st.radio(
            "Select analysis view",
            options=[
                "DHS Gender Responsive Budgeting View",
                "LFS Women Labor View",
                "District Vulnerability Index View",
                "CFSVA Nutrition & Food Security Priority View",
                "District One-Click Report",
                "Data Donation Merge",
            ],
            index=0,
            key="active_view",
        )
        st.caption("Filters and setup controls stay fixed in this sidebar as you move through the app.")
    return view


def _sidebar_opportunity_filters(op_df: pd.DataFrame) -> dict[str, object]:
    with st.sidebar:
        st.markdown("---")
        st.subheader("DHS Filters")

        all_provinces = sorted(op_df["province_name"].dropna().astype(str).unique().tolist())
        _prepare_all_filter_state("op_provinces", all_provinces)
        sel_provinces_raw = st.multiselect(
            "Province",
            options=_with_all_filter_option(all_provinces),
            default=[ALL_FILTER_OPTION],
            key="op_provinces",
        )
        sel_provinces = _resolve_all_filter_selection(sel_provinces_raw, all_provinces)

        district_source = op_df.copy()
        if sel_provinces:
            district_source = district_source[district_source["province_name"].isin(sel_provinces)]
        all_districts = sorted(district_source["district_name"].dropna().astype(str).unique().tolist())
        _prepare_all_filter_state("op_districts", all_districts)
        sel_districts_raw = st.multiselect(
            "District",
            options=_with_all_filter_option(all_districts),
            default=[ALL_FILTER_OPTION],
            key="op_districts",
        )
        sel_districts = _resolve_all_filter_selection(sel_districts_raw, all_districts)

        max_n = int(op_df["n_women_15_49"].fillna(0).max()) if "n_women_15_49" in op_df.columns else 0
        min_n = st.slider(
            "Min women 15-49",
            min_value=0,
            max_value=max(max_n, 1),
            value=0,
            key="op_min_n",
        )
        op_sort = st.selectbox(
            "Sort metric",
            options=["opportunity_score", "women_positive_rate", "no_edu_rate", "rural_share"],
            index=0,
            key="op_sort",
        )
        op_top_n = st.slider("Top districts", min_value=5, max_value=30, value=15, key="op_top_n")

    return {
        "provinces": sel_provinces,
        "districts": sel_districts,
        "min_women": min_n,
        "sort_metric": op_sort,
        "top_n": op_top_n,
    }


def _sidebar_cfsva_filters(cfsva_df: pd.DataFrame) -> dict[str, object]:
    with st.sidebar:
        st.markdown("---")
        st.subheader("CFSVA Filters")

        all_provinces = sorted(cfsva_df["province_name"].dropna().astype(str).unique().tolist())
        _prepare_all_filter_state("cf_provinces", all_provinces)
        selected_provinces_raw = st.multiselect(
            "Province",
            options=_with_all_filter_option(all_provinces),
            default=[ALL_FILTER_OPTION],
            key="cf_provinces",
        )
        selected_provinces = _resolve_all_filter_selection(selected_provinces_raw, all_provinces)

        district_source = cfsva_df.copy()
        if selected_provinces:
            district_source = district_source[district_source["province_name"].isin(selected_provinces)]
        all_districts = sorted(district_source["district_name"].dropna().astype(str).unique().tolist())
        _prepare_all_filter_state("cf_districts", all_districts)
        selected_districts_raw = st.multiselect(
            "District",
            options=_with_all_filter_option(all_districts),
            default=[ALL_FILTER_OPTION],
            key="cf_districts",
        )
        selected_districts = _resolve_all_filter_selection(selected_districts_raw, all_districts)
        max_mothers = int(cfsva_df["n_mothers"].fillna(0).max()) if "n_mothers" in cfsva_df.columns else 0
        max_children = int(cfsva_df["n_children"].fillna(0).max()) if "n_children" in cfsva_df.columns else 0
        min_mothers = st.slider(
            "Min mothers",
            min_value=0,
            max_value=max(max_mothers, 1),
            value=0,
            key="cf_min_mothers",
        )
        min_children = st.slider(
            "Min children",
            min_value=0,
            max_value=max(max_children, 1),
            value=0,
            key="cf_min_children",
        )
        cf_sort = st.selectbox(
            "Sort metric",
            options=[
                "policy_priority_score",
                "fi_modsev_rate",
                "stunting_rate",
                "poor_borderline_rate",
                "underweight_rate",
                "wasting_rate",
            ],
            index=0,
            key="cf_sort",
        )
        cf_top_n = st.slider("Top districts", min_value=5, max_value=30, value=15, key="cf_top_n")

    return {
        "provinces": selected_provinces,
        "districts": selected_districts,
        "min_mothers": min_mothers,
        "min_children": min_children,
        "sort_metric": cf_sort,
        "top_n": cf_top_n,
    }


def _sidebar_lfs_filters(lfs_df: pd.DataFrame) -> dict[str, object]:
    with st.sidebar:
        st.markdown("---")
        st.subheader("LFS Filters")

        all_provinces = sorted(lfs_df["province_name"].dropna().astype(str).unique().tolist())
        _prepare_all_filter_state("lfs_provinces", all_provinces)
        selected_provinces_raw = st.multiselect(
            "Province",
            options=_with_all_filter_option(all_provinces),
            default=[ALL_FILTER_OPTION],
            key="lfs_provinces",
        )
        selected_provinces = _resolve_all_filter_selection(selected_provinces_raw, all_provinces)

        district_source = lfs_df.copy()
        if selected_provinces:
            district_source = district_source[district_source["province_name"].isin(selected_provinces)]
        all_districts = sorted(district_source["district_name"].dropna().astype(str).unique().tolist())
        _prepare_all_filter_state("lfs_districts", all_districts)
        selected_districts_raw = st.multiselect(
            "District",
            options=_with_all_filter_option(all_districts),
            default=[ALL_FILTER_OPTION],
            key="lfs_districts",
        )
        selected_districts = _resolve_all_filter_selection(selected_districts_raw, all_districts)

        max_records = int(lfs_df["lfs_n_women_16_plus"].fillna(0).max()) if "lfs_n_women_16_plus" in lfs_df.columns else 0
        min_records = st.slider(
            "Min women 16+ records",
            min_value=0,
            max_value=max(max_records, 1),
            value=0,
            key="lfs_min_records",
        )
        lfs_sort = st.selectbox(
            "Sort metric",
            options=[
                "lfs_labor_risk_score",
                "lfs_women_unemployment_rate",
                "lfs_women_out_of_labor_force_rate",
                "lfs_women_time_underemployment_rate",
                "lfs_women_employment_rate",
                "lfs_women_mean_monthly_cash_income",
            ],
            index=0,
            key="lfs_sort",
        )
        lfs_top_n = st.slider("Top districts", min_value=5, max_value=30, value=15, key="lfs_top_n")

    return {
        "provinces": selected_provinces,
        "districts": selected_districts,
        "min_records": min_records,
        "sort_metric": lfs_sort,
        "top_n": lfs_top_n,
    }


def _sidebar_vulnerability_filters(vulnerability_df: pd.DataFrame) -> dict[str, object]:
    with st.sidebar:
        st.markdown("---")
        st.subheader("Vulnerability Filters")

        all_provinces = sorted(vulnerability_df["province_name"].dropna().astype(str).unique().tolist())
        _prepare_all_filter_state("vuln_provinces", all_provinces)
        selected_provinces_raw = st.multiselect(
            "Province",
            options=_with_all_filter_option(all_provinces),
            default=[ALL_FILTER_OPTION],
            key="vuln_provinces",
        )
        selected_provinces = _resolve_all_filter_selection(selected_provinces_raw, all_provinces)

        district_source = vulnerability_df.copy()
        if selected_provinces:
            district_source = district_source[district_source["province_name"].isin(selected_provinces)]
        all_districts = sorted(district_source["district_name"].dropna().astype(str).unique().tolist())
        _prepare_all_filter_state("vuln_districts", all_districts)
        selected_districts_raw = st.multiselect(
            "District",
            options=_with_all_filter_option(all_districts),
            default=[ALL_FILTER_OPTION],
            key="vuln_districts",
        )
        selected_districts = _resolve_all_filter_selection(selected_districts_raw, all_districts)

        tier_options = sorted(vulnerability_df["vulnerability_tier"].dropna().astype(str).unique().tolist())
        _prepare_all_filter_state("vuln_tiers", tier_options)
        selected_tiers_raw = st.multiselect(
            "Vulnerability tier",
            options=_with_all_filter_option(tier_options),
            default=[ALL_FILTER_OPTION],
            key="vuln_tiers",
        )
        selected_tiers = _resolve_all_filter_selection(selected_tiers_raw, tier_options)

        max_women = int(vulnerability_df["n_women_15_49"].fillna(0).max()) if "n_women_15_49" in vulnerability_df.columns else 0
        min_women = st.slider(
            "Min women 15-49 sample",
            min_value=0,
            max_value=max(max_women, 1),
            value=0,
            key="vuln_min_women",
        )

        vuln_sort = st.selectbox(
            "Sort metric",
            options=[
                "vulnerability_index",
                "economic_stress_index",
                "nutrition_risk_index",
                "labor_market_risk_index",
            ],
            index=0,
            key="vuln_sort",
        )
        vuln_top_n = st.slider("Top districts", min_value=5, max_value=30, value=15, key="vuln_top_n")

    return {
        "provinces": selected_provinces,
        "districts": selected_districts,
        "tiers": selected_tiers,
        "min_women": min_women,
        "sort_metric": vuln_sort,
        "top_n": vuln_top_n,
    }


def _sidebar_report_filters(baseline_df: pd.DataFrame, local_summary: pd.DataFrame | None) -> dict[str, object]:
    with st.sidebar:
        st.markdown("---")
        st.subheader("District Brief")

        province_options = sorted(baseline_df["province_name"].dropna().astype(str).unique().tolist())
        if not province_options:
            st.warning("No district baseline is available yet for the report view.")
            return {
                "province": None,
                "district": None,
                "include_local": False,
            }

        selected_province = st.selectbox("Province", options=province_options, key="report_province")

        district_options = _district_options_for_province(baseline_df, selected_province)
        selected_district = None
        if district_options:
            selected_district = st.selectbox("District", options=district_options, key="report_district")
        else:
            st.warning("No districts are available for the selected province.")

        include_local = False
        if local_summary is not None and not local_summary.empty:
            st.success(f"Local donation data available for {local_summary['district_name'].nunique()} district(s).")
            include_local = st.checkbox(
                "Include uploaded local data in the brief",
                value=True,
                key="report_include_local",
            )
        else:
            st.caption("No local donated data attached yet. Use the Data Donation Merge view to add district evidence.")

    return {
        "province": selected_province,
        "district": selected_district,
        "include_local": include_local,
    }


def _detect_district_candidates(columns: list[str]) -> list[str]:
    exact = ["district", "district_name", "s0_d_dist"]
    ranked: list[str] = []

    for target in exact:
        for column in columns:
            if column.strip().lower() == target and column not in ranked:
                ranked.append(column)

    for column in columns:
        normalized = column.strip().lower()
        if ("district" in normalized or normalized.endswith("_dist") or normalized.startswith("dist")) and column not in ranked:
            ranked.append(column)

    return ranked


def _read_uploaded_donation_frame(uploaded_file) -> pd.DataFrame:
    file_name = uploaded_file.name.lower()
    payload = BytesIO(uploaded_file.getvalue())

    if file_name.endswith(".csv"):
        return pd.read_csv(payload)
    if file_name.endswith(".xlsx"):
        return pd.read_excel(payload)

    raise ValueError("Unsupported file type. Upload a CSV or XLSX file.")


def _sidebar_donation_file_uploader():
    with st.sidebar:
        st.markdown("---")
        st.subheader("Data Donation")
        uploaded_file = st.file_uploader(
            "Upload local survey data",
            type=["csv", "xlsx"],
            key="donation_file",
            help="Upload a CSV or XLSX file with at least one district column and one numeric indicator.",
        )
        st.caption("Minimum input: one district column and one or more numeric indicator columns.")
    return uploaded_file


def _sidebar_donation_config(local_df: pd.DataFrame) -> dict[str, object]:
    with st.sidebar:
        district_candidates = _detect_district_candidates(local_df.columns.tolist())
        district_options = local_df.columns.tolist()
        district_index = district_options.index(district_candidates[0]) if district_candidates else 0
        district_column = st.selectbox(
            "District column",
            options=district_options,
            index=district_index,
            key="donation_district_column",
        )

        numeric_columns = [
            column for column in local_df.columns if pd.api.types.is_numeric_dtype(local_df[column]) and column != district_column
        ]
        default_metrics = numeric_columns[: min(5, len(numeric_columns))]
        selected_metrics = st.multiselect(
            "Numeric metrics to merge",
            options=numeric_columns,
            default=default_metrics,
            key="donation_metrics",
            help="The app aggregates these numeric fields by district using simple district averages.",
        )
        show_all_baseline = st.checkbox(
            "Show all 30 baseline districts after merge",
            value=False,
            key="donation_show_all_baseline",
        )

    return {
        "district_column": district_column,
        "selected_metrics": selected_metrics,
        "show_all_baseline": show_all_baseline,
    }


def _aggregate_local_donation(
    local_df: pd.DataFrame,
    *,
    district_column: str,
    metric_columns: list[str],
) -> tuple[pd.DataFrame, list[str], dict[str, str]]:
    working = local_df.copy()
    working["district_name"] = working[district_column].apply(_normalize_district_value)

    unmatched_districts = sorted(
        working.loc[working["district_name"].isna(), district_column].dropna().astype(str).unique().tolist()
    )

    matched = working.dropna(subset=["district_name"]).copy()
    if matched.empty:
        raise ValueError("No uploaded rows matched the 30 supported Rwanda district names.")

    metric_map: dict[str, str] = {}
    for column in metric_columns:
        matched[column] = pd.to_numeric(matched[column], errors="coerce")
        metric_map[f"local_avg_{_slugify_column(column)}"] = column

    agg_spec: dict[str, tuple[str, str]] = {"local_sample_rows": (district_column, "size")}
    for output_column, source_column in metric_map.items():
        agg_spec[output_column] = (source_column, "mean")

    summary = matched.groupby("district_name", dropna=False).agg(**agg_spec).reset_index()
    summary = _attach_province_from_district(summary, district_column="district_name")
    summary = summary.sort_values(["province_name", "district_name"]).reset_index(drop=True)
    return summary, unmatched_districts, metric_map


def _merge_local_with_baseline(baseline_df: pd.DataFrame, local_summary: pd.DataFrame) -> pd.DataFrame:
    merged = baseline_df.merge(local_summary, on=["district_name", "province_name"], how="left")
    merged["local_data_present"] = merged["local_sample_rows"].fillna(0) > 0
    return merged.sort_values(["local_data_present", "policy_priority_score", "opportunity_score"], ascending=[False, False, False])


def _district_priority_callout(row: pd.Series) -> tuple[str, str]:
    op_rank = row.get("opportunity_rank")
    policy_rank = row.get("priority_rank")

    if pd.notna(op_rank) and pd.notna(policy_rank) and op_rank <= 10 and policy_rank <= 10:
        return "warning", "This district is high-priority in both DHS and CFSVA gender responsive budgeting baselines."
    if pd.notna(policy_rank) and policy_rank <= 10:
        return "info", "This district is especially urgent on the CFSVA gender responsive budgeting baseline."
    if pd.notna(op_rank) and op_rank <= 10:
        return "info", "This district is especially urgent on the DHS gender responsive budgeting baseline."
    return "success", "This district is lower-ranked than the most urgent hotspots, but still available for local targeting and monitoring."


def _generate_cso_actions(row: pd.Series) -> list[str]:
    actions: list[str] = []

    if pd.notna(row.get("policy_priority_score")) and row.get("policy_priority_score") >= ACTION_THRESHOLDS["policy_priority_score"]:
        actions.append("Scale district-level food security response together with maternal and child nutrition services.")
    if pd.notna(row.get("women_positive_rate")) and row.get("women_positive_rate") >= ACTION_THRESHOLDS["women_positive_rate"]:
        actions.append("Prioritize women-focused livelihoods, savings groups, and social protection or cash-support programming.")
    if pd.notna(row.get("no_edu_rate")) and row.get("no_edu_rate") >= ACTION_THRESHOLDS["no_edu_rate"]:
        actions.append("Add adult literacy and girls' retention support because education deprivation remains material.")
    if pd.notna(row.get("stunting_rate")) and row.get("stunting_rate") >= ACTION_THRESHOLDS["stunting_rate"]:
        actions.append("Pair food-support programs with child growth monitoring, nutrition counseling, and WASH interventions.")
    if pd.notna(row.get("poor_borderline_rate")) and row.get("poor_borderline_rate") >= ACTION_THRESHOLDS["poor_borderline_rate"]:
        actions.append("Combine immediate consumption support with agriculture and household resilience activities.")
    if pd.notna(row.get("rural_share")) and row.get("rural_share") >= ACTION_THRESHOLDS["rural_share"]:
        actions.append("Use community-based or mobile outreach because a large share of affected women are in rural areas.")

    if not actions:
        actions.append("Maintain targeted monitoring and validate local service gaps before scaling a major intervention package.")

    return actions[:5]


def _build_district_report_markdown(
    row: pd.Series,
    *,
    local_row: pd.Series | None,
    local_metric_map: dict[str, str],
) -> str:
    district = str(row.get("district_name", "Unknown district"))
    province = str(row.get("province_name", "Unknown province"))
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"# One-Click District Brief: {district}",
        "",
        f"Generated: {generated_at}",
        f"Province: {province}",
        "",
        "## Executive Summary",
        (
            f"{district} ranks {_format_metric_value('opportunity_rank', row.get('opportunity_rank'))}/30 on the DHS gender responsive budgeting baseline "
            f"and {_format_metric_value('priority_rank', row.get('priority_rank'))}/30 on the CFSVA gender responsive budgeting baseline."
        ),
        "",
        "## Core Baseline Metrics",
        f"- Women poverty rate: {_format_metric_value('women_positive_rate', row.get('women_positive_rate'))}",
        f"- Women no-education rate: {_format_metric_value('no_edu_rate', row.get('no_edu_rate'))}",
        f"- Rural share of women 15-49: {_format_metric_value('rural_share', row.get('rural_share'))}",
        f"- Moderate/severe food insecurity: {_format_metric_value('fi_modsev_rate', row.get('fi_modsev_rate'))}",
        f"- Poor/borderline food consumption: {_format_metric_value('poor_borderline_rate', row.get('poor_borderline_rate'))}",
        f"- Stunting rate: {_format_metric_value('stunting_rate', row.get('stunting_rate'))}",
        f"- Underweight rate: {_format_metric_value('underweight_rate', row.get('underweight_rate'))}",
        f"- Gender responsive budgeting score: {_format_metric_value('policy_priority_score', row.get('policy_priority_score'))}",
        "",
    ]

    has_lfs = any(
        pd.notna(row.get(metric_name))
        for metric_name in [
            "lfs_labor_risk_rank",
            "lfs_women_employment_rate",
            "lfs_women_unemployment_rate",
            "lfs_women_labor_force_participation_rate",
            "lfs_women_mean_monthly_cash_income",
        ]
    )
    if has_lfs:
        lines.extend(
            [
                "## Women Labor Snapshot (LFS 2022)",
                f"- Women labor risk rank: {_format_metric_value('lfs_labor_risk_rank', row.get('lfs_labor_risk_rank'))}/30",
                f"- Women employment rate: {_format_metric_value('lfs_women_employment_rate', row.get('lfs_women_employment_rate'))}",
                f"- Women unemployment rate: {_format_metric_value('lfs_women_unemployment_rate', row.get('lfs_women_unemployment_rate'))}",
                f"- Women labor-force participation: {_format_metric_value('lfs_women_labor_force_participation_rate', row.get('lfs_women_labor_force_participation_rate'))}",
                f"- Women mean monthly cash income: {_format_metric_value('lfs_women_mean_monthly_cash_income', row.get('lfs_women_mean_monthly_cash_income'))}",
                f"- Women time underemployment: {_format_metric_value('lfs_women_time_underemployment_rate', row.get('lfs_women_time_underemployment_rate'))}",
                "",
            ]
        )

    lines.extend(
        [
        "## Recommended CSO Actions",
        ]
    )

    for action in _generate_cso_actions(row):
        lines.append(f"- {action}")

    if local_row is not None:
        lines.extend(["", "## Local Donated Data Overlay"])
        lines.append(f"- Local sample rows: {_format_metric_value('local_sample_rows', local_row.get('local_sample_rows'))}")
        for metric_column in [column for column in local_row.index if str(column).startswith('local_avg_')]:
            source_name = local_metric_map.get(metric_column, metric_column)
            lines.append(
                f"- {source_name}: {_format_metric_value(metric_column, local_row.get(metric_column))}"
            )

    lines.extend(
        [
            "",
            "## Data Sources",
            "- DHS 2014/15 gender responsive budgeting baseline",
            "- CFSVA 2015 maternal and child nutrition baseline",
        ]
    )

    return "\n".join(lines)


def _render_opportunity_dashboard(op_df: pd.DataFrame, filters: dict[str, object]) -> None:
    op_df = _coerce_numeric(
        op_df,
        [
            "n_women_15_49",
            "women_positive_rate",
            "predicted_positive_rate",
            "opportunity_score",
            "no_edu_rate",
            "rural_share",
        ],
    )

    st.caption(
        "Women aged 15-49 from Rwanda DHS 2014/15 (RWHR70FL). "
        "DHS gender responsive budgeting score ranks districts by unmet economic need (poverty gap, education gap)."
    )

    filtered = op_df.copy()
    provinces = filters["provinces"]
    if provinces:
        filtered = filtered[filtered["province_name"].isin(provinces)]
    districts = filters["districts"]
    if districts:
        filtered = filtered[filtered["district_name"].isin(districts)]
    filtered = filtered[filtered["n_women_15_49"] >= int(filters["min_women"])]

    if filtered.empty:
        st.warning("No districts match current filters.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Districts", f"{len(filtered)}")
    col2.metric("Women 15-49", f"{filtered['n_women_15_49'].sum():,}")
    col3.metric("Avg poverty rate", f"{filtered['women_positive_rate'].mean():.1%}")
    col4.metric("Avg no-education", f"{filtered['no_edu_rate'].mean():.1%}")

    extra1, extra2 = st.columns(2)
    extra1.metric("DHS gender responsive budgeting score", f"{filtered['opportunity_score'].mean():.3f}")
    extra2.metric("Avg rural share", f"{filtered['rural_share'].mean():.1%}")

    sort_metric = str(filters["sort_metric"])
    top_n = int(filters["top_n"])
    ranked = filtered.sort_values(sort_metric, ascending=False).head(top_n).copy()
    ranked["label"] = ranked["province_name"] + " | " + ranked["district_name"]

    st.subheader(f"Top {top_n} priority districts by {sort_metric}")
    _render_sorted_metric_bar_chart(
        ranked,
        label_column="label",
        district_column="district_name",
        province_column="province_name",
        metric_column=sort_metric,
    )

    st.subheader("Poverty rate vs no-education rate by district")
    st.caption("Hover a dot to see district-level details.")
    scatter_df = filtered[
        [
            "district_name",
            "province_name",
            "n_women_15_49",
            "women_positive_rate",
            "no_edu_rate",
            "opportunity_score",
        ]
    ].dropna(subset=["women_positive_rate", "no_edu_rate"])
    scatter_chart = (
        alt.Chart(scatter_df)
        .mark_circle(size=95, opacity=0.85)
        .encode(
            x=alt.X("women_positive_rate:Q", title="Poverty rate (women)"),
            y=alt.Y("no_edu_rate:Q", title="No-education rate"),
            color=alt.Color("province_name:N", title="Province", scale=_province_color_scale()),
            tooltip=[
                alt.Tooltip("district_name:N", title="District"),
                alt.Tooltip("province_name:N", title="Province"),
                alt.Tooltip("n_women_15_49:Q", title="Women 15-49", format=","),
                alt.Tooltip("women_positive_rate:Q", title="Poverty rate", format=".1%"),
                alt.Tooltip("no_edu_rate:Q", title="No-education rate", format=".1%"),
                alt.Tooltip("opportunity_score:Q", title=_metric_label("opportunity_score"), format=".3f"),
            ],
        )
        .properties(height=360)
        .configure_view(strokeWidth=0)
        .configure_axis(labelColor=UI_THEME["muted"], titleColor=UI_THEME["muted"], gridColor="#eadfce")
        .configure_legend(labelColor=UI_THEME["muted"], titleColor=UI_THEME["text"], orient="bottom")
    )
    st.altair_chart(scatter_chart, width="stretch")
    if len(scatter_df) < len(filtered):
        st.caption(
            f"{len(filtered) - len(scatter_df)} district(s) are omitted from the scatter because one or more plotted metrics are missing."
        )

    display_cols = [
        "province_name",
        "district_name",
        "n_women_15_49",
        "women_positive_rate",
        "predicted_positive_rate",
        "opportunity_score",
        "opportunity_rank",
        "no_edu_rate",
        "rural_share",
    ]
    available_cols = [column for column in display_cols if column in ranked.columns]
    st.subheader("District detail table")
    st.dataframe(
        ranked[available_cols].rename(columns={column: _column_label(column) for column in available_cols}),
        width="stretch",
        hide_index=True,
    )

    st.download_button(
        label="Download DHS gender responsive budgeting CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="women_opportunity_districts.csv",
        mime="text/csv",
    )


def _render_lfs_dashboard(lfs_df: pd.DataFrame, filters: dict[str, object]) -> None:
    lfs_df = _coerce_numeric(
        lfs_df,
        [
            "lfs_n_women_16_plus",
            "lfs_weighted_women_16_plus",
            "lfs_n_women_labor_rows",
            "lfs_women_employment_rate",
            "lfs_women_unemployment_rate",
            "lfs_women_out_of_labor_force_rate",
            "lfs_women_labor_force_participation_rate",
            "lfs_women_time_underemployment_rate",
            "lfs_women_mean_monthly_cash_income",
            "lfs_women_median_monthly_cash_income",
            "lfs_women_mean_usual_hours",
            "lfs_labor_risk_score",
            "lfs_labor_risk_rank",
        ],
    )

    st.caption(
        "Women labor-market signals from Rwanda LFS 2022 aggregated at district level. "
        "This view isolates employment, unemployment, income, and labor-force risk patterns without mixing them into other baselines."
    )

    filtered = lfs_df.copy()
    provinces = filters["provinces"]
    if provinces:
        filtered = filtered[filtered["province_name"].isin(provinces)]
    districts = filters["districts"]
    if districts:
        filtered = filtered[filtered["district_name"].isin(districts)]
    filtered = filtered[filtered["lfs_n_women_16_plus"] >= int(filters["min_records"])]

    if filtered.empty:
        st.warning("No districts match current LFS filters.")
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Districts", f"{len(filtered)}")
    m2.metric("Women 16+ records", _format_metric_value("lfs_n_women_16_plus", filtered["lfs_n_women_16_plus"].sum()))
    m3.metric(
        "Avg employment rate",
        f"{filtered['lfs_women_employment_rate'].mean(skipna=True):.1%}" if filtered["lfs_women_employment_rate"].notna().any() else "n/a",
    )
    m4.metric(
        "Avg unemployment rate",
        f"{filtered['lfs_women_unemployment_rate'].mean(skipna=True):.1%}" if filtered["lfs_women_unemployment_rate"].notna().any() else "n/a",
    )

    m5, m6, m7, m8 = st.columns(4)
    m5.metric(
        "Avg LF participation",
        f"{filtered['lfs_women_labor_force_participation_rate'].mean(skipna=True):.1%}" if filtered["lfs_women_labor_force_participation_rate"].notna().any() else "n/a",
    )
    m6.metric(
        "Avg out of labor force",
        f"{filtered['lfs_women_out_of_labor_force_rate'].mean(skipna=True):.1%}" if filtered["lfs_women_out_of_labor_force_rate"].notna().any() else "n/a",
    )
    m7.metric(
        "Avg time underemployment",
        f"{filtered['lfs_women_time_underemployment_rate'].mean(skipna=True):.1%}" if filtered["lfs_women_time_underemployment_rate"].notna().any() else "n/a",
    )
    m8.metric(
        "Avg monthly cash income",
        f"{filtered['lfs_women_mean_monthly_cash_income'].mean(skipna=True):,.0f}" if filtered['lfs_women_mean_monthly_cash_income'].notna().any() else "n/a",
    )

    sort_metric = str(filters["sort_metric"])
    top_n = int(filters["top_n"])
    ranked = filtered.sort_values(sort_metric, ascending=False).head(top_n).copy()
    ranked["label"] = ranked["province_name"] + " | " + ranked["district_name"]

    st.subheader(f"Top {len(ranked)} districts by {_metric_label(sort_metric)}")
    _render_sorted_metric_bar_chart(
        ranked,
        label_column="label",
        district_column="district_name",
        province_column="province_name",
        metric_column=sort_metric,
    )

    st.subheader("Unemployment rate vs monthly cash income")
    st.caption("Hover a dot to inspect district-level women labor outcomes.")
    scatter_df = filtered[
        [
            "district_name",
            "province_name",
            "lfs_n_women_16_plus",
            "lfs_women_unemployment_rate",
            "lfs_women_employment_rate",
            "lfs_women_mean_monthly_cash_income",
            "lfs_labor_risk_score",
        ]
    ].dropna(subset=["lfs_women_unemployment_rate", "lfs_women_mean_monthly_cash_income"])
    scatter_chart = (
        alt.Chart(scatter_df)
        .mark_circle(size=95, opacity=0.85)
        .encode(
            x=alt.X("lfs_women_unemployment_rate:Q", title="Women unemployment rate"),
            y=alt.Y("lfs_women_mean_monthly_cash_income:Q", title="Women mean monthly cash income"),
            color=alt.Color("province_name:N", title="Province", scale=_province_color_scale()),
            tooltip=[
                alt.Tooltip("district_name:N", title="District"),
                alt.Tooltip("province_name:N", title="Province"),
                alt.Tooltip("lfs_n_women_16_plus:Q", title="Women 16+ records", format=","),
                alt.Tooltip("lfs_women_employment_rate:Q", title="Employment rate", format=".1%"),
                alt.Tooltip("lfs_women_unemployment_rate:Q", title="Unemployment rate", format=".1%"),
                alt.Tooltip("lfs_women_mean_monthly_cash_income:Q", title="Monthly cash income", format=",.0f"),
                alt.Tooltip("lfs_labor_risk_score:Q", title="Labor risk score", format=".3f"),
            ],
        )
        .properties(height=360)
        .configure_view(strokeWidth=0)
        .configure_axis(labelColor=UI_THEME["muted"], titleColor=UI_THEME["muted"], gridColor="#eadfce")
        .configure_legend(labelColor=UI_THEME["muted"], titleColor=UI_THEME["text"], orient="bottom")
    )
    st.altair_chart(scatter_chart, width="stretch")
    if len(scatter_df) < len(filtered):
        st.caption(
            f"{len(filtered) - len(scatter_df)} district(s) are omitted from the scatter because one or more plotted metrics are missing."
        )

    risk_components = [
        "lfs_women_unemployment_rate",
        "lfs_women_out_of_labor_force_rate",
        "lfs_women_time_underemployment_rate",
    ]
    component_ranked = ranked.dropna(subset=risk_components, how="all").copy()
    if not component_ranked.empty:
        st.subheader("Risk-rate profile for top districts")
        _render_ranked_component_chart(
            component_ranked,
            label_column="label",
            district_column="district_name",
            components=risk_components,
        )

    display_cols = [
        "province_name",
        "district_name",
        "lfs_labor_risk_rank",
        "lfs_labor_risk_score",
        "lfs_n_women_16_plus",
        "lfs_weighted_women_16_plus",
        "lfs_n_women_labor_rows",
        "lfs_women_employment_rate",
        "lfs_women_unemployment_rate",
        "lfs_women_labor_force_participation_rate",
        "lfs_women_out_of_labor_force_rate",
        "lfs_women_time_underemployment_rate",
        "lfs_women_mean_monthly_cash_income",
        "lfs_women_median_monthly_cash_income",
        "lfs_women_mean_usual_hours",
    ]
    available_cols = [column for column in display_cols if column in ranked.columns]
    st.subheader("District labor detail table")
    st.dataframe(
        ranked[available_cols].rename(columns={column: _column_label(column) for column in available_cols}),
        width="stretch",
        hide_index=True,
    )

    st.download_button(
        label="Download LFS district labor CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="lfs_2022_women_district_labor_filtered.csv",
        mime="text/csv",
    )


def _render_vulnerability_dashboard(
    vulnerability_df: pd.DataFrame,
    filters: dict[str, object],
    summary: dict[str, object],
) -> None:
    st.caption(
        "Composite district vulnerability index built from DHS economic stress, "
        "CFSVA nutrition risk, and LFS labor-market risk domains."
    )

    filtered = vulnerability_df.copy()
    provinces = filters["provinces"]
    if provinces:
        filtered = filtered[filtered["province_name"].isin(provinces)]
    districts = filters["districts"]
    if districts:
        filtered = filtered[filtered["district_name"].isin(districts)]
    tiers = filters["tiers"]
    if tiers and "vulnerability_tier" in filtered.columns:
        filtered = filtered[filtered["vulnerability_tier"].isin(tiers)]
    if "n_women_15_49" in filtered.columns:
        filtered = filtered[filtered["n_women_15_49"].fillna(0) >= int(filters["min_women"])]

    filtered = filtered[filtered["vulnerability_index"].notna()].copy()
    if filtered.empty:
        st.warning("No districts match current vulnerability filters.")
        return

    filtered = filtered.sort_values("vulnerability_index", ascending=False).reset_index(drop=True)
    very_high_count = int((filtered["vulnerability_tier"] == "Very High").sum()) if "vulnerability_tier" in filtered.columns else 0
    top_district = str(filtered.iloc[0]["district_name"]) if not filtered.empty else "n/a"

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Districts", f"{len(filtered)}")
    k2.metric("Avg vulnerability index", f"{filtered['vulnerability_index'].mean(skipna=True):.3f}")
    k3.metric("Very high vulnerability", f"{very_high_count}")
    k4.metric("Highest-risk district", top_district)

    sort_metric = str(filters["sort_metric"])
    top_n = int(filters["top_n"])
    ranked = filtered.sort_values(sort_metric, ascending=False).head(top_n).copy()
    ranked["label"] = ranked["province_name"] + " | " + ranked["district_name"]

    st.subheader(f"Top {len(ranked)} districts by {_metric_label(sort_metric)}")
    _render_sorted_metric_bar_chart(
        ranked,
        label_column="label",
        district_column="district_name",
        province_column="province_name",
        metric_column=sort_metric,
    )

    st.subheader("Nutrition risk vs labor-market risk")
    st.caption("Dot size scales with the district vulnerability index.")
    scatter_df = filtered[
        [
            "district_name",
            "province_name",
            "vulnerability_tier",
            "nutrition_risk_index",
            "labor_market_risk_index",
            "economic_stress_index",
            "vulnerability_index",
        ]
    ].dropna(subset=["nutrition_risk_index", "labor_market_risk_index", "vulnerability_index"])
    if scatter_df.empty:
        st.info("Not enough non-missing domain values to draw the risk scatter.")
    else:
        scatter_chart = (
            alt.Chart(scatter_df)
            .mark_circle(opacity=0.85)
            .encode(
                x=alt.X("nutrition_risk_index:Q", title="Nutrition risk index (CFSVA)"),
                y=alt.Y("labor_market_risk_index:Q", title="Labor-market risk index (LFS)"),
                color=alt.Color("province_name:N", title="Province", scale=_province_color_scale()),
                size=alt.Size("vulnerability_index:Q", title="Vulnerability index", scale=alt.Scale(range=[80, 420])),
                tooltip=[
                    alt.Tooltip("district_name:N", title="District"),
                    alt.Tooltip("province_name:N", title="Province"),
                    alt.Tooltip("vulnerability_tier:N", title="Tier"),
                    alt.Tooltip("economic_stress_index:Q", title="Economic stress", format=".3f"),
                    alt.Tooltip("nutrition_risk_index:Q", title="Nutrition risk", format=".3f"),
                    alt.Tooltip("labor_market_risk_index:Q", title="Labor risk", format=".3f"),
                    alt.Tooltip("vulnerability_index:Q", title="Vulnerability index", format=".3f"),
                ],
            )
            .properties(height=360)
            .configure_view(strokeWidth=0)
            .configure_axis(labelColor=UI_THEME["muted"], titleColor=UI_THEME["muted"], gridColor="#eadfce")
            .configure_legend(labelColor=UI_THEME["muted"], titleColor=UI_THEME["text"], orient="bottom")
        )
        st.altair_chart(scatter_chart, width="stretch")

    components = [
        "economic_stress_index",
        "nutrition_risk_index",
        "labor_market_risk_index",
    ]
    component_ranked = ranked.dropna(subset=components, how="all").copy()
    if not component_ranked.empty:
        st.subheader("Domain profile for top districts")
        _render_ranked_component_chart(
            component_ranked,
            label_column="label",
            district_column="district_name",
            components=components,
        )

    with st.expander("Index explanation and formula", expanded=False):
        st.markdown(
            "\n".join(
                [
                    "The district vulnerability index is built in three steps:",
                    "1. Min-max normalize each input metric to a 0-1 risk scale.",
                    "2. Compute domain indices as simple averages:",
                    "   - Economic stress (DHS): poverty rate, no-education rate, rural share",
                    "   - Nutrition risk (CFSVA): food insecurity, poor/borderline consumption, stunting, underweight, wasting",
                    "   - Labor-market risk (LFS): unemployment, out-of-labor-force, underemployment, and inverse income",
                    "3. Blend domains with policy weights:",
                    "   - 0.40 Economic stress + 0.35 Nutrition risk + 0.25 Labor-market risk",
                    "",
                    "Higher index values indicate higher relative vulnerability compared with other districts in this run.",
                ]
            )
        )

        if summary:
            weights = summary.get("domain_weights", {})
            if weights:
                st.caption(
                    "Configured domain weights: "
                    + ", ".join(f"{name}={value:.2f}" for name, value in weights.items())
                )
            top_list = summary.get("top_10_vulnerable_districts", [])
            if top_list:
                st.caption("Top 10 vulnerable districts from latest pipeline run: " + ", ".join(str(value) for value in top_list))

    display_cols = [
        "vulnerability_rank",
        "vulnerability_tier",
        "province_name",
        "district_name",
        "vulnerability_index",
        "economic_stress_index",
        "nutrition_risk_index",
        "labor_market_risk_index",
        "women_positive_rate",
        "no_edu_rate",
        "rural_share",
        "fi_modsev_rate",
        "poor_borderline_rate",
        "stunting_rate",
        "underweight_rate",
        "wasting_rate",
        "lfs_women_unemployment_rate",
        "lfs_women_out_of_labor_force_rate",
        "lfs_women_time_underemployment_rate",
        "lfs_women_mean_monthly_cash_income",
    ]
    available_cols = [column for column in display_cols if column in filtered.columns]
    st.subheader("District vulnerability table")
    st.dataframe(
        filtered[available_cols].rename(columns={column: _column_label(column) for column in available_cols}),
        width="stretch",
        hide_index=True,
    )

    map_ready_cols = [
        "province_name",
        "district_name",
        "vulnerability_rank",
        "vulnerability_tier",
        "vulnerability_index",
        "economic_stress_index",
        "nutrition_risk_index",
        "labor_market_risk_index",
    ]
    available_map_cols = [column for column in map_ready_cols if column in filtered.columns]
    map_ready = filtered[available_map_cols].copy()

    d1, d2 = st.columns(2)
    d1.download_button(
        label="Download vulnerability map-ready CSV",
        data=map_ready.to_csv(index=False).encode("utf-8"),
        file_name="district_vulnerability_map_ready.csv",
        mime="text/csv",
    )
    d2.download_button(
        label="Download full vulnerability index CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="district_vulnerability_index_filtered.csv",
        mime="text/csv",
    )


def _render_cfsva_policy_dashboard(cfsva_df: pd.DataFrame, filters: dict[str, object]) -> None:
    cfsva_df = _coerce_numeric(
        cfsva_df,
        [
            "n_mothers",
            "fi_modsev_rate",
            "poor_borderline_rate",
            "n_children",
            "stunting_rate",
            "wasting_rate",
            "underweight_rate",
            "policy_priority_score",
            "priority_rank",
        ],
    )
    cfsva_df = _attach_province_from_district(cfsva_df, district_column="district_name")

    st.caption(
        "CFSVA 2015 maternal and child nutrition signals aggregated at district level. "
        "This view helps CSOs prioritize where policy implementation should move first."
    )

    filtered = cfsva_df.copy()
    provinces = filters["provinces"]
    if provinces:
        filtered = filtered[filtered["province_name"].isin(provinces)]
    districts = filters["districts"]
    if districts:
        filtered = filtered[filtered["district_name"].isin(districts)]
    filtered = filtered[filtered["n_mothers"] >= int(filters["min_mothers"])]
    filtered = filtered[filtered["n_children"] >= int(filters["min_children"])]

    if filtered.empty:
        st.warning("No districts match current CFSVA filters.")
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Districts", f"{len(filtered)}")
    m2.metric("Mothers covered", f"{int(filtered['n_mothers'].sum()):,}")
    m3.metric("Children covered", f"{int(filtered['n_children'].sum()):,}")
    m4.metric("Avg gender responsive budgeting score", f"{filtered['policy_priority_score'].mean():.3f}")

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Avg mod/sev food insecurity", f"{filtered['fi_modsev_rate'].mean():.1%}")
    m6.metric("Avg poor/borderline consumption", f"{filtered['poor_borderline_rate'].mean():.1%}")
    m7.metric("Avg stunting", f"{filtered['stunting_rate'].mean():.1%}")
    m8.metric("Avg underweight", f"{filtered['underweight_rate'].mean():.1%}")

    sort_metric = str(filters["sort_metric"])
    top_n = int(filters["top_n"])
    ranked = filtered.sort_values(sort_metric, ascending=False).head(top_n).copy()
    ranked["district_label"] = ranked["district_name"].astype(str)

    st.subheader(f"Top {top_n} districts by {sort_metric}")
    _render_sorted_metric_bar_chart(
        ranked,
        label_column="district_label",
        district_column="district_name",
        province_column="province_name",
        metric_column=sort_metric,
    )

    st.subheader("Food insecurity vs stunting")
    st.caption("Hover a dot to see district-level details.")
    scatter_df = filtered[
        [
            "district_name",
            "province_name",
            "n_mothers",
            "n_children",
            "fi_modsev_rate",
            "stunting_rate",
            "policy_priority_score",
        ]
    ].dropna(subset=["fi_modsev_rate", "stunting_rate"])
    scatter_chart = (
        alt.Chart(scatter_df)
        .mark_circle(size=95, opacity=0.85)
        .encode(
            x=alt.X("fi_modsev_rate:Q", title="Moderate/Severe food insecurity"),
            y=alt.Y("stunting_rate:Q", title="Stunting rate"),
            color=alt.Color("province_name:N", title="Province", scale=_province_color_scale()),
            tooltip=[
                alt.Tooltip("district_name:N", title="District"),
                alt.Tooltip("province_name:N", title="Province"),
                alt.Tooltip("n_mothers:Q", title="Mothers", format=","),
                alt.Tooltip("n_children:Q", title="Children", format=","),
                alt.Tooltip("fi_modsev_rate:Q", title="Food insecurity", format=".1%"),
                alt.Tooltip("stunting_rate:Q", title="Stunting", format=".1%"),
                alt.Tooltip("policy_priority_score:Q", title=_metric_label("policy_priority_score"), format=".3f"),
            ],
        )
        .properties(height=360)
        .configure_view(strokeWidth=0)
        .configure_axis(labelColor=UI_THEME["muted"], titleColor=UI_THEME["muted"], gridColor="#eadfce")
        .configure_legend(labelColor=UI_THEME["muted"], titleColor=UI_THEME["text"], orient="bottom")
    )
    st.altair_chart(scatter_chart, width="stretch")
    if len(scatter_df) < len(filtered):
        st.caption(
            f"{len(filtered) - len(scatter_df)} district(s) are omitted from the scatter because one or more plotted metrics are missing."
        )

    st.subheader("Risk component profile for top districts")
    components = [
        "fi_modsev_rate",
        "poor_borderline_rate",
        "stunting_rate",
        "underweight_rate",
        "wasting_rate",
    ]
    _render_ranked_component_chart(
        ranked,
        label_column="district_label",
        district_column="district_name",
        components=components,
    )

    display_cols = [
        "priority_rank",
        "district_name",
        "policy_priority_score",
        "n_mothers",
        "fi_modsev_rate",
        "poor_borderline_rate",
        "n_children",
        "stunting_rate",
        "underweight_rate",
        "wasting_rate",
    ]
    available_cols = [column for column in display_cols if column in ranked.columns]
    st.subheader("District gender responsive budgeting table")
    st.dataframe(
        ranked[available_cols].rename(columns={column: _column_label(column) for column in available_cols}),
        width="stretch",
        hide_index=True,
    )

    st.download_button(
        label="Download CFSVA gender responsive budgeting CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="cfsva_2015_district_policy_risk_filtered.csv",
        mime="text/csv",
    )


def _render_district_report_view(baseline_df: pd.DataFrame) -> None:
    local_summary = st.session_state.get("donation_local_summary")
    local_metric_map = st.session_state.get("donation_metric_map", {})
    filters = _sidebar_report_filters(baseline_df, local_summary)

    district_name = filters["district"]
    if district_name is None:
        st.info("Choose a district in the sidebar to load a district brief.")
        return

    district_matches = baseline_df.loc[baseline_df["district_name"] == district_name]
    if district_matches.empty:
        st.warning("The selected district is not available in the combined baseline.")
        return

    district_row = district_matches.iloc[0]

    local_row = None
    if filters["include_local"] and isinstance(local_summary, pd.DataFrame) and not local_summary.empty:
        local_match = local_summary.loc[local_summary["district_name"] == district_name]
        if not local_match.empty:
            local_row = local_match.iloc[0]

    st.subheader(f"One-Click District Brief: {district_name}")
    st.caption("A ready-to-share district snapshot for CSOs and policy implementers.")

    callout_kind, callout_message = _district_priority_callout(district_row)
    getattr(st, callout_kind)(callout_message)

    metrics_col, legend_col = st.columns([6, 1])

    with metrics_col:
        top1, top2, top3, top4 = st.columns(4)
        with top1:
            st.metric("Province", str(district_row.get("province_name", "n/a")))
        with top2:
            dhs_rank = district_row.get("opportunity_rank")
            st.metric("DHS rank", _format_metric_value("opportunity_rank", dhs_rank))
            _render_metric_underline("opportunity_rank", dhs_rank, baseline_df, low_is_risk=True)
        with top3:
            cfsva_rank = district_row.get("priority_rank")
            st.metric("CFSVA rank", _format_metric_value("priority_rank", cfsva_rank))
            _render_metric_underline("priority_rank", cfsva_rank, baseline_df, low_is_risk=True)
        with top4:
            policy_score = district_row.get("policy_priority_score")
            st.metric("Gender responsive budgeting score", _format_metric_value("policy_priority_score", policy_score))
            _render_metric_underline("policy_priority_score", policy_score, baseline_df, low_is_risk=False)

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            women_poverty_rate = district_row.get("women_positive_rate")
            st.metric("Women poverty rate", _format_metric_value("women_positive_rate", women_poverty_rate))
            _render_metric_underline("women_positive_rate", women_poverty_rate, baseline_df, low_is_risk=False)
        with m2:
            women_no_edu_rate = district_row.get("no_edu_rate")
            st.metric("Women no-education", _format_metric_value("no_edu_rate", women_no_edu_rate))
            _render_metric_underline("no_edu_rate", women_no_edu_rate, baseline_df, low_is_risk=False)
        with m3:
            food_insecurity_rate = district_row.get("fi_modsev_rate")
            st.metric("Food insecurity", _format_metric_value("fi_modsev_rate", food_insecurity_rate))
            _render_metric_underline("fi_modsev_rate", food_insecurity_rate, baseline_df, low_is_risk=False)
        with m4:
            stunting_rate = district_row.get("stunting_rate")
            st.metric("Stunting", _format_metric_value("stunting_rate", stunting_rate))
            _render_metric_underline("stunting_rate", stunting_rate, baseline_df, low_is_risk=False)

        m5, m6, m7, m8 = st.columns(4)
        m5.metric("Women 15-49", _format_metric_value("n_women_15_49", district_row.get("n_women_15_49")))
        m6.metric("Mothers covered", _format_metric_value("n_mothers", district_row.get("n_mothers")))
        m7.metric("Children covered", _format_metric_value("n_children", district_row.get("n_children")))
        m8.metric("Rural share", _format_metric_value("rural_share", district_row.get("rural_share")))

    with legend_col:
        _render_metric_underline_legend()

    has_lfs = any(
        pd.notna(district_row.get(metric_name))
        for metric_name in [
            "lfs_labor_risk_rank",
            "lfs_women_employment_rate",
            "lfs_women_unemployment_rate",
            "lfs_women_labor_force_participation_rate",
            "lfs_women_mean_monthly_cash_income",
        ]
    )

    if has_lfs:
        st.subheader("Women labor snapshot (LFS 2022)")
        labor_callout_rank = district_row.get("lfs_labor_risk_rank")
        if pd.notna(labor_callout_rank) and float(labor_callout_rank) <= 10:
            st.info("This district is also among the highest-risk women labor-market districts in the 2022 LFS baseline.")

        labor1, labor2, labor3, labor4 = st.columns(4)
        with labor1:
            labor_rank = district_row.get("lfs_labor_risk_rank")
            st.metric("LFS labor risk rank", _format_metric_value("lfs_labor_risk_rank", labor_rank))
            _render_metric_underline("lfs_labor_risk_rank", labor_rank, baseline_df, low_is_risk=True)
        with labor2:
            employment_rate = district_row.get("lfs_women_employment_rate")
            st.metric("Women employment", _format_metric_value("lfs_women_employment_rate", employment_rate))
            _render_metric_underline("lfs_women_employment_rate", employment_rate, baseline_df, low_is_risk=True)
        with labor3:
            unemployment_rate = district_row.get("lfs_women_unemployment_rate")
            st.metric("Women unemployment", _format_metric_value("lfs_women_unemployment_rate", unemployment_rate))
            _render_metric_underline("lfs_women_unemployment_rate", unemployment_rate, baseline_df, low_is_risk=False)
        with labor4:
            income_value = district_row.get("lfs_women_mean_monthly_cash_income")
            st.metric("Monthly cash income", _format_metric_value("lfs_women_mean_monthly_cash_income", income_value))
            _render_metric_underline("lfs_women_mean_monthly_cash_income", income_value, baseline_df, low_is_risk=True)

        labor5, labor6, labor7, labor8 = st.columns(4)
        with labor5:
            participation_rate = district_row.get("lfs_women_labor_force_participation_rate")
            st.metric("LF participation", _format_metric_value("lfs_women_labor_force_participation_rate", participation_rate))
            _render_metric_underline("lfs_women_labor_force_participation_rate", participation_rate, baseline_df, low_is_risk=True)
        with labor6:
            out_labor_rate = district_row.get("lfs_women_out_of_labor_force_rate")
            st.metric("Out of labor force", _format_metric_value("lfs_women_out_of_labor_force_rate", out_labor_rate))
            _render_metric_underline("lfs_women_out_of_labor_force_rate", out_labor_rate, baseline_df, low_is_risk=False)
        with labor7:
            underemployment_rate = district_row.get("lfs_women_time_underemployment_rate")
            st.metric("Time underemployment", _format_metric_value("lfs_women_time_underemployment_rate", underemployment_rate))
            _render_metric_underline("lfs_women_time_underemployment_rate", underemployment_rate, baseline_df, low_is_risk=False)
        with labor8:
            women_records = district_row.get("lfs_n_women_16_plus")
            st.metric("Women 16+ records", _format_metric_value("lfs_n_women_16_plus", women_records))
    else:
        st.info("No LFS district labor metrics are attached to this district yet.")

    st.subheader("Recommended CSO actions")
    for action in _generate_cso_actions(district_row):
        st.markdown(f"- {action}")
    st.caption(
        "Action suggestions are triggered from transparent baseline thresholds and are intended for triage, not automatic allocation decisions."
    )

    st.subheader("Baseline evidence snapshot")
    baseline_snapshot = pd.DataFrame(
        {
            "Metric": [
                "DHS gender responsive budgeting rank",
                "Women poverty rate",
                "Women no-education rate",
                "Rural share",
                "CFSVA gender responsive budgeting rank",
                "Moderate/severe food insecurity",
                "Poor/borderline food consumption",
                "Stunting rate",
                "Underweight rate",
            ],
            "Value": [
                _format_metric_value("opportunity_rank", district_row.get("opportunity_rank")),
                _format_metric_value("women_positive_rate", district_row.get("women_positive_rate")),
                _format_metric_value("no_edu_rate", district_row.get("no_edu_rate")),
                _format_metric_value("rural_share", district_row.get("rural_share")),
                _format_metric_value("priority_rank", district_row.get("priority_rank")),
                _format_metric_value("fi_modsev_rate", district_row.get("fi_modsev_rate")),
                _format_metric_value("poor_borderline_rate", district_row.get("poor_borderline_rate")),
                _format_metric_value("stunting_rate", district_row.get("stunting_rate")),
                _format_metric_value("underweight_rate", district_row.get("underweight_rate")),
            ],
        }
    )
    st.dataframe(baseline_snapshot, width="stretch", hide_index=True)

    if has_lfs:
        st.subheader("Women labor evidence snapshot")
        lfs_snapshot = pd.DataFrame(
            {
                "Metric": [
                    "LFS labor risk rank",
                    "Women employment rate",
                    "Women unemployment rate",
                    "Women labor-force participation",
                    "Women out of labor force",
                    "Women time underemployment",
                    "Women mean monthly cash income",
                    "Women 16+ records",
                ],
                "Value": [
                    _format_metric_value("lfs_labor_risk_rank", district_row.get("lfs_labor_risk_rank")),
                    _format_metric_value("lfs_women_employment_rate", district_row.get("lfs_women_employment_rate")),
                    _format_metric_value("lfs_women_unemployment_rate", district_row.get("lfs_women_unemployment_rate")),
                    _format_metric_value(
                        "lfs_women_labor_force_participation_rate",
                        district_row.get("lfs_women_labor_force_participation_rate"),
                    ),
                    _format_metric_value("lfs_women_out_of_labor_force_rate", district_row.get("lfs_women_out_of_labor_force_rate")),
                    _format_metric_value(
                        "lfs_women_time_underemployment_rate",
                        district_row.get("lfs_women_time_underemployment_rate"),
                    ),
                    _format_metric_value(
                        "lfs_women_mean_monthly_cash_income",
                        district_row.get("lfs_women_mean_monthly_cash_income"),
                    ),
                    _format_metric_value("lfs_n_women_16_plus", district_row.get("lfs_n_women_16_plus")),
                ],
            }
        )
        st.dataframe(lfs_snapshot, width="stretch", hide_index=True)

    if local_row is not None:
        st.subheader("Local donated data overlay")
        local_metrics = pd.DataFrame(
            {
                "Metric": ["Local sample rows"]
                + [local_metric_map.get(column, column) for column in local_row.index if str(column).startswith("local_avg_")],
                "Value": [_format_metric_value("local_sample_rows", local_row.get("local_sample_rows"))]
                + [
                    _format_metric_value(column, local_row.get(column))
                    for column in local_row.index
                    if str(column).startswith("local_avg_")
                ],
            }
        )
        st.dataframe(local_metrics, width="stretch", hide_index=True)
    else:
        st.info("No local donated dataset is attached to this district in the current session.")

    report_markdown = _build_district_report_markdown(
        district_row,
        local_row=local_row,
        local_metric_map=local_metric_map,
    )

    download_col1, download_col2 = st.columns(2)
    download_col1.download_button(
        label="One-Click Download District Brief (.md)",
        data=report_markdown.encode("utf-8"),
        file_name=f"district_brief_{_slugify_column(district_name)}.md",
        mime="text/markdown",
    )
    district_export = baseline_df.loc[baseline_df["district_name"] == district_name]
    download_col2.download_button(
        label="Download District Baseline Row (.csv)",
        data=district_export.to_csv(index=False).encode("utf-8"),
        file_name=f"district_baseline_{_slugify_column(district_name)}.csv",
        mime="text/csv",
    )

    st.subheader("Brief preview")
    st.markdown(report_markdown)


def _render_donation_dashboard(baseline_df: pd.DataFrame) -> None:
    st.subheader("Data Donation Merge")
    st.caption(
        "Upload a small CSV or XLSX from field work. The app standardizes district names, aggregates numeric metrics by district, and merges them with the national baseline."
    )

    template_df = pd.DataFrame(
        {
            "district_name": ["Nyabihu", "Rutsiro", "Gisagara"],
            "households_surveyed": [42, 35, 28],
            "women_service_access_rate": [0.58, 0.41, 0.66],
            "nutrition_screen_positive_rate": [0.22, 0.31, 0.18],
            "safe_water_access_rate": [0.47, 0.39, 0.62],
        }
    )

    st.download_button(
        label="Download data-donation template CSV",
        data=template_df.to_csv(index=False).encode("utf-8"),
        file_name="cso_data_donation_template.csv",
        mime="text/csv",
    )

    uploaded_file = _sidebar_donation_file_uploader()
    if uploaded_file is None:
        st.info("No local survey file uploaded yet. Use the sidebar to attach a CSV or XLSX file.")
        st.session_state.pop("donation_local_summary", None)
        st.session_state.pop("donation_metric_map", None)
        st.session_state.pop("donation_merged_baseline", None)
        return

    try:
        local_df = _read_uploaded_donation_frame(uploaded_file)
    except Exception as exc:
        st.error(f"Could not read the uploaded file: {exc}")
        return

    controls = _sidebar_donation_config(local_df)
    selected_metrics = controls["selected_metrics"]
    if not selected_metrics:
        st.warning("Select at least one numeric metric in the sidebar to build the donation merge.")
        st.dataframe(local_df.head(20), width="stretch", hide_index=True)
        return

    metric_quality = _build_metric_quality_table(local_df, selected_metrics)

    try:
        local_summary, unmatched_districts, metric_map = _aggregate_local_donation(
            local_df,
            district_column=controls["district_column"],
            metric_columns=selected_metrics,
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    merged = _merge_local_with_baseline(baseline_df, local_summary)
    st.session_state["donation_local_summary"] = local_summary
    st.session_state["donation_metric_map"] = metric_map
    st.session_state["donation_merged_baseline"] = merged

    preview_df = merged.copy() if controls["show_all_baseline"] else merged[merged["local_data_present"]].copy()
    matched_row_count = int(local_df[controls["district_column"]].apply(_normalize_district_value).notna().sum())
    matched_row_share = matched_row_count / len(local_df) if len(local_df) else 0.0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Uploaded rows", f"{len(local_df):,}")
    k2.metric("Matched rows", f"{matched_row_count:,}")
    k3.metric("Matched row share", f"{matched_row_share:.1%}")
    k4.metric("Matched districts", f"{local_summary['district_name'].nunique()}")
    k5.metric("Local metrics merged", f"{len(metric_map)}")

    st.success(
        "Local data is now attached to the session baseline. You can open the District One-Click Report view and include local evidence for matched districts."
    )

    if unmatched_districts:
        st.warning(
            "Some uploaded district names did not match the supported 30 districts: "
            + ", ".join(unmatched_districts[:12])
            + (" ..." if len(unmatched_districts) > 12 else "")
        )
        with st.expander("Review all unmatched district labels", expanded=False):
            st.dataframe(pd.DataFrame({"Unmatched district label": unmatched_districts}), width="stretch", hide_index=True)

    with st.expander("Metric quality before district aggregation", expanded=False):
        st.caption("Rows that cannot be coerced to numeric values are ignored when district averages are computed.")
        display_quality = metric_quality.rename(
            columns={
                "metric_name": "Metric",
                "rows_with_values": "Rows with values",
                "numeric_rows": "Numeric after coercion",
                "lost_after_coercion": "Lost during coercion",
                "numeric_share": "Usable row share",
            }
        )
        display_quality["Usable row share"] = display_quality["Usable row share"].map(lambda value: f"{value:.1%}")
        st.dataframe(display_quality, width="stretch", hide_index=True)

    st.subheader("Uploaded data preview")
    st.dataframe(local_df.head(20), width="stretch", hide_index=True)

    st.subheader("District-level local aggregation")
    st.dataframe(
        local_summary.rename(columns={column: _column_label(column) for column in local_summary.columns}),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Merged baseline with local donation")
    display_cols = [
        "province_name",
        "district_name",
        "opportunity_rank",
        "opportunity_score",
        "priority_rank",
        "policy_priority_score",
        "local_data_present",
        "local_sample_rows",
    ] + list(metric_map.keys())
    available_cols = [column for column in display_cols if column in preview_df.columns]
    st.dataframe(
        preview_df[available_cols].rename(columns={column: _column_label(column) for column in available_cols}),
        width="stretch",
        hide_index=True,
    )

    download_col1, download_col2 = st.columns(2)
    download_col1.download_button(
        label="Download local aggregation CSV",
        data=local_summary.to_csv(index=False).encode("utf-8"),
        file_name="local_cso_donation_by_district.csv",
        mime="text/csv",
    )
    download_col2.download_button(
        label="Download merged baseline CSV",
        data=merged.to_csv(index=False).encode("utf-8"),
        file_name="baseline_plus_local_donation.csv",
        mime="text/csv",
    )


def main() -> None:
    st.set_page_config(
        page_title="Rwanda Gender Data Visibility Intelligence Platform",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _render_app_styles()

    active_view = _sidebar_navigation()
    opportunity_summary = _load_json_summary(str(OPPORTUNITY_SUMMARY_PATH)) if OPPORTUNITY_SUMMARY_PATH.exists() else {}
    cfsva_summary = _load_json_summary(str(CFSVA_POLICY_SUMMARY_PATH)) if CFSVA_POLICY_SUMMARY_PATH.exists() else {}
    _render_app_header(active_view, opportunity_summary, cfsva_summary)

    if active_view == "DHS Gender Responsive Budgeting View":
        st.subheader("Women 15-49 gender responsive budgeting priorities by district (DHS 2014/15)")
        if not OPPORTUNITY_PATH.exists():
            st.error("No DHS gender responsive budgeting file found. Run scripts/run_women_opportunity.py first.")
        else:
            op_df = _load_data(str(OPPORTUNITY_PATH))
            filters = _sidebar_opportunity_filters(op_df)
            _render_opportunity_dashboard(op_df, filters)
        return

    if active_view == "LFS Women Labor View":
        st.subheader("Women labor-market conditions by district (LFS 2022)")
        if not LFS_DISTRICT_PATH.exists():
            st.error(
                "No LFS district labor file found. "
                "Run scripts/run_lfs_district_analytics.py first."
            )
        else:
            lfs_df = _load_lfs_district_signals(str(LFS_DISTRICT_PATH))
            if LFS_DISTRICT_SUMMARY_PATH.exists():
                lfs_summary = _load_json_summary(str(LFS_DISTRICT_SUMMARY_PATH))
                st.caption(
                    "Processed LFS coverage: "
                    f"{_format_whole_number(lfs_summary.get('women_rows_16_plus'))} women 16+ records across "
                    f"{_format_whole_number(lfs_summary.get('districts'))} districts."
                )
            filters = _sidebar_lfs_filters(lfs_df)
            _render_lfs_dashboard(lfs_df, filters)
        return

    if active_view == "District Vulnerability Index View":
        st.subheader("District vulnerability index (DHS + CFSVA + LFS)")
        if not VULNERABILITY_PATH.exists():
            st.error(
                "No district vulnerability index file found. "
                "Run scripts/run_district_vulnerability_index.py first."
            )
        else:
            vulnerability_df = _load_vulnerability_index(str(VULNERABILITY_PATH))
            vulnerability_summary = (
                _load_json_summary(str(VULNERABILITY_SUMMARY_PATH)) if VULNERABILITY_SUMMARY_PATH.exists() else {}
            )
            if vulnerability_summary:
                st.caption(
                    "Latest pipeline output: "
                    f"{_format_whole_number(vulnerability_summary.get('rows_ranked'))} ranked districts, "
                    f"average index {_format_metric_value('vulnerability_index', vulnerability_summary.get('avg_vulnerability_index'))}."
                )
            filters = _sidebar_vulnerability_filters(vulnerability_df)
            _render_vulnerability_dashboard(vulnerability_df, filters, vulnerability_summary)
        return

    if active_view == "CFSVA Nutrition & Food Security Priority View":
        st.subheader("District gender responsive budgeting signals from CFSVA 2015")
        if not CFSVA_POLICY_PATH.exists():
            st.error(
                "No CFSVA district gender responsive budgeting file found. "
                "Run the CFSVA processing step first."
            )
        else:
            cfsva_df = _load_data(str(CFSVA_POLICY_PATH)).rename(columns={"S0_D_Dist": "district_name"})
            cfsva_df = _attach_province_from_district(cfsva_df, district_column="district_name")
            filters = _sidebar_cfsva_filters(cfsva_df)
            _render_cfsva_policy_dashboard(cfsva_df, filters)
        return

    if not OPPORTUNITY_PATH.exists() or not CFSVA_POLICY_PATH.exists():
        st.error("Both DHS and CFSVA processed outputs are required for the district brief and data-donation features.")
        return

    baseline_df = _load_combined_baseline(str(OPPORTUNITY_PATH), str(CFSVA_POLICY_PATH))
    if baseline_df.empty:
        st.error("The combined district baseline is empty. Rebuild the processed DHS and CFSVA outputs first.")
        return

    if LFS_DISTRICT_PATH.exists():
        lfs_for_report = _load_lfs_district_signals(str(LFS_DISTRICT_PATH))
        baseline_df = _merge_opportunity_with_lfs(baseline_df, lfs_for_report)

    if active_view == "District One-Click Report":
        _render_district_report_view(baseline_df)
    else:
        _render_donation_dashboard(baseline_df)


if __name__ == "__main__":
    main()
