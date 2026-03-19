from datetime import datetime
from io import BytesIO
from pathlib import Path
import re

import altair as alt
import pandas as pd
import streamlit as st

OPPORTUNITY_PATH = Path("data/processed/women_opportunity_districts.csv")
CFSVA_POLICY_PATH = Path("data/processed/cfsva_2015_district_policy_risk.csv")

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


def _slugify_column(name: str) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", str(name).strip().lower())
    return cleaned.strip("_") or "metric"


def _metric_label(metric: str) -> str:
    cleaned = metric
    for prefix in ["local_avg_", "local_sum_"]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    return cleaned.replace("_", " ").title()


def _metric_format(metric: str) -> str:
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
            color=alt.Color(f"{province_column}:N", title="Province"),
            tooltip=[
                alt.Tooltip(f"{district_column}:N", title="District"),
                alt.Tooltip(f"{province_column}:N", title="Province"),
                alt.Tooltip(f"{metric_column}:Q", title=_metric_label(metric_column), format=_metric_format(metric_column)),
            ],
        )
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

    chart = (
        alt.Chart(long_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{label_column}:N", sort=order, title="District"),
            y=alt.Y("value:Q", title="Rate"),
            color=alt.Color("component:N", title="Risk component"),
            tooltip=[
                alt.Tooltip(f"{district_column}:N", title="District"),
                alt.Tooltip("component:N", title="Component"),
                alt.Tooltip("value:Q", title="Rate", format=".1%"),
            ],
        )
    )
    st.altair_chart(chart, width="stretch")


def _sidebar_navigation() -> str:
    with st.sidebar:
        st.header("Navigation")
        view = st.radio(
            "Select analysis view",
            options=[
                "DHS Opportunity View",
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
        sel_provinces = st.multiselect(
            "Province",
            options=all_provinces,
            default=all_provinces,
            key="op_provinces",
        )

        district_source = op_df.copy()
        if sel_provinces:
            district_source = district_source[district_source["province_name"].isin(sel_provinces)]
        all_districts = sorted(district_source["district_name"].dropna().astype(str).unique().tolist())
        sel_districts = st.multiselect(
            "District",
            options=all_districts,
            default=all_districts,
            key="op_districts",
        )

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
        selected_provinces = st.multiselect(
            "Province",
            options=all_provinces,
            default=all_provinces,
            key="cf_provinces",
        )

        district_source = cfsva_df.copy()
        if selected_provinces:
            district_source = district_source[district_source["province_name"].isin(selected_provinces)]
        all_districts = sorted(district_source["district_name"].dropna().astype(str).unique().tolist())
        selected_districts = st.multiselect(
            "District",
            options=all_districts,
            default=all_districts,
            key="cf_districts",
        )
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


def _sidebar_report_filters(baseline_df: pd.DataFrame, local_summary: pd.DataFrame | None) -> dict[str, object]:
    with st.sidebar:
        st.markdown("---")
        st.subheader("District Brief")

        province_options = sorted(baseline_df["province_name"].dropna().astype(str).unique().tolist())
        selected_province = st.selectbox("Province", options=province_options, key="report_province")

        district_options = sorted(
            baseline_df.loc[baseline_df["province_name"] == selected_province, "district_name"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
        selected_district = st.selectbox("District", options=district_options, key="report_district")

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
        return "warning", "This district is high-priority in both DHS opportunity and CFSVA nutrition-food-security baselines."
    if pd.notna(policy_rank) and policy_rank <= 10:
        return "info", "This district is especially urgent on the CFSVA policy-priority baseline."
    if pd.notna(op_rank) and op_rank <= 10:
        return "info", "This district is especially urgent on the DHS women opportunity baseline."
    return "success", "This district is lower-ranked than the most urgent hotspots, but still available for local targeting and monitoring."


def _generate_cso_actions(row: pd.Series) -> list[str]:
    actions: list[str] = []

    if pd.notna(row.get("policy_priority_score")) and row.get("policy_priority_score") >= 0.35:
        actions.append("Scale district-level food security response together with maternal and child nutrition services.")
    if pd.notna(row.get("women_positive_rate")) and row.get("women_positive_rate") >= 0.35:
        actions.append("Prioritize women-focused livelihoods, savings groups, and social protection or cash-support programming.")
    if pd.notna(row.get("no_edu_rate")) and row.get("no_edu_rate") >= 0.12:
        actions.append("Add adult literacy and girls' retention support because education deprivation remains material.")
    if pd.notna(row.get("stunting_rate")) and row.get("stunting_rate") >= 0.35:
        actions.append("Pair food-support programs with child growth monitoring, nutrition counseling, and WASH interventions.")
    if pd.notna(row.get("poor_borderline_rate")) and row.get("poor_borderline_rate") >= 0.35:
        actions.append("Combine immediate consumption support with agriculture and household resilience activities.")
    if pd.notna(row.get("rural_share")) and row.get("rural_share") >= 0.80:
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
            f"{district} ranks {_format_metric_value('opportunity_rank', row.get('opportunity_rank'))}/30 on the DHS women opportunity baseline "
            f"and {_format_metric_value('priority_rank', row.get('priority_rank'))}/30 on the CFSVA policy-priority baseline."
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
        f"- Policy priority score: {_format_metric_value('policy_priority_score', row.get('policy_priority_score'))}",
        "",
        "## Recommended CSO Actions",
    ]

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
            "- DHS 2014/15 women opportunity baseline",
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
        "Opportunity score ranks districts by unmet economic need (poverty gap, education gap)."
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
    extra1.metric("Avg opportunity score", f"{filtered['opportunity_score'].mean():.3f}")
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
            color=alt.Color("province_name:N", title="Province"),
            tooltip=[
                alt.Tooltip("district_name:N", title="District"),
                alt.Tooltip("province_name:N", title="Province"),
                alt.Tooltip("n_women_15_49:Q", title="Women 15-49", format=","),
                alt.Tooltip("women_positive_rate:Q", title="Poverty rate", format=".1%"),
                alt.Tooltip("no_edu_rate:Q", title="No-education rate", format=".1%"),
                alt.Tooltip("opportunity_score:Q", title="Opportunity score", format=".3f"),
            ],
        )
    )
    st.altair_chart(scatter_chart, width="stretch")

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
    st.dataframe(ranked[available_cols], width="stretch", hide_index=True)

    st.download_button(
        label="Download opportunity map CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="women_opportunity_districts.csv",
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
    m4.metric("Avg policy score", f"{filtered['policy_priority_score'].mean():.3f}")

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
            color=alt.Color("province_name:N", title="Province"),
            tooltip=[
                alt.Tooltip("district_name:N", title="District"),
                alt.Tooltip("province_name:N", title="Province"),
                alt.Tooltip("n_mothers:Q", title="Mothers", format=","),
                alt.Tooltip("n_children:Q", title="Children", format=","),
                alt.Tooltip("fi_modsev_rate:Q", title="Food insecurity", format=".1%"),
                alt.Tooltip("stunting_rate:Q", title="Stunting", format=".1%"),
                alt.Tooltip("policy_priority_score:Q", title="Policy score", format=".3f"),
            ],
        )
    )
    st.altair_chart(scatter_chart, width="stretch")

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
    st.subheader("District policy-priority table")
    st.dataframe(ranked[available_cols], width="stretch", hide_index=True)

    st.download_button(
        label="Download CFSVA policy CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="cfsva_2015_district_policy_risk_filtered.csv",
        mime="text/csv",
    )


def _render_district_report_view(baseline_df: pd.DataFrame) -> None:
    local_summary = st.session_state.get("donation_local_summary")
    local_metric_map = st.session_state.get("donation_metric_map", {})
    filters = _sidebar_report_filters(baseline_df, local_summary)

    district_name = filters["district"]
    district_row = baseline_df.loc[baseline_df["district_name"] == district_name].iloc[0]

    local_row = None
    if filters["include_local"] and isinstance(local_summary, pd.DataFrame) and not local_summary.empty:
        local_match = local_summary.loc[local_summary["district_name"] == district_name]
        if not local_match.empty:
            local_row = local_match.iloc[0]

    st.subheader(f"One-Click District Brief: {district_name}")
    st.caption("A ready-to-share district snapshot for CSOs and policy implementers.")

    callout_kind, callout_message = _district_priority_callout(district_row)
    getattr(st, callout_kind)(callout_message)

    top1, top2, top3, top4 = st.columns(4)
    top1.metric("Province", str(district_row.get("province_name", "n/a")))
    top2.metric("DHS rank", _format_metric_value("opportunity_rank", district_row.get("opportunity_rank")))
    top3.metric("CFSVA rank", _format_metric_value("priority_rank", district_row.get("priority_rank")))
    top4.metric("Policy score", _format_metric_value("policy_priority_score", district_row.get("policy_priority_score")))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Women poverty rate", _format_metric_value("women_positive_rate", district_row.get("women_positive_rate")))
    m2.metric("Women no-education", _format_metric_value("no_edu_rate", district_row.get("no_edu_rate")))
    m3.metric("Food insecurity", _format_metric_value("fi_modsev_rate", district_row.get("fi_modsev_rate")))
    m4.metric("Stunting", _format_metric_value("stunting_rate", district_row.get("stunting_rate")))

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Women 15-49", _format_metric_value("n_women_15_49", district_row.get("n_women_15_49")))
    m6.metric("Mothers covered", _format_metric_value("n_mothers", district_row.get("n_mothers")))
    m7.metric("Children covered", _format_metric_value("n_children", district_row.get("n_children")))
    m8.metric("Rural share", _format_metric_value("rural_share", district_row.get("rural_share")))

    st.subheader("Recommended CSO actions")
    for action in _generate_cso_actions(district_row):
        st.markdown(f"- {action}")

    st.subheader("Baseline evidence snapshot")
    baseline_snapshot = pd.DataFrame(
        {
            "Metric": [
                "DHS opportunity rank",
                "Women poverty rate",
                "Women no-education rate",
                "Rural share",
                "CFSVA policy rank",
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

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Uploaded rows", f"{len(local_df):,}")
    k2.metric("Matched districts", f"{local_summary['district_name'].nunique()}")
    k3.metric("Unmatched district labels", f"{len(unmatched_districts)}")
    k4.metric("Local metrics merged", f"{len(metric_map)}")

    st.success(
        "Local data is now attached to the session baseline. You can open the District One-Click Report view and include local evidence for matched districts."
    )

    if unmatched_districts:
        st.warning(
            "Some uploaded district names did not match the supported 30 districts: "
            + ", ".join(unmatched_districts[:12])
            + (" ..." if len(unmatched_districts) > 12 else "")
        )

    st.subheader("Uploaded data preview")
    st.dataframe(local_df.head(20), width="stretch", hide_index=True)

    st.subheader("District-level local aggregation")
    st.dataframe(local_summary, width="stretch", hide_index=True)

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
    st.dataframe(preview_df[available_cols], width="stretch", hide_index=True)

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
    st.set_page_config(page_title="Rwanda Women Policy Dashboard", layout="wide")
    st.title("Rwanda Women Policy Dashboard")

    st.caption(
        "Use the fixed left sidebar for navigation and filters. "
        "The dashboard now includes a district one-click brief and a CSO data-donation merge flow."
    )

    active_view = _sidebar_navigation()

    if active_view == "DHS Opportunity View":
        st.subheader("Women 15-49 economic opportunity by district (DHS 2014/15)")
        if not OPPORTUNITY_PATH.exists():
            st.error("No opportunity map found. Run scripts/run_women_opportunity.py first.")
        else:
            op_df = _load_data(str(OPPORTUNITY_PATH))
            filters = _sidebar_opportunity_filters(op_df)
            _render_opportunity_dashboard(op_df, filters)
        return

    if active_view == "CFSVA Nutrition & Food Security Priority View":
        st.subheader("District policy-priority signals from CFSVA 2015")
        if not CFSVA_POLICY_PATH.exists():
            st.error(
                "No CFSVA district policy score file found. "
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

    if active_view == "District One-Click Report":
        _render_district_report_view(baseline_df)
    else:
        _render_donation_dashboard(baseline_df)


if __name__ == "__main__":
    main()
