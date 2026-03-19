import pandas as pd
import pytest

from gsd.data import validate_columns_exist, validate_required_columns


def test_validate_required_columns_passes() -> None:
    dataframe = pd.DataFrame(
        {
            "gender": ["F", "M"],
            "target": [1, 0],
            "age": [30, 41],
        }
    )

    validate_required_columns(
        dataframe,
        gender_column="gender",
        target_column="target",
    )


def test_validate_required_columns_raises_for_missing_column() -> None:
    dataframe = pd.DataFrame(
        {
            "gender": ["F", "M"],
            "age": [30, 41],
        }
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_required_columns(
            dataframe,
            gender_column="gender",
            target_column="target",
        )


def test_validate_columns_exist_checks_multiple_columns() -> None:
    dataframe = pd.DataFrame(
        {
            "region": ["north", "south"],
            "gender": ["F", "M"],
            "target": [1, 0],
        }
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_columns_exist(
            dataframe,
            required_columns=["region", "gender", "income"],
        )
