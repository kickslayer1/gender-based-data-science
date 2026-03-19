from pathlib import Path

import pandas as pd


def load_sav(data_path: str | Path, *, convert_categoricals: bool = True) -> pd.DataFrame:
    """Load an SPSS .sav file into a DataFrame.

    Parameters
    ----------
    data_path:
        Path to the .sav file.
    convert_categoricals:
        When True (default) SPSS value labels are returned as strings instead
        of raw numeric codes — essential for gender/demographic columns where
        labels like "Female" / "Male" are stored as 1 / 2 in the file.
    """
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"SAV file not found: {path}")

    dataframe = pd.read_spss(path, convert_categoricals=convert_categoricals)
    if dataframe.empty:
        raise ValueError("Input SAV file is empty.")

    return dataframe


def load_sav_folder(
    folder_path: str | Path,
    *,
    convert_categoricals: bool = True,
) -> dict[str, pd.DataFrame]:
    """Load every .sav file in a folder as a named DataFrame.

    Parameters
    ----------
    folder_path:
        Directory that contains the .sav files.
    convert_categoricals:
        Passed through to :func:`load_sav` for each file.
    """
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"SAV folder not found: {folder}")

    sav_files = sorted(folder.glob("*.sav"))
    if not sav_files:
        raise ValueError(f"No SAV files found in folder: {folder}")

    loaded: dict[str, pd.DataFrame] = {}
    for file_path in sav_files:
        frame = pd.read_spss(file_path, convert_categoricals=convert_categoricals)
        if frame.empty:
            continue
        loaded[file_path.stem] = frame

    if not loaded:
        raise ValueError("All SAV files in folder were empty.")

    return loaded


def load_dta(data_path: str | Path, *, convert_categoricals: bool = True) -> pd.DataFrame:
    """Load a Stata .dta file into a DataFrame.

    Parameters
    ----------
    data_path:
        Path to the .dta file.
    convert_categoricals:
        When True (default) Stata value labels are decoded to strings instead
        of raw numeric codes.
    """
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"DTA file not found: {path}")

    dataframe = pd.read_stata(path, convert_categoricals=convert_categoricals)
    if dataframe.empty:
        raise ValueError("Input DTA file is empty.")

    return dataframe


def load_dta_folder(
    folder_path: str | Path,
    *,
    convert_categoricals: bool = True,
) -> dict[str, pd.DataFrame]:
    """Load every .dta file in a folder as a named DataFrame.

    Parameters
    ----------
    folder_path:
        Directory that contains the .dta files.
    convert_categoricals:
        Passed through to :func:`load_dta` for each file.
    """
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"DTA folder not found: {folder}")

    dta_files = sorted(folder.glob("*.dta"))
    if not dta_files:
        raise ValueError(f"No DTA files found in folder: {folder}")

    loaded: dict[str, pd.DataFrame] = {}
    for file_path in dta_files:
        frame = pd.read_stata(file_path, convert_categoricals=convert_categoricals)
        if frame.empty:
            continue
        loaded[file_path.stem] = frame

    if not loaded:
        raise ValueError("All DTA files in folder were empty.")

    return loaded


def load_data_folder(
    folder_path: str | Path,
    *,
    convert_categoricals: bool = True,
) -> dict[str, pd.DataFrame]:
    """Load all .csv, .sav, and/or .dta files from a folder into named DataFrames.

    File stems are used as dictionary keys.  Priority order when the same stem
    appears in multiple formats: CSV > SAV > DTA.

    Parameters
    ----------
    folder_path:
        Directory containing the data files.
    convert_categoricals:
        Passed through when loading .sav and .dta files.
    """
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Data folder not found: {folder}")

    # Priority: CSV > SAV > DTA — first match for a stem wins
    all_files = (
        sorted(folder.glob("*.csv"))
        + sorted(folder.glob("*.sav"))
        + sorted(folder.glob("*.dta"))
    )
    if not all_files:
        raise ValueError(f"No CSV, SAV, or DTA files found in folder: {folder}")

    loaded: dict[str, pd.DataFrame] = {}
    for file_path in all_files:
        stem = file_path.stem
        if stem in loaded:
            continue
        suffix = file_path.suffix.lower()
        if suffix == ".csv":
            frame = pd.read_csv(file_path)
        elif suffix == ".sav":
            frame = pd.read_spss(file_path, convert_categoricals=convert_categoricals)
        else:  # .dta
            frame = pd.read_stata(file_path, convert_categoricals=convert_categoricals)
        if frame.empty:
            continue
        loaded[stem] = frame

    if not loaded:
        raise ValueError("All data files in folder were empty.")

    return loaded


def load_csv(data_path: str | Path) -> pd.DataFrame:
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    dataframe = pd.read_csv(path)
    if dataframe.empty:
        raise ValueError("Input CSV is empty.")

    return dataframe


def load_csv_folder(folder_path: str | Path) -> dict[str, pd.DataFrame]:
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"CSV folder not found: {folder}")

    csv_files = sorted(folder.glob("*.csv"))
    if not csv_files:
        raise ValueError(f"No CSV files found in folder: {folder}")

    loaded: dict[str, pd.DataFrame] = {}
    for file_path in csv_files:
        frame = pd.read_csv(file_path)
        if frame.empty:
            continue
        loaded[file_path.stem] = frame

    if not loaded:
        raise ValueError("All CSV files in folder were empty.")

    return loaded


def merge_tables_on_keys(
    tables: dict[str, pd.DataFrame],
    join_keys: list[str],
    *,
    base_table: str | None = None,
    how: str = "left",
) -> pd.DataFrame:
    if not tables:
        raise ValueError("No tables were provided for merge.")
    if not join_keys:
        raise ValueError("At least one join key is required.")

    available_names = sorted(tables.keys())
    base_name = base_table or available_names[0]
    if base_name not in tables:
        joined = ", ".join(available_names)
        raise ValueError(f"Base table '{base_name}' not found. Available tables: {joined}")

    merged = tables[base_name].copy()
    validate_columns_exist(merged, join_keys)

    for name in available_names:
        if name == base_name:
            continue

        frame = tables[name]
        validate_columns_exist(frame, join_keys)

        overlap = [
            column
            for column in frame.columns
            if column in merged.columns and column not in join_keys
        ]
        right = frame.drop(columns=overlap, errors="ignore")
        merged = merged.merge(right, on=join_keys, how=how)

    if merged.empty:
        raise ValueError("Merged table is empty. Check join keys and source data.")

    return merged


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
