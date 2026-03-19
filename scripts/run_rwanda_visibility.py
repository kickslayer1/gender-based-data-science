import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gsd.data import load_csv, load_data_folder, load_dta, load_sav, merge_tables_on_keys
from gsd.opportunity import parse_women_values
from gsd.visibility import build_rwanda_sector_visibility_table


def _parse_csv_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _load_input_data(args: argparse.Namespace):
    if args.data_path and args.tables_folder:
        raise ValueError("Use either --data-path or --tables-folder, not both.")

    if args.data_path:
        path = Path(args.data_path)
        suffix = path.suffix.lower()
        if suffix == ".sav":
            return load_sav(path)
        if suffix == ".dta":
            return load_dta(path)
        return load_csv(path)

    if args.tables_folder:
        tables = load_data_folder(args.tables_folder)
        if len(tables) == 1 and not args.join_keys:
            return next(iter(tables.values()))

        join_keys = _parse_csv_list(args.join_keys)
        if not join_keys:
            raise ValueError(
                "--join-keys is required when multiple tables are loaded from --tables-folder."
            )

        return merge_tables_on_keys(
            tables,
            join_keys=join_keys,
            base_table=args.base_table,
            how=args.join_how,
        )

    raise ValueError("One of --data-path or --tables-folder is required.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a Rwanda sector-level women data visibility table with trust metrics "
            "based on feature count, feature coverage, and sample support."
        )
    )
    parser.add_argument(
        "--data-path",
        default=None,
        help="Path to a single prepared CSV, SAV, or DTA file.",
    )
    parser.add_argument(
        "--tables-folder",
        default=None,
        help="Folder containing CSV, SAV, and/or DTA tables to merge before visibility analysis.",
    )
    parser.add_argument(
        "--join-keys",
        default=None,
        help="Comma-separated join keys used when --tables-folder contains multiple tables.",
    )
    parser.add_argument(
        "--base-table",
        default=None,
        help="Optional base table name (CSV stem) for left-join merges.",
    )
    parser.add_argument(
        "--join-how",
        default="left",
        choices=["left", "inner", "right", "outer"],
        help="Join mode for multi-table merge.",
    )
    parser.add_argument(
        "--gender-column",
        default="gender",
        help="Gender column name.",
    )
    parser.add_argument(
        "--women-values",
        default="f,female,woman,women",
        help="Comma-separated values treated as women labels.",
    )
    parser.add_argument(
        "--province-column",
        default="province",
        help="Province column name.",
    )
    parser.add_argument(
        "--district-column",
        default="district",
        help="District column name.",
    )
    parser.add_argument(
        "--sector-column",
        default="sector",
        help="Sector column name.",
    )
    parser.add_argument(
        "--feature-columns",
        default=None,
        help="Optional comma-separated feature columns used for trust computation.",
    )
    parser.add_argument(
        "--target-column",
        default=None,
        help="Optional target column to include women target-rate in visibility output.",
    )
    parser.add_argument(
        "--min-women-count",
        type=int,
        default=30,
        help="Minimum women samples used to saturate sample trust score.",
    )
    parser.add_argument(
        "--min-feature-count",
        type=int,
        default=8,
        help="Feature count threshold used to saturate feature-count trust score.",
    )
    parser.add_argument(
        "--trust-threshold",
        type=float,
        default=0.70,
        help="Threshold above which a group is marked trusted.",
    )
    parser.add_argument(
        "--trusted-only",
        action="store_true",
        help="If provided, output only trusted groups.",
    )
    parser.add_argument(
        "--output-csv",
        default="data/processed/rwanda_sector_visibility.csv",
        help="Output CSV path for sector visibility table.",
    )
    parser.add_argument(
        "--output-json",
        default="data/processed/rwanda_sector_visibility_summary.json",
        help="Output JSON path for metadata and summary.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Rows to print in top preview.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    dataframe = _load_input_data(args)
    women_values = parse_women_values(args.women_values)
    feature_columns = _parse_csv_list(args.feature_columns) if args.feature_columns else None

    visibility, summary = build_rwanda_sector_visibility_table(
        dataframe,
        gender_column=args.gender_column,
        women_values=women_values,
        sector_column=args.sector_column,
        district_column=args.district_column,
        province_column=args.province_column,
        feature_columns=feature_columns,
        target_column=args.target_column,
        min_women_count=args.min_women_count,
        min_feature_count=args.min_feature_count,
        trust_threshold=args.trust_threshold,
    )

    if args.trusted_only:
        visibility = visibility[visibility["trusted"]].copy()

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    visibility.to_csv(output_csv, index=False)

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    top_preview = visibility.head(max(args.top_n, 0)).where(visibility.notna(), None).to_dict("records")
    payload = {
        **summary,
        "output_csv": str(output_csv),
        "trusted_only": bool(args.trusted_only),
        "rows_output": int(len(visibility)),
        "top_preview": top_preview,
    }
    output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("Rwanda sector visibility processing complete.")
    print(f"Visibility table written to: {output_csv}")
    print(f"Summary written to: {output_json}")
    print(f"Rows in output: {len(visibility)}")
    print(visibility.head(args.top_n).to_string(index=False))


if __name__ == "__main__":
    main()
