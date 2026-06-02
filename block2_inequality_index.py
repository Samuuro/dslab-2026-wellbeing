"""
block2_inequality_index.py
==========================
BLOCK 2 of the data pipeline. The CENTRAL PILLAR of the project.

Builds the Internal Inequality Index (III) from horizontal gaps within each country:
  - age gap        (Young vs Old)
  - sex gap        (Female vs Male)
  - education gap  (Tertiary vs Primary)

For each indicator available in a decomposed form, we compute the ABSOLUTE gap
between the two poles (|poleA - poleB|): a larger gap = a less homogeneous society
on that indicator. Gaps are normalized 0..100 within each (axis, indicator, year)
so indicators on different scales can be averaged, then aggregated:
  indicator gaps --> per-axis inequality --> overall III (mean of the three axes).

Higher III = more internal inequality = worse.

Inputs : data/current_wellbeing.csv
Outputs: outputs/inequality_index.csv (per country-year: iii + per-axis scores)
         console report + saved file for later blocks.
"""
import pandas as pd
import numpy as np
import os
from indicator_config import LEVEL_INDICATORS, HORIZONTAL_AXES, GEO_GROUPS

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "current_wellbeing.csv")
OUT_DIR = os.path.join(HERE, "..", "outputs")
YEARS = [2018, 2022]
MIN_COUNTRIES = 25      # an indicator must cover >= this many countries to enter the index
MIN_IND_PER_AXIS = 5    # a country needs >= this many indicator-gaps to get an axis score

df = pd.read_csv(DATA)
df = df[df['OBS_VALUE'].notna()]


def axis_gaps(axis, poleA, poleB, year):
    """Return a long dataframe of |poleA - poleB| per (country, indicator) for one axis/year."""
    if axis == 'age':
        base = df[(df['Sex'] == 'Total') & (df['Education level'] == 'Total')]
        col = 'Age'
    elif axis == 'sex':
        base = df[(df['Age'] == 'Total') & (df['Education level'] == 'Total')]
        col = 'Sex'
    else:  # education
        base = df[(df['Age'] == 'Total') & (df['Sex'] == 'Total')]
        col = 'Education level'

    b = base[base['TIME_PERIOD'] == year]
    a = b[b[col] == poleA][['Reference area', 'Measure', 'OBS_VALUE']].rename(columns={'OBS_VALUE': 'A'})
    c = b[b[col] == poleB][['Reference area', 'Measure', 'OBS_VALUE']].rename(columns={'OBS_VALUE': 'B'})
    m = a.merge(c, on=['Reference area', 'Measure'])
    m = m[m['Measure'].isin(LEVEL_INDICATORS.keys())]      # only level indicators
    m['gap'] = (m['A'] - m['B']).abs()                     # absolute gap

    # keep only indicators covering enough countries
    counts = m.groupby('Measure')['Reference area'].nunique()
    keep = counts[counts >= MIN_COUNTRIES].index
    m = m[m['Measure'].isin(keep)]

    # normalize each indicator's gap 0..100 (within this axis-year) so scales are comparable
    def norm(g):
        lo, hi = g.min(), g.max()
        return pd.Series(50.0, index=g.index) if hi == lo else (g - lo) / (hi - lo) * 100.0
    m['gap_norm'] = m.groupby('Measure')['gap'].transform(norm)
    m['axis'] = axis
    return m[['Reference area', 'axis', 'Measure', 'gap', 'gap_norm']]


records = []
for year in YEARS:
    allg = pd.concat([axis_gaps(ax, pa, pb, year) for ax, (pa, pb) in HORIZONTAL_AXES.items()])
    allg['year'] = year
    # per-axis score per country = mean of normalized gaps (require enough indicators)
    axis_score = (allg.groupby(['Reference area', 'axis'])
                      .agg(score=('gap_norm', 'mean'), n=('gap_norm', 'size'))
                      .reset_index())
    axis_score = axis_score[axis_score['n'] >= MIN_IND_PER_AXIS]
    wide = axis_score.pivot(index='Reference area', columns='axis', values='score')
    wide['year'] = year
    records.append(wide.reset_index())

iii = pd.concat(records, ignore_index=True)
# overall III = mean of available axis scores (age/sex/education)
axis_cols = [c for c in ['age', 'sex', 'education'] if c in iii.columns]
iii['III'] = iii[axis_cols].mean(axis=1)

geo_lookup = {c: g for g, cs in GEO_GROUPS.items() for c in cs}
iii['geo'] = iii['Reference area'].map(geo_lookup).fillna('Other')

# ---- report ----
print("Axes built:", axis_cols)
for y in YEARS:
    sub = iii[iii['year'] == y]
    print(f"{y}: {len(sub)} countries with an III score")

print("\n--- 2022 Internal Inequality Index (higher = more unequal) ---")
r = iii[iii['year'] == 2022].sort_values('III', ascending=False)
pd.set_option('display.width', 140)
print(r[['Reference area', 'geo', 'age', 'sex', 'education', 'III']].round(1).to_string(index=False))

iii.to_csv(os.path.join(OUT_DIR, "inequality_index.csv"), index=False)
print("\nSaved: outputs/inequality_index.csv")
