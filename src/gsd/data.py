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


def validate_required_columns(
    dataframe: pd.DataFrame,
    *,
    gender_column: str,
    target_column: str,
) -> None:
    missing_columns = [
        column
        for column in (gender_column, target_column)
        if column not in dataframe.columns
    ]
    if missing_columns:
        joined = ", ".join(missing_columns)
        raise ValueError(f"Missing required columns: {joined}")
