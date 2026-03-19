import pandas as pd
import pytest

from gsd.opportunity import build_predictive_opportunity_map, parse_women_values


def _sample_dataset() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for idx in range(60):
        region = "north" if idx % 2 == 0 else "south"
        sector = "health" if idx % 3 == 0 else "education"
        gender = "female" if idx % 4 != 0 else "male"
        age = 20 + (idx % 30)
        income = 1500 + (idx * 25)
        event_date = f"2025-{(idx % 12) + 1:02d}-15"

        target = 1 if (gender == "female" and region == "north") or idx % 7 == 0 else 0
        rows.append(
            {
                "region": region,
                "sector": sector,
                "gender": gender,
                "age": age,
                "income": income,
                "event_date": event_date,
                "target": target,
            }
        )

    return pd.DataFrame(rows)


def test_build_predictive_opportunity_map_returns_ranked_frame() -> None:
    dataframe = _sample_dataset()

    map_frame, summary = build_predictive_opportunity_map(
        dataframe,
        target_column="target",
        gender_column="gender",
        segment_columns=["region", "sector"],
        women_values=parse_women_values("female,woman"),
        time_column="event_date",
        min_group_size=5,
    )

    assert not map_frame.empty
    assert "opportunity_rank" in map_frame.columns
    assert "opportunity_score" in map_frame.columns
    assert map_frame.iloc[0]["opportunity_rank"] == 1
    assert summary["groups_after_threshold"] > 0


def test_multiclass_target_requires_positive_class() -> None:
    dataframe = pd.DataFrame(
        {
            "gender": ["female", "female", "male", "female", "male", "female"],
            "region": ["north", "north", "south", "south", "north", "south"],
            "target": ["low", "medium", "high", "medium", "low", "high"],
            "age": [22, 25, 31, 27, 29, 30],
        }
    )

    with pytest.raises(ValueError, match="positive_class must be provided"):
        build_predictive_opportunity_map(
            dataframe,
            target_column="target",
            gender_column="gender",
            segment_columns=["region"],
            women_values={"female"},
            min_group_size=1,
        )
