"""
Women-Centered Opportunity Map — Rwanda DHS 2014/15
===================================================
Reshapes DHS Household Recode (RWHR70FL.DTA) from wide household-member format
to person-level rows, filters to women aged 15-49, then runs the predictive
opportunity map to identify districts with the highest unmet need.

Opportunity metric: poverty gap (women in poorest/poorer wealth quintiles).
Secondary metric: education gap (women with no schooling).

Usage:
    python scripts/run_women_opportunity.py

Outputs:
    data/processed/dhs_women_15_49.csv          — person-level women dataset
    data/processed/women_opportunity_districts.csv — district-level opportunity map
    data/processed/women_opportunity_summary.json  — run metadata
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from gsd.opportunity import build_predictive_opportunity_map

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_FILE = Path("data/raw/RWHR70FL.DTA")
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PERSON_FILE = OUT_DIR / "dhs_women_15_49.csv"
OPMAP_FILE = OUT_DIR / "women_opportunity_districts.csv"
SUMMARY_FILE = OUT_DIR / "women_opportunity_summary.json"

# ---------------------------------------------------------------------------
# DHS label maps (numeric codes → human-readable)
# ---------------------------------------------------------------------------
PROVINCE_LABELS = {1: "Kigali", 2: "South", 3: "West", 4: "North", 5: "East"}
WEALTH_LABELS = {1: "poorest", 2: "poorer", 3: "middle", 4: "richer", 5: "richest"}
EDUCATION_LABELS = {0: "none", 1: "primary", 2: "secondary", 3: "higher"}
RESIDENCE_LABELS = {1: "urban", 2: "rural"}

# Mapping of shdistrict numeric code → name from official DHS codebook
DISTRICT_LABELS = {
    11: "Nyarugenge", 12: "Gasabo", 13: "Kicukiro",
    21: "Nyanza", 22: "Gisagara", 23: "Nyaruguru", 24: "Huye", 25: "Nyamagabe",
    26: "Ruhango", 27: "Muhanga", 28: "Kamonyi",
    31: "Karongi", 32: "Rutsiro", 33: "Rubavu", 34: "Nyabihu",
    35: "Ngororero", 36: "Cibitoke", 37: "Rusizi", 38: "Nyamasheke",
    41: "Rulindo", 42: "Gakenke", 43: "Musanze", 44: "Burera", 45: "Gicumbi",
    51: "Rwamagana", 52: "Nyagatare", 53: "Gatsibo", 54: "Kayonza",
    55: "Kirehe", 56: "Ngoma", 57: "Bugesera",
}

# ---------------------------------------------------------------------------
# Step 1 — Load household-level data
# ---------------------------------------------------------------------------
print("Loading RWHR70FL.DTA …")
df = pd.read_stata(DATA_FILE, convert_categoricals=False)
print(f"  Households loaded: {len(df):,}")

# Household-level identifiers & covariates
hh_cols = ["hhid", "hv024", "shdistrict", "hv025", "hv270"]
hh = df[hh_cols].copy()
hh["province_name"] = hh["hv024"].map(PROVINCE_LABELS)
hh["district_name"] = hh["shdistrict"].map(DISTRICT_LABELS)
hh["wealth_label"] = hh["hv270"].map(WEALTH_LABELS)
hh["residence"] = hh["hv025"].map(RESIDENCE_LABELS)

# ---------------------------------------------------------------------------
# Step 2 — Melt wide member columns to person-level rows
# ---------------------------------------------------------------------------
# 22 potential members per household (slots 01..22)
SLOTS = [f"{i:02d}" for i in range(1, 23)]

# Only keep slots that have actual data
member_frames = []
for slot in SLOTS:
    sex_col = f"hv104_{slot}"
    age_col = f"hv105_{slot}"
    edu_col = f"hv106_{slot}"
    rel_col = f"hv101_{slot}"
    if sex_col not in df.columns:
        continue
    chunk = hh[["hhid"]].copy()
    chunk["slot"] = slot
    chunk["sex"] = df[sex_col].values
    chunk["age"] = df[age_col].values if age_col in df.columns else pd.NA
    chunk["education_code"] = df[edu_col].values if edu_col in df.columns else pd.NA
    chunk["relation_code"] = df[rel_col].values if rel_col in df.columns else pd.NA
    member_frames.append(chunk)

members = pd.concat(member_frames, ignore_index=True)
members = members.dropna(subset=["sex"])  # drop empty member slots (sex = NaN)
members = members[members["sex"].isin([1, 2])]  # keep only valid sex codes

# Merge HH-level fields
persons = members.merge(
    hh[["hhid", "province_name", "district_name", "wealth_label", "hv270", "residence"]],
    on="hhid",
    how="left",
)
persons["education_label"] = persons["education_code"].map(EDUCATION_LABELS)

print(f"  Total persons reshaped: {len(persons):,}")

# ---------------------------------------------------------------------------
# Step 3 — Filter to women aged 15-49
# ---------------------------------------------------------------------------
women = persons[(persons["sex"] == 2) & (persons["age"] >= 15) & (persons["age"] <= 49)].copy()
women["sex_label"] = "female"

print(f"  Women aged 15-49: {len(women):,}")
print(f"  Districts covered: {women['district_name'].nunique()}")

# Derived opportunity indicators
women["is_poor"] = (women["hv270"] <= 2).astype(int)           # poorest or poorer
women["has_no_edu"] = (women["education_code"] == 0).astype(int)  # no schooling
women["is_rural"] = (women["residence"] == "rural").astype(int)

# Save person-level file
women.to_csv(PERSON_FILE, index=False)
print(f"\n  Person-level file saved → {PERSON_FILE}")

# ---------------------------------------------------------------------------
# Step 4 — Run predictive opportunity map
# ---------------------------------------------------------------------------
# Drop rows with missing target or geography
opmap_df = women.dropna(subset=["is_poor", "province_name", "district_name"]).copy()

print("\nRunning predictive opportunity map …")
print(f"  Analysis rows: {len(opmap_df):,}")
print(f"  Poverty rate among women 15-49: {opmap_df['is_poor'].mean():.1%}")
print(f"  No-education rate among women 15-49: {opmap_df['has_no_edu'].mean():.1%}")

ranked, summary = build_predictive_opportunity_map(
    opmap_df,
    target_column="is_poor",
    gender_column="sex_label",
    segment_columns=["province_name", "district_name"],
    women_values={"female"},
    positive_class=1,
    min_group_size=10,
)

# Enrich output with secondary metrics
edu_by_district = (
    women.groupby("district_name")["has_no_edu"]
    .mean()
    .reset_index()
    .rename(columns={"has_no_edu": "no_edu_rate"})
)
rural_by_district = (
    women.groupby("district_name")["is_rural"]
    .mean()
    .reset_index()
    .rename(columns={"is_rural": "rural_share"})
)
n_by_district = (
    women.groupby("district_name")["age"]
    .count()
    .reset_index()
    .rename(columns={"age": "n_women_15_49"})
)

ranked = (
    ranked
    .merge(edu_by_district, on="district_name", how="left")
    .merge(rural_by_district, on="district_name", how="left")
    .merge(n_by_district, on="district_name", how="left")
)

ranked.to_csv(OPMAP_FILE, index=False)
print(f"\n  Opportunity map saved → {OPMAP_FILE}")

# ---------------------------------------------------------------------------
# Step 5 — Summary JSON
# ---------------------------------------------------------------------------
summary_out = {
    "source_file": str(DATA_FILE),
    "households": int(len(df)),
    "persons_total": int(len(persons)),
    "women_15_49": int(len(women)),
    "districts": int(women["district_name"].nunique()),
    "poverty_rate_women": float(round(opmap_df["is_poor"].mean(), 4)),
    "no_edu_rate_women": float(round(opmap_df["has_no_edu"].mean(), 4)),
    "rural_share_women": float(round(women["is_rural"].mean(), 4)),
    "top_5_opportunity_districts": ranked.head(5)["district_name"].tolist(),
    **summary,
}

with open(SUMMARY_FILE, "w") as f:
    json.dump(summary_out, f, indent=2, default=str)
print(f"  Summary saved        → {SUMMARY_FILE}")

# ---------------------------------------------------------------------------
# Step 6 — Console report
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("WOMEN OPPORTUNITY MAP — TOP 10 PRIORITY DISTRICTS")
print("=" * 60)
display_cols = [
    "province_name",
    "district_name",
    "n_women_15_49",
    "women_share",
    "poverty_rate",
    "opportunity_score",
    "no_edu_rate",
    "rural_share",
]
available = [c for c in display_cols if c in ranked.columns]

# Rename poverty_rate if present, otherwise fall back
if "poverty_rate" not in ranked.columns and "actual_positive_rate" in ranked.columns:
    ranked = ranked.rename(columns={"actual_positive_rate": "poverty_rate"})
    if "poverty_rate" not in available and "actual_positive_rate" in available:
        available = [c if c != "actual_positive_rate" else "poverty_rate" for c in available]

available = [c for c in available if c in ranked.columns]
top10 = ranked.head(10)[available]

# Format percentages
for col in ["women_share", "poverty_rate", "no_edu_rate", "rural_share"]:
    if col in top10.columns:
        top10 = top10.copy()
        top10[col] = top10[col].map(lambda v: f"{v:.1%}" if pd.notna(v) else "")

print(top10.to_string(index=False))
print("\nDone.")
