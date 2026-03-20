# Rwanda Gender Data Visibility Intelligence Platform

District-level data visibility intelligence for women-centered policy action in Rwanda.

This project helps civil society organizations and policy teams answer one core question: **where should we act first, and why?**

## Why This Matters

- Combines DHS and CFSVA evidence into one district view
- Surfaces high-priority districts with transparent metrics
- Turns analytics into action-ready summaries for decision-makers
- Allows local CSOs to merge field survey data with national baselines

## What You Get

### 1. DHS Gender Responsive Budgeting Mapping

- Builds a district gender responsive budgeting ranking for women aged 15-49
- Captures poverty pressure, education gaps, and rural exposure

### 2. CFSVA Nutrition and Food Security Prioritization

- Produces district gender responsive budgeting scores from mother and child indicators
- Highlights hotspots for nutrition and food-security intervention

### 3. One-Click District Briefs

- Instant district-level summaries with key metrics and recommended CSO actions
- Exportable as Markdown and CSV

### 4. Data Donation Merge

- Upload local CSO CSV/XLSX data
- Standardize district names
- Merge local findings with baseline district evidence

### 5. District Vulnerability Index

- Blends DHS, CFSVA, and LFS district metrics into one transparent index
- Produces vulnerability ranks and tiers for targeting and map workflows

## Quick Start

1. Create and activate a virtual environment
2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Generate DHS gender responsive budgeting outputs

```bash
python scripts/run_women_opportunity.py
```

4. Generate LFS 2022 women labor district outputs

```bash
python scripts/run_lfs_district_analytics.py
```

5. Generate district vulnerability index outputs

```bash
python scripts/run_district_vulnerability_index.py
```

6. Launch the dashboard

```bash
streamlit run scripts/run_dashboard.py
```

## Dashboard Views

- DHS Gender Responsive Budgeting View
- LFS Women Labor View
- District Vulnerability Index View
- CFSVA Nutrition and Food Security Priority View
- District One-Click Report
- Data Donation Merge

The LFS Women Labor View presents district-level women employment, unemployment,
labor-force participation, time underemployment, and income signals from the
2022 labour-force survey.

## How To Read The Metrics

- `DHS gender responsive budgeting score`: a district priority index built from the DHS women-poverty model. Current formula: `0.50 * predicted poverty rate + 0.30 * max(predicted - actual, 0) + 0.15 * women share + 0.05 * trend`. In this run, women share is constant and trend is zero, so the score behaves mainly like a poverty-priority signal. Significance: use it to rank districts relative to each other, not as a percent grade.
- `CFSVA gender responsive budgeting score`: a district composite built from food insecurity and child nutrition burden, including moderate/severe food insecurity, poor/borderline consumption, stunting, underweight, and wasting. Significance: higher values indicate heavier nutrition and food-security stress relative to other districts.
- `Women labor risk score (LFS)`: a weighted labor-market risk index: `0.40 * unemployment + 0.30 * out of labor force + 0.20 * time underemployment + 0.10 * inverse income`, after min-max normalization. Significance: higher values indicate weaker women labor-market conditions.
- `District vulnerability index`: a blended cross-source index: `0.40 * economic stress + 0.35 * nutrition risk + 0.25 * labor-market risk`. Significance: higher values indicate stronger multi-dimensional vulnerability and should be read as a district targeting rank.
- All composite scores in this project are relative indices. They are mainly for comparison, ranking, and triage across districts, so they are not expected to behave like 0-100 performance scores.

## Data Sources Used

- Rwanda DHS 2014-15 Household Recode: `data/raw/RWHR70FL.DTA`
- Rwanda Labour Force Survey 2022 individual file: `data/raw/RW_LFS2022.dta`
- Rwanda Labour Force Survey Gender Thematic Report 2024: `data/raw/LABOUR_FORCE_SURVEY_Gender_Thematic_Report_2024.pdf`
- Rwanda National Gender Statistics Report: `data/raw/National Gender Statistics Report.pdf`
- Rwanda CFSVA 2015 Mother dataset: `data/raw/cfsva-2015-mother-DB- annex.sav`
- Rwanda CFSVA 2015 Child dataset: `data/raw/cfsva-2015-child-DB- annex.sav`
- Rwanda CFSVA 2015 Master dataset (supporting reference): `data/raw/cfsva-2015-master-DB- annex.sav`
- Local CSO data donation uploads at runtime: CSV/XLSX files merged by district in the dashboard

These inputs are transformed into district-level decision outputs under `data/processed`, including DHS, CFSVA, LFS, and the blended district vulnerability index outputs.

## Core Outputs

- `data/processed/women_opportunity_districts.csv`
- `data/processed/women_opportunity_summary.json`
- `data/processed/lfs_2022_women_district_labor.csv`
- `data/processed/lfs_2022_women_district_labor_summary.json`
- `data/processed/district_vulnerability_index.csv`
- `data/processed/district_vulnerability_index_summary.json`
- `data/processed/cfsva_2015_district_policy_risk.csv`
- `data/processed/cfsva_2015_district_policy_risk_summary.json`

## Repository Layout

- `data/raw`: source datasets
- `data/processed`: generated analytics outputs
- `scripts`: runnable pipelines and dashboard entrypoints
- `src/gsd`: reusable project code
- `tests`: automated tests

## Notes

- No datasets are committed in this repository.
- Keep fairness, privacy, and responsible-use checks explicit before deployment.
