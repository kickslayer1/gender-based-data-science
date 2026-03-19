import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gsd.data import load_csv, validate_columns_exist
from gsd.opportunity import build_predictive_opportunity_map, parse_women_values


def _parse_comma_separated(value: str) -> list[str]:
    items = [item.strip() for item in value.split(",") if item.strip()]
    if not items:
        raise ValueError("Expected at least one comma-separated value.")
    return items


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a women-centered predictive opportunity map from rich tabular data."
        )
    )
    parser.add_argument("--data-path", required=True, help="Path to CSV dataset.")
    parser.add_argument(
        "--target-column",
        required=True,
        help="Outcome variable to model (binary preferred).",
    )
    parser.add_argument(
        "--gender-column",
        default="gender",
        help="Column name containing gender labels.",
    )
    parser.add_argument(
        "--segment-columns",
        required=True,
        help=(
            "Comma-separated segment columns that define your opportunity map "
            "(example: region,industry)."
        ),
    )
    parser.add_argument(
        "--time-column",
        default=None,
        help="Optional date/time column for trend slope estimation.",
    )
    parser.add_argument(
        "--women-values",
        default="f,female,woman,women",
        help="Comma-separated label values treated as women in the gender column.",
    )
    parser.add_argument(
        "--positive-class",
        default=None,
        help="Explicit target class label to treat as positive opportunity.",
    )
    parser.add_argument(
        "--min-group-size",
        type=int,
        default=30,
        help="Minimum women records required per segment to score it.",
    )
    parser.add_argument(
        "--include-gender-feature",
        action="store_true",
        help="Include gender as a model feature when learning opportunity propensity.",
    )
    parser.add_argument(
        "--output-csv",
        default="data/processed/opportunity_map.csv",
        help="File path for the ranked opportunity map table.",
    )
    parser.add_argument(
        "--output-json",
        default="data/processed/opportunity_summary.json",
        help="File path for opportunity-map metadata and run summary.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of top segments to print to console.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    dataframe = load_csv(args.data_path)
    segment_columns = _parse_comma_separated(args.segment_columns)
    women_values = parse_women_values(args.women_values)

    required = [args.target_column, args.gender_column, *segment_columns]
    if args.time_column:
        required.append(args.time_column)
    validate_columns_exist(dataframe, required_columns=required)

    opportunity_map, summary = build_predictive_opportunity_map(
        dataframe,
        target_column=args.target_column,
        gender_column=args.gender_column,
        segment_columns=segment_columns,
        women_values=women_values,
        time_column=args.time_column,
        min_group_size=args.min_group_size,
        positive_class=args.positive_class,
        include_gender_feature=args.include_gender_feature,
    )

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    opportunity_map.to_csv(output_csv, index=False)

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    top_preview = (
        opportunity_map.head(max(args.top_n, 0)).where(opportunity_map.notna(), None).to_dict("records")
    )
    summary_payload = {
        **summary,
        "output_csv": str(output_csv),
        "top_preview": top_preview,
    }
    output_json.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

    print("Predictive opportunity map complete.")
    print(f"Ranked table written to: {output_csv}")
    print(f"Summary written to: {output_json}")
    print("Top ranked segments:")
    print(opportunity_map.head(args.top_n).to_string(index=False))


if __name__ == "__main__":
    main()
