import importlib
import sys
import types

import pandas as pd
import pytest


def _load_dashboard_module():
    if "altair" not in sys.modules:
        altair_stub = types.ModuleType("altair")
        altair_stub.Scale = object
        sys.modules["altair"] = altair_stub

    if "streamlit" not in sys.modules:
        streamlit_stub = types.ModuleType("streamlit")

        def cache_data(*args, **kwargs):
            def decorator(function):
                return function

            return decorator

        streamlit_stub.cache_data = cache_data
        streamlit_stub.session_state = {}
        sys.modules["streamlit"] = streamlit_stub

    sys.modules.pop("scripts.run_dashboard", None)
    return importlib.import_module("scripts.run_dashboard")


dashboard = _load_dashboard_module()


def test_normalize_district_value_handles_common_variants() -> None:
    assert dashboard._normalize_district_value("District of Nyabihu") == "Nyabihu"
    assert dashboard._normalize_district_value("NYARUGURU district") == "Nyaruguru"
    assert dashboard._normalize_district_value("gasabo") == "Gasabo"
    assert dashboard._normalize_district_value("unknown place") is None


def test_shared_priority_districts_preserves_opportunity_order() -> None:
    opportunity_summary = {
        "top_5_opportunity_districts": ["Nyabihu", "Gisagara", "Rutsiro", "Nyanza", "Burera"],
    }
    cfsva_summary = {
        "top_10_districts": ["Rutsiro", "Nyabihu", "Rusizi", "Burera"],
    }

    assert dashboard._shared_priority_districts(opportunity_summary, cfsva_summary) == ["Nyabihu", "Rutsiro", "Burera"]


def test_district_options_for_province_returns_sorted_unique_names() -> None:
    baseline_df = pd.DataFrame(
        {
            "province_name": ["West", "West", "West", "East"],
            "district_name": ["Rutsiro", "Nyabihu", "Nyabihu", "Ngoma"],
        }
    )

    assert dashboard._district_options_for_province(baseline_df, "West") == ["Nyabihu", "Rutsiro"]
    assert dashboard._district_options_for_province(baseline_df, "North") == []


def test_build_metric_quality_table_reports_numeric_loss() -> None:
    local_df = pd.DataFrame(
        {
            "women_service_access_rate": [0.45, "0.80", "bad", None],
            "nutrition_screen_positive_rate": [0.11, 0.22, 0.33, 0.44],
        }
    )

    quality_table = dashboard._build_metric_quality_table(
        local_df,
        ["women_service_access_rate", "nutrition_screen_positive_rate"],
    )

    access_row = quality_table.loc[quality_table["metric_name"] == "women_service_access_rate"].iloc[0]
    assert access_row["rows_with_values"] == 3
    assert access_row["numeric_rows"] == 2
    assert access_row["lost_after_coercion"] == 1
    assert access_row["numeric_share"] == pytest.approx(0.5)

    nutrition_row = quality_table.loc[quality_table["metric_name"] == "nutrition_screen_positive_rate"].iloc[0]
    assert nutrition_row["rows_with_values"] == 4
    assert nutrition_row["numeric_rows"] == 4
    assert nutrition_row["lost_after_coercion"] == 0
    assert nutrition_row["numeric_share"] == pytest.approx(1.0)


def test_resolve_all_filter_selection_returns_full_list_for_all_or_empty() -> None:
    available_values = ["East", "North", "West"]

    assert dashboard._resolve_all_filter_selection(["All"], available_values) == available_values
    assert dashboard._resolve_all_filter_selection([], available_values) == available_values
    assert dashboard._resolve_all_filter_selection(["West"], available_values) == ["West"]


def test_prepare_all_filter_state_sanitizes_invalid_values() -> None:
    dashboard.st.session_state.clear()
    dashboard._prepare_all_filter_state("op_provinces", ["East", "West"])
    assert dashboard.st.session_state["op_provinces"] == ["All"]
    assert dashboard.st.session_state["op_provinces__previous"] == ["All"]

    dashboard.st.session_state["op_provinces"] = ["West", "Invalid"]
    dashboard._prepare_all_filter_state("op_provinces", ["East", "West"])
    assert dashboard.st.session_state["op_provinces"] == ["West"]


def test_prepare_all_filter_state_all_toggles_with_user_intent() -> None:
    dashboard.st.session_state.clear()

    dashboard.st.session_state["op_provinces"] = ["All"]
    dashboard.st.session_state["op_provinces__previous"] = ["All"]
    dashboard._prepare_all_filter_state("op_provinces", ["East", "West"])
    assert dashboard.st.session_state["op_provinces"] == ["All"]

    dashboard.st.session_state["op_provinces"] = ["All", "West"]
    dashboard._prepare_all_filter_state("op_provinces", ["East", "West"])
    assert dashboard.st.session_state["op_provinces"] == ["West"]

    dashboard.st.session_state["op_provinces"] = ["West", "All"]
    dashboard._prepare_all_filter_state("op_provinces", ["East", "West"])
    assert dashboard.st.session_state["op_provinces"] == ["All"]

    dashboard.st.session_state["op_provinces"] = ["All", "East", "West"]
    dashboard._prepare_all_filter_state("op_provinces", ["East", "West"])
    assert dashboard.st.session_state["op_provinces"] == ["East", "West"]


def test_normalize_province_value_maps_known_labels() -> None:
    assert dashboard._normalize_province_value("Kigali city") == "Kigali"
    assert dashboard._normalize_province_value("Western Province") == "West"
    assert dashboard._normalize_province_value("East") == "East"
    assert dashboard._normalize_province_value("Unknown Region") is None


def test_merge_opportunity_with_lfs_attaches_labor_columns_by_district() -> None:
    opportunity_df = pd.DataFrame(
        {
            "province_name": ["West", "South"],
            "district_name": ["Nyabihu", "Huye"],
            "opportunity_score": [0.52, 0.38],
        }
    )
    lfs_df = pd.DataFrame(
        {
            "province_name": ["West", "South"],
            "district_name": ["Nyabihu", "Huye"],
            "lfs_women_employment_rate": [0.61, 0.56],
            "lfs_labor_risk_score": [0.72, 0.47],
        }
    )

    merged = dashboard._merge_opportunity_with_lfs(opportunity_df, lfs_df)

    assert "lfs_women_employment_rate" in merged.columns
    assert "lfs_labor_risk_score" in merged.columns
    nyabihu_row = merged.loc[merged["district_name"] == "Nyabihu"].iloc[0]
    assert nyabihu_row["lfs_women_employment_rate"] == pytest.approx(0.61)
    assert nyabihu_row["lfs_labor_risk_score"] == pytest.approx(0.72)


def test_collapse_lfs_rows_by_district_prefers_complete_row() -> None:
    lfs_df = pd.DataFrame(
        {
            "province_name": ["East", "West", "South"],
            "district_name": ["Nyabihu", "Nyabihu", "Huye"],
            "lfs_n_women_16_plus": [pd.NA, 554.0, 500.0],
            "lfs_women_employment_rate": [pd.NA, 0.42, 0.56],
            "lfs_labor_risk_score": [pd.NA, 0.48, 0.47],
        }
    )

    collapsed = dashboard._collapse_lfs_rows_by_district(lfs_df)

    assert len(collapsed) == 2
    nyabihu_row = collapsed.loc[collapsed["district_name"] == "Nyabihu"].iloc[0]
    assert nyabihu_row["province_name"] == "West"
    assert nyabihu_row["lfs_women_employment_rate"] == pytest.approx(0.42)
    assert nyabihu_row["lfs_labor_risk_score"] == pytest.approx(0.48)


def test_build_district_report_markdown_includes_lfs_section_when_available() -> None:
    district_row = pd.Series(
        {
            "district_name": "Nyabihu",
            "province_name": "West",
            "opportunity_rank": 1,
            "priority_rank": 2,
            "women_positive_rate": 0.42,
            "no_edu_rate": 0.15,
            "rural_share": 0.82,
            "fi_modsev_rate": 0.26,
            "poor_borderline_rate": 0.31,
            "stunting_rate": 0.37,
            "underweight_rate": 0.14,
            "policy_priority_score": 0.41,
            "lfs_labor_risk_rank": 3,
            "lfs_women_employment_rate": 0.39,
            "lfs_women_unemployment_rate": 0.16,
            "lfs_women_labor_force_participation_rate": 0.55,
            "lfs_women_mean_monthly_cash_income": 28925.43,
            "lfs_women_time_underemployment_rate": 0.48,
        }
    )

    report_markdown = dashboard._build_district_report_markdown(
        district_row,
        local_row=None,
        local_metric_map={},
    )

    assert "## Women Labor Snapshot (LFS 2022)" in report_markdown
    assert "Women labor risk rank" in report_markdown
    assert "Women mean monthly cash income" in report_markdown