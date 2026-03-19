# Gender-Based Data Science Project

This repository is a starter template for a data science project focused on gender-based analysis.

## Project Goals

- Load and validate tabular data with a gender column and target column.
- Train a baseline classification model.
- Report model quality overall and split by gender groups.
- Analyze women-centered trend patterns across key segments.
- Build a predictive opportunity map to rank high-potential segments.
- Publish Rwanda women-centered visibility outputs down to sector level.
- Add trust scoring that emphasizes feature count and feature coverage quality.
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

## Women-Centered Opportunity Map Workflow

Use the opportunity-map script after adding your richer dataset to `data/raw/`.

Example command:

```bash
python scripts/run_opportunity_map.py \
   --data-path data/raw/your_dataset.csv \
   --target-column outcome \
   --gender-column gender \
   --segment-columns region,industry \
   --time-column event_date \
   --women-values female,woman,women \
   --min-group-size 30
```

Outputs:

- `data/processed/opportunity_map.csv`: ranked segment-level opportunity table
- `data/processed/opportunity_summary.json`: run metadata and top-segment preview

Main ranking features include:

- women positive outcome rate by segment
- predicted propensity for women in each segment
- opportunity gap (`predicted_positive_rate - women_positive_rate`)
- optional yearly trend slope when `--time-column` is provided

## Rwanda Sector Visibility Workflow

This workflow is designed for multi-table ingestion and sector-level reporting.

If you have one prepared table:

```bash
python scripts/run_rwanda_visibility.py \
   --data-path data/raw/your_dataset.csv \
   --gender-column gender \
   --province-column province \
   --district-column district \
   --sector-column sector
```

If you have multiple source tables:

```bash
python scripts/run_rwanda_visibility.py \
   --tables-folder data/raw \
   --join-keys household_id,person_id \
   --base-table household_master \
   --gender-column gender \
   --province-column province \
   --district-column district \
   --sector-column sector
```

Outputs:

- `data/processed/rwanda_sector_visibility.csv`: location-level visibility and trust table
- `data/processed/rwanda_sector_visibility_summary.json`: metadata and top rows

Trust scoring in this workflow combines:

- feature coverage ratio (weighted highest)
- feature count trust against a minimum-feature threshold
- sample trust based on women row volume in each location group

## Expected Data Requirements

The baseline script expects a CSV with:

- one target column (binary or multiclass)
- one gender column used for subgroup reporting
- one or more segment columns used to define opportunity map groups
- Rwanda administrative columns for visibility output (`province`, `district`, `sector` by default)
- optional timestamp/date column to detect direction of trend over time
- any number of additional feature columns

## Notes

- No dataset is included in this template.
- Keep sensitive attributes and fairness requirements under explicit review before shipping models.
