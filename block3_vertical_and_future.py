"""
block3_vertical_and_future.py
==============================
BLOCK 3 of the data pipeline. Adds the two remaining "beyond GDP" dimensions:

  A) VERTICAL INEQUALITY INDEX (VII): within-country gap between top and bottom of the
     distribution (decile/quintile ratios). The 11 indicators in this OECD dataset are
     ALREADY ratios (e.g. "Top earnings decile in factor of lowest decile"), so a value
     of 5 means "top earns 5x the bottom" -> already an inequality measure. We keep
     indicators with >= MIN_COUNTRIES coverage, normalize 0-100 (higher = more unequal),
     and average. Complements the horizontal axes from Block 2.

  B) FUTURE SUSTAINABILITY INDEX (FSI): based on the 4 capitals (economic / human /
     natural / social). For each indicator we apply a direction (+1 higher better,
     -1 lower better), normalize 0-100, average within each capital, then average the
     four capitals -> FSI. Higher FSI = better future prospects.

Inputs : data/vertical_inequality.csv, data/future_wellbeing.csv
Outputs: outputs/vertical_inequality_index.csv, outputs/future_sustainability_index.csv
"""
import pandas as pd
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")
OUT_DIR = os.path.join(HERE, "..", "outputs")
YEARS = [2018, 2022]
MIN_COUNTRIES = 25

from indicator_config import GEO_GROUPS
geo_lookup = {c: g for g, cs in GEO_GROUPS.items() for c in cs}


# ============================================================================
# A) VERTICAL INEQUALITY INDEX
# ============================================================================
v = pd.read_csv(os.path.join(DATA_DIR, "vertical_inequality.csv"))
v = v[v['OBS_VALUE'].notna()]
v = v[v['TIME_PERIOD'].isin(YEARS)]

# Drop indicators that are too sparse for the chosen years
counts = v.groupby(['TIME_PERIOD', 'Measure'])['Reference area'].nunique()
keep = counts[counts >= MIN_COUNTRIES].index
v = v.set_index(['TIME_PERIOD', 'Measure']).loc[keep].reset_index()

# Normalize each (year, indicator) 0..100 -> higher value = more vertical inequality
def norm(g):
    lo, hi = g.min(), g.max()
    return pd.Series(50.0, index=g.index) if hi == lo else (g - lo) / (hi - lo) * 100.0
v['vii_norm'] = v.groupby(['TIME_PERIOD', 'Measure'])['OBS_VALUE'].transform(norm)

# Country-year VII = mean of available normalized indicators (require >= 4 indicators)
vii = (v.groupby(['Reference area', 'TIME_PERIOD'])
         .agg(VII=('vii_norm', 'mean'), n_ind=('vii_norm', 'size'))
         .reset_index())
vii = vii[vii['n_ind'] >= 4]
vii['geo'] = vii['Reference area'].map(geo_lookup).fillna('Other')


# ============================================================================
# B) FUTURE SUSTAINABILITY INDEX
# ============================================================================
# Direction map for the 35 future-wellbeing indicators (+1 higher better, -1 lower better)
FUTURE_DIRECTION = {
    # --- Economic capital ---
    'General government net financial worth': +1,        # higher net worth = stronger fiscal position
    'Gross fixed capital formation': +1,                 # more investment = more future capacity
    'Households and NPISHs debt': -1,                    # higher debt burden = more fragility
    'Intellectual property assets': +1,
    'Investment in R&D': +1,
    'Monetary financial institutions leverage': -1,      # higher leverage = more financial risk
    'Produced fixed assets': +1,
    'Total economy net financial worth': +1,
    # --- Human capital ---
    'Educational attainment among young adults': +1,
    'Labour underutilisation rate': -1,
    'Obesity prevalence': -1,
    'Premature mortality': -1,
    'Smoking prevalence': -1,
    # --- Natural capital ---
    'Carbon footprint': -1,
    'Gain of natural and semi-natural land cover': +1,
    'Greenhouse gas emissions per capita': -1,
    'Intact forest landscapes': +1,
    'Loss of natural and semi-natural land cover': -1,
    'Material footprint per capita': -1,
    'Natural and semi-natural land cover': +1,
    'Protected marine areas': +1,
    'Protected terrestrial areas': +1,
    'Recycling rate': +1,
    'Red list index of threatened species': +1,          # closer to 1 = fewer species threatened
    'Renewable energy': +1,
    'Soil nutrient balance': 0,                          # ambiguous (both excess and deficit are bad) -> excluded
    'Water stress (internal resources)': -1,
    'Water stress (total renewable resources)': -1,
    # --- Social capital ---
    'Corruption': +1,                                    # OECD uses Transparency Intl. CPI: higher = LESS corrupt
    'Gender parity in politics': +1,
    'Government stakeholder engagement': +1,
    'Trust in government': +1,
    'Trust in others': +1,
    'Trust in the police': +1,
    'Volunteering through organisations': +1,
}

f = pd.read_csv(os.path.join(DATA_DIR, "future_wellbeing.csv"))
f = f[f['OBS_VALUE'].notna()]
ftot = f[(f['Age'] == 'Total') & (f['Sex'] == 'Total') & (f['Education level'] == 'Total')]
ftot = ftot[ftot['TIME_PERIOD'].isin(YEARS)]
# Exclude ambiguous indicators (direction = 0)
ftot = ftot[ftot['Measure'].map(FUTURE_DIRECTION).fillna(0) != 0].copy()

# Require min country coverage per (year, indicator)
counts = ftot.groupby(['TIME_PERIOD', 'Measure'])['Reference area'].nunique()
keep = counts[counts >= MIN_COUNTRIES].index
ftot = ftot.set_index(['TIME_PERIOD', 'Measure']).loc[keep].reset_index()

# Normalize each indicator 0..100 within (year, indicator), then apply direction
def norm_dir(sub):
    vals = sub['OBS_VALUE'].astype(float)
    lo, hi = vals.min(), vals.max()
    n = pd.Series(50.0, index=vals.index) if hi == lo else (vals - lo) / (hi - lo) * 100.0
    if FUTURE_DIRECTION[sub.name[1]] == -1:
        n = 100.0 - n
    return n
ftot['n'] = ftot.groupby(['TIME_PERIOD', 'Measure'], group_keys=False).apply(norm_dir)

# Per-capital score = mean of normalized indicators (need >=2 indicators per capital)
cap_score = (ftot.groupby(['Reference area', 'TIME_PERIOD', 'Domain'])
                 .agg(score=('n', 'mean'), n_ind=('n', 'size')).reset_index())
cap_score = cap_score[cap_score['n_ind'] >= 2]

# Pivot to wide form (one column per capital) + overall FSI = mean of available capitals
wide = cap_score.pivot(index=['Reference area', 'TIME_PERIOD'], columns='Domain', values='score').reset_index()
cap_cols = [c for c in ['Economic capital', 'Human capital', 'Natural capital', 'Social capital']
            if c in wide.columns]
wide['FSI'] = wide[cap_cols].mean(axis=1)
wide['geo'] = wide['Reference area'].map(geo_lookup).fillna('Other')


# ============================================================================
# REPORT
# ============================================================================
print("=" * 70)
print("VERTICAL INEQUALITY INDEX (VII) — 2022 ranking (higher = more unequal)")
print("=" * 70)
r = vii[vii['TIME_PERIOD'] == 2022].sort_values('VII', ascending=False)
pd.set_option('display.width', 140)
print(r[['Reference area', 'geo', 'VII', 'n_ind']].round(1).to_string(index=False))

print("\n" + "=" * 70)
print("FUTURE SUSTAINABILITY INDEX (FSI) — 2022 ranking (higher = better future)")
print("=" * 70)
r = wide[wide['TIME_PERIOD'] == 2022].sort_values('FSI', ascending=False)
print(r[['Reference area', 'geo'] + cap_cols + ['FSI']].round(1).to_string(index=False))

vii.to_csv(os.path.join(OUT_DIR, "vertical_inequality_index.csv"), index=False)
wide.to_csv(os.path.join(OUT_DIR, "future_sustainability_index.csv"), index=False)
print("\nSaved: outputs/vertical_inequality_index.csv, outputs/future_sustainability_index.csv")
