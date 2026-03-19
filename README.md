# Gender-Based Data Science Project

This repository is a starter template for a data science project focused on gender-based analysis.

## Project Goals

- Load and validate tabular data with a gender column and target column.
- Train a baseline classification model.
- Report model quality overall and split by gender groups.
- Keep data, notebooks, scripts, and source code organized for reproducible work.

## Repository Layout

- `data/raw/`: source datasets (not committed by default)
- `data/processed/`: generated outputs and metrics
- `notebooks/`: exploratory analysis notebooks
- `scripts/`: runnable entrypoints
- `src/gsd/`: reusable project code
- `tests/`: tests for project utilities

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run baseline training with your CSV:

   ```bash
   python scripts/run_baseline.py --data-path data/raw/your_dataset.csv --target-column outcome --gender-column gender
   ```

4. Metrics are written to:

   - `data/processed/baseline_metrics.json`

## Expected Data Requirements

The baseline script expects a CSV with:

- one target column (binary or multiclass)
- one gender column used for subgroup reporting
- any number of additional feature columns

## Notes

- No dataset is included in this template.
- Keep sensitive attributes and fairness requirements under explicit review before shipping models.
