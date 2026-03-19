import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gsd.data import load_csv, validate_required_columns
from gsd.modeling import train_baseline_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train and evaluate a baseline model for gender-based analysis."
    )
    parser.add_argument("--data-path", required=True, help="Path to CSV dataset.")
    parser.add_argument(
        "--target-column",
        required=True,
        help="Column name for prediction target.",
    )
    parser.add_argument(
        "--gender-column",
        default="gender",
        help="Column name representing gender groups.",
    )
    parser.add_argument(
        "--include-gender-feature",
        action="store_true",
        help="Include the gender column as an input feature.",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of rows used for test split.",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--output-path",
        default="data/processed/baseline_metrics.json",
        help="File path to store evaluation metrics as JSON.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    dataframe = load_csv(args.data_path)
    validate_required_columns(
        dataframe,
        gender_column=args.gender_column,
        target_column=args.target_column,
    )

    _, metrics = train_baseline_model(
        dataframe,
        target_column=args.target_column,
        gender_column=args.gender_column,
        include_gender_feature=args.include_gender_feature,
        test_size=args.test_size,
        random_state=args.random_state,
    )

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("Baseline training complete.")
    print(f"Metrics written to: {output_path}")
    print(f"Overall accuracy: {metrics['overall']['accuracy']:.4f}")


if __name__ == "__main__":
    main()
