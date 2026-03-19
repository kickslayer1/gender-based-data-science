from pathlib import Path

import pandas as pd
import streamlit as st

DEFAULT_DISTRICT_PATH = Path("data/processed/rwanda_district_visibility.csv")
DEFAULT_SECTOR_PATH = Path("data/processed/rwanda_sector_visibility.csv")
OPPORTUNITY_PATH = Path("data/processed/women_opportunity_districts.csv")


def _resolve_source_path() -> Path | None:
    if DEFAULT_DISTRICT_PATH.exists():
        return DEFAULT_DISTRICT_PATH
    if DEFAULT_SECTOR_PATH.exists():
        return DEFAULT_SECTOR_PATH
    return None


def _resolve_columns(dataframe: pd.DataFrame) -> dict[str, str | None]:
    columns = set(dataframe.columns)

    province_column = None
    if "province" in columns:
        province_column = "province"
    elif "hv024" in columns:
        province_column = "hv024"

    district_column = None
    if "district" in columns:
        district_column = "district"
    elif "shdistrict" in columns:
        district_column = "shdistrict"

    sector_column = "sector" if "sector" in columns else None

    return {
        "province": province_column,
        "district": district_column,
        "sector": sector_column,
    }


@st.cache_data(show_spinner=False)
def _load_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def _coerce_types(dataframe: pd.DataFrame) -> pd.DataFrame:
    frame = dataframe.copy()

    numeric_columns = [
        "n_total",
        "women_count",
        "women_share",
        "n_women",
        "avg_available_features",
        "feature_coverage_ratio",
        "sample_trust_score",
        "feature_count_trust_score",
        "feature_coverage_trust_score",
        "trust_score",
        "visibility_score",
    ]
    for column in numeric_columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if "trusted" in frame.columns:
        frame["trusted"] = (
            frame["trusted"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": True, "false": False, "1": True, "0": False})
            .fillna(False)
        )

    return frame


def _build_group_label(dataframe: pd.DataFrame, columns: dict[str, str | None]) -> pd.Series:
    district_column = columns["district"]
    province_column = columns["province"]
    sector_column = columns["sector"]

    if sector_column and district_column:
        return (
            dataframe[province_column].astype(str)
            + " | "
            + dataframe[district_column].astype(str)
            + " | "
            + dataframe[sector_column].astype(str)
            if province_column
            else dataframe[district_column].astype(str) + " | " + dataframe[sector_column].astype(str)
        )

    if district_column and province_column:
        return dataframe[province_column].astype(str) + " | " + dataframe[district_column].astype(str)

    if district_column:
        return dataframe[district_column].astype(str)

    if province_column:
        return dataframe[province_column].astype(str)

    return pd.Series([f"group_{idx}" for idx in range(len(dataframe))], index=dataframe.index)


def _render_visibility_tab(dataframe: pd.DataFrame, columns: dict[str, str | None]) -> None:
    required = {"women_share", "trust_score", "visibility_score"}
    missing = [column for column in required if column not in dataframe.columns]
    if missing:
        st.error("Missing required metric columns: " + ", ".join(missing))
        return

    province_column = columns["province"]
    district_column = columns["district"]

    selected_provinces: list[str] = []
    if province_column:
        province_values = sorted(dataframe[province_column].dropna().astype(str).unique().tolist())
        selected_provinces = st.sidebar.multiselect(
            "Province",
            options=province_values,
            default=province_values,
            key="vis_provinces",
        )

    selected_districts: list[str] = []
    if district_column:
        district_values = sorted(dataframe[district_column].dropna().astype(str).unique().tolist())
        selected_districts = st.sidebar.multiselect(
            "District",
            options=district_values,
            default=district_values,
            key="vis_districts",
        )

    trusted_only = st.sidebar.checkbox("Trusted groups only", value=False, key="vis_trusted")

    max_women = int(dataframe["n_women"].max()) if "n_women" in dataframe.columns else 0
    min_women = st.sidebar.slider(
        "Minimum women count",
        min_value=0,
        max_value=max(max_women, 1),
        value=0,
        key="vis_min_women",
    )

    sort_metric = st.sidebar.selectbox(
        "Sort metric",
        options=["visibility_score", "trust_score", "women_share", "n_women"],
        index=0,
        key="vis_sort",
    )
    top_n = st.sidebar.slider("Top groups to show", min_value=5, max_value=30, value=15, key="vis_top_n")

    filtered = dataframe.copy()
    if province_column and selected_provinces:
        filtered = filtered[filtered[province_column].astype(str).isin(selected_provinces)]
    if district_column and selected_districts:
        filtered = filtered[filtered[district_column].astype(str).isin(selected_districts)]
    if trusted_only and "trusted" in filtered.columns:
        filtered = filtered[filtered["trusted"]]
    if "n_women" in filtered.columns:
        filtered = filtered[filtered["n_women"] >= min_women]

    if filtered.empty:
        st.warning("No rows match current filters.")
        return

    filtered = filtered.copy()
    filtered["group_label"] = _build_group_label(filtered, columns)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Groups", f"{len(filtered)}")
    col2.metric("Avg visibility", f"{filtered['visibility_score'].mean():.3f}")
    col3.metric("Avg trust", f"{filtered['trust_score'].mean():.3f}")
    col4.metric("Avg women share", f"{filtered['women_share'].mean():.3f}")

    ranked = filtered.sort_values(sort_metric, ascending=False).head(top_n)

    st.subheader("Top groups")
    st.bar_chart(ranked.set_index("group_label")[[sort_metric]])

    st.subheader("Trust vs women share")
    scatter_columns = ["group_label", "women_share", "trust_score"]
    if "trusted" in filtered.columns:
        scatter_columns.append("trusted")
    st.scatter_chart(
        filtered[scatter_columns],
        x="women_share",
        y="trust_score",
        color="trusted" if "trusted" in scatter_columns else None,
    )

    st.subheader("Filtered table")
    st.dataframe(ranked, use_container_width=True, hide_index=True)

    st.download_button(
        label="Download filtered CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="rwanda_visibility_filtered.csv",
        mime="text/csv",
    )


def _render_opportunity_tab(op_df: pd.DataFrame) -> None:
    st.caption(
        "Women aged 15-49 from Rwanda DHS 2014/15 (RWHR70FL). "
        "Opportunity score ranks districts by unmet economic need (poverty gap, education gap)."
    )

    with st.sidebar:
        st.markdown("---")
        st.subheader("Opportunity filters")
        all_provinces = sorted(op_df["province_name"].dropna().unique().tolist())
        sel_provinces = st.multiselect(
            "Province",
            options=all_provinces,
            default=all_provinces,
            key="op_provinces",
        )
        max_n = int(op_df["n_women_15_49"].max())
        min_n = st.slider(
            "Min women 15-49 in district",
            min_value=0,
            max_value=max_n,
            value=0,
            key="op_min_n",
        )
        op_sort = st.selectbox(
            "Sort metric",
            options=["opportunity_score", "women_positive_rate", "no_edu_rate", "rural_share"],
            index=0,
            key="op_sort",
        )
        op_top_n = st.slider("Districts to show", min_value=5, max_value=30, value=15, key="op_top_n")

    filtered = op_df.copy()
    if sel_provinces:
        filtered = filtered[filtered["province_name"].isin(sel_provinces)]
    filtered = filtered[filtered["n_women_15_49"] >= min_n]

    if filtered.empty:
        st.warning("No districts match current filters.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Districts", f"{len(filtered)}")
    col2.metric("Women 15-49", f"{filtered['n_women_15_49'].sum():,}")
    col3.metric("Avg poverty rate", f"{filtered['women_positive_rate'].mean():.1%}")
    col4.metric("Avg no-education", f"{filtered['no_edu_rate'].mean():.1%}")

    ranked = filtered.sort_values(op_sort, ascending=False).head(op_top_n)
    ranked["label"] = ranked["province_name"] + " | " + ranked["district_name"]

    st.subheader(f"Top {op_top_n} priority districts by {op_sort}")
    st.bar_chart(ranked.set_index("label")[[op_sort]])

    st.subheader("Poverty rate vs no-education rate by district")
    scatter_df = filtered[["district_name", "women_positive_rate", "no_edu_rate", "province_name"]].copy()
    scatter_df = scatter_df.rename(
        columns={"women_positive_rate": "poverty_rate_women", "province_name": "province"}
    )
    st.scatter_chart(scatter_df, x="poverty_rate_women", y="no_edu_rate", color="province")

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
    available_cols = [c for c in display_cols if c in ranked.columns]
    st.subheader("District detail table")
    st.dataframe(ranked[available_cols], use_container_width=True, hide_index=True)

    st.download_button(
        label="Download opportunity map CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="women_opportunity_districts.csv",
        mime="text/csv",
    )


def main() -> None:
    st.set_page_config(page_title="Rwanda Women Dashboard", layout="wide")
    st.title("Rwanda Women-Centred Data Dashboard")

    tab_vis, tab_op = st.tabs(["Data Visibility", "Opportunity Map"])

    # ── Visibility tab ────────────────────────────────────────────────────────
    with tab_vis:
        st.subheader("District / sector trust and visibility")
        source_path = _resolve_source_path()
        if source_path is None:
            st.error("No visibility file found. Run scripts/run_rwanda_visibility.py first.")
        else:
            with st.sidebar:
                st.header("Visibility filters")
                st.caption("Source: " + str(source_path))
            vis_df = _coerce_types(_load_data(str(source_path)))
            _render_visibility_tab(vis_df, _resolve_columns(vis_df))

    # ── Opportunity tab ───────────────────────────────────────────────────────
    with tab_op:
        st.subheader("Women 15-49 economic opportunity by district (DHS 2014/15)")
        if not OPPORTUNITY_PATH.exists():
            st.error("No opportunity map found. Run scripts/run_women_opportunity.py first.")
        else:
            op_df = _load_data(str(OPPORTUNITY_PATH))
            _render_opportunity_tab(op_df)


if __name__ == "__main__":
    main()
