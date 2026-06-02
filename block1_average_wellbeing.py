"""
block1_average_wellbeing.py
===========================
BLOCK 1 of the data pipeline.
Loads the OECD Current well-being CSV, filters to 2018 & 2022 (national totals),
normalizes the 54 level indicators in the correct direction, and builds the
composite AVERAGE well-being index per country.

Output: prints a coverage report and the composite ranking, saves an intermediate
parquet for the next blocks.
"""
import pandas as pd
import numpy as np
import os
from indicator_config import LEVEL_INDICATORS, GEO_GROUPS

# Paths are relative to the project root. Put the OECD CSVs in the ../data/ folder.
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")
OUT_DIR = os.path.join(HERE, "..", "outputs")
DATA = os.path.join(DATA_DIR, "current_wellbeing.csv")
YEARS = [2018, 2022]

# ---------------------------------------------------------------------------
# 1. Load and isolate the national-total slice (Age=Total, Sex=Total, Edu=Total)
# ---------------------------------------------------------------------------
df = pd.read_csv(DATA)
df = df[df['OBS_VALUE'].notna()]
tot = df[(df['Age'] == 'Total') & (df['Sex'] == 'Total') &
         (df['Education level'] == 'Total') & (df['TIME_PERIOD'].isin(YEARS))].copy()

# Keep only the level indicators we decided feed the average
tot = tot[tot['Measure'].isin(LEVEL_INDICATORS.keys())]

# Some indicators appear under two units ("...in the same subgroup"); for the total
# slice we keep one value per (country, measure, year). Guard against duplicates.
# We sort by unit name and keep the first so the choice is deterministic/reproducible.
tot = (tot.sort_values('Unit of measure')
          .drop_duplicates(subset=['Reference area', 'Measure', 'TIME_PERIOD'], keep='first'))

print("Level indicators present in data:", tot['Measure'].nunique(), "of", len(LEVEL_INDICATORS))

# ---------------------------------------------------------------------------
# 2. Normalize each indicator (min-max 0..100) within each year, applying direction
# ---------------------------------------------------------------------------
def normalize(sub):
    """Min-max normalize one (year, measure) group to 0..100, applying direction."""
    vals = sub['OBS_VALUE'].astype(float)
    lo, hi = vals.min(), vals.max()
    if hi == lo:
        norm = pd.Series(50.0, index=vals.index)
    else:
        norm = (vals - lo) / (hi - lo) * 100.0
    if LEVEL_INDICATORS[sub.name[1]] == -1:   # name = (TIME_PERIOD, Measure)
        norm = 100.0 - norm
    return norm

tot['norm'] = tot.groupby(['TIME_PERIOD', 'Measure'], group_keys=False).apply(normalize)

# ---------------------------------------------------------------------------
# 3. Composite average well-being = mean of normalized indicators per country-year
#    (require a minimum number of indicators to avoid unstable averages)
# ---------------------------------------------------------------------------
MIN_INDICATORS = 20
comp = (tot.groupby(['Reference area', 'TIME_PERIOD'])
           .agg(avg_wellbeing=('norm', 'mean'), n_ind=('norm', 'size'))
           .reset_index())
comp = comp[comp['n_ind'] >= MIN_INDICATORS]

# attach geographic group
geo_lookup = {c: g for g, cs in GEO_GROUPS.items() for c in cs}
comp['geo'] = comp['Reference area'].map(geo_lookup).fillna('Other')

# ---------------------------------------------------------------------------
# 4. Report
# ---------------------------------------------------------------------------
for y in YEARS:
    sub = comp[comp['TIME_PERIOD'] == y]
    print(f"\n=== {y}: {len(sub)} countries (>= {MIN_INDICATORS} indicators) ===")

print("\n--- 2022 composite average well-being ranking ---")
r22 = comp[comp['TIME_PERIOD'] == 2022].sort_values('avg_wellbeing', ascending=False)
pd.set_option('display.width', 140)
print(r22[['Reference area', 'geo', 'avg_wellbeing', 'n_ind']].to_string(index=False))

# save intermediate
comp.to_csv(os.path.join(OUT_DIR, "wb_average.csv"), index=False)
tot.to_csv(os.path.join(OUT_DIR, "wb_total_normalized.csv"), index=False)
print("\nSaved: outputs/wb_average.csv, outputs/wb_total_normalized.csv")