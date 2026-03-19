from pathlib import Path

import pandas as pd


def load_csv(data_path: str | Path) -> pd.DataFrame:
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    dataframe = pd.read_csv(path)
    if dataframe.empty:
        raise ValueError("Input CSV is empty.")

    return dataframe


def validate_columns_exist(
    dataframe: pd.DataFrame,
    required_columns: list[str],
) -> None:
    missing_columns = [column for column in required_columns if column not in dataframe.columns]
    if missing_columns:
        joined = ", ".join(missing_columns)
        raise ValueError(f"Missing required columns: {joined}")


def validate_required_columns(
    dataframe: pd.DataFrame,
    *,
    gender_column: str,
    target_column: str,
) -> None:
    validate_columns_exist(
        dataframe,
        required_columns=[gender_column, target_column],
    )
