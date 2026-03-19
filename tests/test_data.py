import pandas as pd
import pytest

from gsd.data import (
    load_csv_folder,
    load_data_folder,
    load_sav,
    load_sav_folder,
    merge_tables_on_keys,
    validate_columns_exist,
    validate_required_columns,
)


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


def test_load_csv_folder_reads_multiple_tables(tmp_path) -> None:
    first = tmp_path / "base.csv"
    second = tmp_path / "attributes.csv"

    first.write_text("id,gender,target\n1,F,1\n2,M,0\n", encoding="utf-8")
    second.write_text("id,sector\n1,Kicukiro\n2,Niboye\n", encoding="utf-8")

    loaded = load_csv_folder(tmp_path)

    assert set(loaded.keys()) == {"base", "attributes"}
    assert loaded["base"].shape[0] == 2


def test_merge_tables_on_keys_combines_dataframes() -> None:
    tables = {
        "base": pd.DataFrame(
            {
                "id": [1, 2],
                "gender": ["F", "M"],
            }
        ),
        "target": pd.DataFrame(
            {
                "id": [1, 2],
                "outcome": [1, 0],
            }
        ),
    }

    merged = merge_tables_on_keys(
        tables,
        join_keys=["id"],
        base_table="base",
    )

    assert list(merged.columns) == ["id", "gender", "outcome"]
    assert merged.shape == (2, 3)


# ---------------------------------------------------------------------------
# SAV / SPSS loading tests
# ---------------------------------------------------------------------------

def test_load_sav_reads_file(tmp_path) -> None:
    import pyreadstat

    df = pd.DataFrame({"id": [1, 2], "gender": ["Female", "Male"], "target": [1, 0]})
    sav_path = tmp_path / "sample.sav"
    pyreadstat.write_sav(df, str(sav_path))

    result = load_sav(sav_path, convert_categoricals=False)

    assert result.shape[0] == 2
    assert "gender" in result.columns


def test_load_sav_raises_for_missing_file(tmp_path) -> None:
    import pytest

    with pytest.raises(FileNotFoundError, match="SAV file not found"):
        load_sav(tmp_path / "does_not_exist.sav")


def test_load_sav_folder_reads_multiple_files(tmp_path) -> None:
    import pyreadstat

    df_a = pd.DataFrame({"id": [1, 2], "province": ["Kigali", "Eastern"]})
    df_b = pd.DataFrame({"id": [3, 4], "province": ["Northern", "Southern"]})
    pyreadstat.write_sav(df_a, str(tmp_path / "wave1.sav"))
    pyreadstat.write_sav(df_b, str(tmp_path / "wave2.sav"))

    loaded = load_sav_folder(tmp_path, convert_categoricals=False)

    assert set(loaded.keys()) == {"wave1", "wave2"}
    assert loaded["wave1"].shape[0] == 2


def test_load_data_folder_handles_mixed_formats(tmp_path) -> None:
    import pyreadstat

    (tmp_path / "demo.csv").write_text("id,gender\n1,F\n2,M\n", encoding="utf-8")
    df_b = pd.DataFrame({"id": [3, 4], "sector": ["Kicukiro", "Niboye"]})
    pyreadstat.write_sav(df_b, str(tmp_path / "sectors.sav"))

    loaded = load_data_folder(tmp_path, convert_categoricals=False)

    assert "demo" in loaded
    assert "sectors" in loaded
    assert loaded["demo"].shape[0] == 2
    assert loaded["sectors"].shape[0] == 2

