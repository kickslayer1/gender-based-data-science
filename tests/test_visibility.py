import pandas as pd
import pytest

from gsd.visibility import build_rwanda_sector_visibility_table


def _visibility_dataset() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    sectors = ["Niboye", "Kigarama", "Kicukiro", "Gatenga"]

    for idx in range(80):
        rows.append(
            {
                "province": "Kigali City",
                "district": "Kicukiro",
                "sector": sectors[idx % len(sectors)],
                "gender": "female" if idx % 3 != 0 else "male",
                "income": 1000 + (idx * 12),
                "education_level": "secondary" if idx % 2 == 0 else "higher",
                "finance_access": 1 if idx % 4 in {1, 2, 3} else 0,
            }
        )

    return pd.DataFrame(rows)


def test_build_rwanda_sector_visibility_table_returns_scores() -> None:
    dataframe = _visibility_dataset()

    visibility, summary = build_rwanda_sector_visibility_table(
        dataframe,
        gender_column="gender",
        women_values={"female", "woman", "women"},
        province_column="province",
        district_column="district",
        sector_column="sector",
        min_women_count=10,
        min_feature_count=3,
        trust_threshold=0.65,
    )

    assert not visibility.empty
    assert "trust_score" in visibility.columns
    assert "feature_count_trust_score" in visibility.columns
    assert "visibility_score" in visibility.columns
    assert summary["trusted_groups"] >= 1
    assert summary["feature_count_total"] >= 1


def test_build_rwanda_sector_visibility_table_raises_for_missing_women_rows() -> None:
    dataframe = _visibility_dataset()

    with pytest.raises(ValueError, match="No rows matched women_values"):
        build_rwanda_sector_visibility_table(
            dataframe,
            gender_column="gender",
            women_values={"unknown_label"},
            province_column="province",
            district_column="district",
            sector_column="sector",
        )
