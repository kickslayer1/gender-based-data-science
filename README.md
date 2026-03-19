# Rwanda Women Policy Intelligence

District-level data science for women-centered policy action in Rwanda.

This project helps civil society organizations and policy teams answer one core question: **where should we act first, and why?**

## Why This Matters

- Combines DHS and CFSVA evidence into one district view
- Surfaces high-priority districts with transparent metrics
- Turns analytics into action-ready summaries for decision-makers
- Allows local CSOs to merge field survey data with national baselines

## What You Get

### 1. DHS Opportunity Mapping

- Builds a district opportunity ranking for women aged 15-49
- Captures poverty pressure, education gaps, and rural exposure

### 2. CFSVA Nutrition and Food Security Prioritization

- Produces district policy-priority scores from mother and child indicators
- Highlights hotspots for nutrition and food-security intervention

### 3. One-Click District Briefs

- Instant district-level summaries with key metrics and recommended CSO actions
- Exportable as Markdown and CSV

### 4. Data Donation Merge

- Upload local CSO CSV/XLSX data
- Standardize district names
- Merge local findings with baseline district evidence

## Quick Start

1. Create and activate a virtual environment
2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Generate DHS women opportunity outputs

```bash
python scripts/run_women_opportunity.py
```

4. Launch the dashboard

```bash
streamlit run scripts/run_dashboard.py
```

## Dashboard Views

- DHS Opportunity View
- CFSVA Nutrition and Food Security Priority View
- District One-Click Report
- Data Donation Merge

## Data Sources Used

- Rwanda DHS 2014-15 Household Recode: `data/raw/RWHR70FL.DTA`
- Rwanda CFSVA 2015 Mother dataset: `data/raw/cfsva-2015-mother-DB- annex.sav`
- Rwanda CFSVA 2015 Child dataset: `data/raw/cfsva-2015-child-DB- annex.sav`
- Rwanda CFSVA 2015 Master dataset (supporting reference): `data/raw/cfsva-2015-master-DB- annex.sav`
- Local CSO data donation uploads at runtime: CSV/XLSX files merged by district in the dashboard

These inputs are transformed into district-level decision outputs under `data/processed`.

## Core Outputs

- `data/processed/women_opportunity_districts.csv`
- `data/processed/women_opportunity_summary.json`
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
