"""
block5_covid_resilience.py
==========================
BLOCK 5 of the data pipeline. The final analytical block.

Question: did countries that were more UNEQUAL before the pandemic absorb the
COVID shock worse? Did inequality itself change between 2018 and 2022?

METHODOLOGICAL NOTE — IMPORTANT
The composite scores from Blocks 1-4 (avg_wellbeing, III, VII, FSI) are each
min-max normalized WITHIN A YEAR, so 0 = worst country that year, 100 = best.
This makes them valid for any CROSS-SECTIONAL comparison within a year
(Block 4 quadrants, correlations, etc.), but they CANNOT be subtracted across
years: a country going from "80 to 85" might just mean others fell more, or
that the sample composition changed.

For temporal comparisons we therefore work on the RAW indicator values:
  1. For each level indicator available in both 2018 and 2022 at the national-total
     slice, compute the change (with direction: a fall in "homicides" is GOOD,
     a fall in "life satisfaction" is BAD).
  2. Per country, the "Well-Being Change Score" (WBC) = % indicators improved
     - % worsened, with a 5% relative-change tolerance to ignore noise.
  3. Analogously, for inequality change we compute raw horizontal gaps
     |poleA - poleB| per indicator in each year, and the "Inequality Change
     Score" (ICS) = % gaps widened - % gaps shrunk. NEVER subtract III_2022 - III_2018.

We then test:
  - Is pre-pandemic Internal Inequality (III 2018, a valid cross-section measure)
    correlated with the WBC?
  - Did inequality itself change (ICS distribution)?

Inputs:  data/current_wellbeing.csv, outputs/inequality_index.csv
Outputs: outputs/covid_resilience.csv
         outputs/figures/fig_E_wbc_by_country.png
         outputs/figures/fig_F_iii18_vs_wbc.png
         outputs/figures/fig_G_iii_change.png  (now using ICS)
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from indicator_config import LEVEL_INDICATORS, GEO_GROUPS

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "current_wellbeing.csv")
OUT_DIR = os.path.join(HERE, "..", "outputs")
FIG_DIR = os.path.join(OUT_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

GEO_PALETTE = {
    'Northern': '#378ADD', 'Western': '#1D9E75', 'Southern': '#D85A30',
    'Eastern': '#BA7517', 'Other': '#888780',
}
geo_lookup = {c: g for g, cs in GEO_GROUPS.items() for c in cs}


# ---------------------------------------------------------------------------
# 1. Load raw data, isolate national-total slice for 2018 and 2022
# ---------------------------------------------------------------------------
df = pd.read_csv(DATA)
df = df[df['OBS_VALUE'].notna()]
tot = df[(df['Age'] == 'Total') & (df['Sex'] == 'Total') &
         (df['Education level'] == 'Total') & (df['TIME_PERIOD'].isin([2018, 2022]))].copy()
tot = tot[tot['Measure'].isin(LEVEL_INDICATORS.keys())]

# Deduplicate by (country, measure, year) keeping the same unit deterministically
tot = (tot.sort_values('Unit of measure')
          .drop_duplicates(subset=['Reference area', 'Measure', 'TIME_PERIOD'], keep='first'))

# Pivot to wide: one row per (country, measure), columns 2018 and 2022
piv = (tot.pivot_table(index=['Reference area', 'Measure'],
                       columns='TIME_PERIOD', values='OBS_VALUE', aggfunc='first')
          .reset_index()
          .rename(columns={2018: 'v18', 2022: 'v22'}))
paired = piv.dropna(subset=['v18', 'v22']).copy()
paired['direction'] = paired['Measure'].map(LEVEL_INDICATORS)

# ---------------------------------------------------------------------------
# 2. Per-indicator classification: improved / worsened / stable
# ---------------------------------------------------------------------------
# Use a relative tolerance: change must exceed 5% of the 2018 value to count as
# a real movement. This avoids treating measurement noise as a signal.
TOL = 0.05

paired['rel_change'] = (paired['v22'] - paired['v18']) / paired['v18'].abs()
# signed_change = positive if BETTER, negative if WORSE, applying direction
paired['signed_change'] = paired['rel_change'] * paired['direction']
paired['movement'] = np.where(paired['signed_change'] > TOL, 'improved',
                       np.where(paired['signed_change'] < -TOL, 'worsened', 'stable'))

# ---------------------------------------------------------------------------
# 3. Country-level Well-Being Change Score (WBC)
# ---------------------------------------------------------------------------
# WBC = (% improved indicators) - (% worsened indicators)
# Range: -100 (all worsened) to +100 (all improved). Around 0 = stable on balance.
agg = (paired.groupby('Reference area')['movement']
              .value_counts().unstack(fill_value=0)
              .reindex(columns=['improved', 'stable', 'worsened'], fill_value=0))
agg['n'] = agg.sum(axis=1)
agg['pct_improved'] = agg['improved'] / agg['n'] * 100
agg['pct_worsened'] = agg['worsened'] / agg['n'] * 100
agg['WBC'] = agg['pct_improved'] - agg['pct_worsened']

# Require >= 15 paired indicators for a stable WBC
agg = agg[agg['n'] >= 15].copy()
agg['geo'] = agg.index.map(geo_lookup).fillna('Other')
agg = agg.reset_index()

# ---------------------------------------------------------------------------
# 4. Join with pre-pandemic III (2018) to test the resilience hypothesis
# ---------------------------------------------------------------------------
iii = pd.read_csv(os.path.join(OUT_DIR, "inequality_index.csv"))
iii18 = iii[iii['year'] == 2018][['Reference area', 'III']].rename(columns={'III': 'III_2018'})

res = agg.merge(iii18, on='Reference area', how='left')

# ---------------------------------------------------------------------------
# 4b. Inequality change 2018 -> 2022 using RAW indicator gaps (same approach as WBC).
# We do NOT compare the composite III scores between years (they're year-normalized,
# so they can't be subtracted). Instead, for each horizontal axis we compute the gap
# |poleA - poleB| in raw units for every paired (country, indicator), then mark it
# as widened / shrunk / stable using the same 5% tolerance as WBC.
# ---------------------------------------------------------------------------
from indicator_config import HORIZONTAL_AXES

def axis_gap_changes(axis, poleA, poleB):
    """Return per (country, indicator) the raw gap in 2018 vs 2022, with movement label."""
    if axis == 'age':
        base = df[(df['Sex'] == 'Total') & (df['Education level'] == 'Total')]
        col = 'Age'
    elif axis == 'sex':
        base = df[(df['Age'] == 'Total') & (df['Education level'] == 'Total')]
        col = 'Sex'
    else:
        base = df[(df['Age'] == 'Total') & (df['Sex'] == 'Total')]
        col = 'Education level'

    sub = base[base['TIME_PERIOD'].isin([2018, 2022]) & base['Measure'].isin(LEVEL_INDICATORS)]
    # Pivot to compute |poleA - poleB| per (country, measure, year)
    p = (sub[sub[col].isin([poleA, poleB])]
            .pivot_table(index=['Reference area', 'Measure', 'TIME_PERIOD'],
                          columns=col, values='OBS_VALUE', aggfunc='first')
            .reset_index())
    p = p.dropna(subset=[poleA, poleB])
    p['gap'] = (p[poleA] - p[poleB]).abs()
    # Wide form: gap_18 vs gap_22
    w = p.pivot_table(index=['Reference area', 'Measure'],
                       columns='TIME_PERIOD', values='gap', aggfunc='first').reset_index()
    w = w.dropna(subset=[2018, 2022]).rename(columns={2018: 'gap18', 2022: 'gap22'})
    # Relative change of the gap. Positive = gap widened (worse equality).
    w['rel'] = (w['gap22'] - w['gap18']) / w['gap18'].replace(0, np.nan).abs()
    w['movement'] = np.where(w['rel'] > TOL, 'widened',
                       np.where(w['rel'] < -TOL, 'shrunk', 'stable'))
    w['axis'] = axis
    return w

gap_changes = pd.concat([axis_gap_changes(ax, pa, pb)
                         for ax, (pa, pb) in HORIZONTAL_AXES.items()],
                        ignore_index=True).dropna(subset=['rel'])

# Inequality Change Score per country: % widened - % shrunk (across all paired axis-indicators)
ineq_agg = (gap_changes.groupby('Reference area')['movement']
                       .value_counts().unstack(fill_value=0)
                       .reindex(columns=['widened', 'stable', 'shrunk'], fill_value=0))
ineq_agg['n'] = ineq_agg.sum(axis=1)
ineq_agg['pct_widened'] = ineq_agg['widened'] / ineq_agg['n'] * 100
ineq_agg['pct_shrunk'] = ineq_agg['shrunk'] / ineq_agg['n'] * 100
ineq_agg['ICS'] = ineq_agg['pct_widened'] - ineq_agg['pct_shrunk']
ineq_agg = ineq_agg[ineq_agg['n'] >= 10].reset_index()  # need >=10 paired axis-indicators

res = res.merge(ineq_agg[['Reference area', 'pct_widened', 'pct_shrunk', 'ICS']],
                on='Reference area', how='left')

# ---------------------------------------------------------------------------
# 5. Report
# ---------------------------------------------------------------------------
print(f"Paired indicator-country observations: {len(paired)}")
print(f"Countries with WBC computable (>=15 indicators): {len(res)}")

print("\n--- Countries that suffered MOST from 2018 to 2022 (lowest WBC) ---")
print(res.sort_values('WBC').head(10)[
    ['Reference area', 'geo', 'n', 'pct_improved', 'pct_worsened', 'WBC']
].round(1).to_string(index=False))

print("\n--- Countries that improved MOST (highest WBC) ---")
print(res.sort_values('WBC', ascending=False).head(10)[
    ['Reference area', 'geo', 'n', 'pct_improved', 'pct_worsened', 'WBC']
].round(1).to_string(index=False))

# Correlation: did pre-pandemic inequality predict the shock absorption?
sub = res.dropna(subset=['III_2018', 'WBC'])
corr = sub['III_2018'].corr(sub['WBC'])
print(f"\nPearson(III 2018, WBC 2018->2022) = {corr:.2f}  on {len(sub)} countries")

# Did inequality itself change? (Now using the methodologically valid ICS, not composite III)
sub2 = res.dropna(subset=['ICS'])
print(f"\nInequality Change Score (ICS) — based on raw axis gaps, NOT composite III scores")
print(f"Countries with computable ICS: {len(sub2)}")
print(f"Mean ICS: {sub2['ICS'].mean():.1f}  (positive = gap widened on more indicators than shrunk)")
print(f"Countries where inequality WIDENED on net (ICS>0): {(sub2['ICS'] > 0).sum()} / {len(sub2)}")
print(f"Countries where inequality SHRUNK on net (ICS<0):  {(sub2['ICS'] < 0).sum()} / {len(sub2)}")

res.to_csv(os.path.join(OUT_DIR, "covid_resilience.csv"), index=False)


# ---------------------------------------------------------------------------
# 6. Figures
# ---------------------------------------------------------------------------
# Fig.E — WBC ranking (diverging bar chart)
fig, ax = plt.subplots(figsize=(9, 12))
r = res.sort_values('WBC')
colors = [GEO_PALETTE[g] for g in r['geo']]
ax.barh(r['Reference area'], r['WBC'], color=colors, edgecolor='white', linewidth=0.6)
ax.axvline(0, color='black', linewidth=0.8)
ax.set_xlabel('Well-Being Change Score (%improved − %worsened, 2018→2022)', fontsize=11)
ax.set_title('Country-level well-being change across the COVID-19 period (2018→2022)', fontsize=12, pad=12)
ax.grid(axis='x', alpha=0.2)
# Region legend
patches = [plt.Rectangle((0, 0), 1, 1, color=c, label=g) for g, c in GEO_PALETTE.items()]
ax.legend(handles=patches, title='Region', loc='lower right', frameon=False, fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "fig_E_wbc_by_country.png"), dpi=150, bbox_inches='tight')
plt.close()
print(f"\nSaved: {os.path.join(FIG_DIR, 'fig_E_wbc_by_country.png')}")

# Fig.F — III 2018 vs WBC (the resilience hypothesis)
sub = res.dropna(subset=['III_2018', 'WBC'])
fig, ax = plt.subplots(figsize=(10, 7))
for geo, color in GEO_PALETTE.items():
    s = sub[sub['geo'] == geo]
    ax.scatter(s['III_2018'], s['WBC'], c=color, s=85, alpha=0.85,
               edgecolors='white', linewidth=1.2, label=geo)
for _, row in sub.iterrows():
    ax.annotate(row['Reference area'], (row['III_2018'], row['WBC']),
                xytext=(4, 4), textcoords='offset points', fontsize=7.5, alpha=0.85)
# OLS fit line
z = np.polyfit(sub['III_2018'], sub['WBC'], 1)
xs = np.linspace(sub['III_2018'].min(), sub['III_2018'].max(), 50)
ax.plot(xs, z[0] * xs + z[1], color='gray', linestyle='--', linewidth=1.5,
        label=f'OLS fit (r={corr:.2f})')
ax.axhline(0, color='black', linewidth=0.6, alpha=0.5)
ax.set_xlabel('Internal Inequality Index — 2018 (pre-pandemic)', fontsize=11)
ax.set_ylabel('Well-Being Change Score (2018→2022)', fontsize=11)
ax.set_title('Did pre-pandemic inequality predict COVID resilience?', fontsize=12, pad=12)
ax.legend(loc='best', frameon=False, fontsize=9)
ax.grid(True, alpha=0.2)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "fig_F_iii18_vs_wbc.png"), dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: {os.path.join(FIG_DIR, 'fig_F_iii18_vs_wbc.png')}")

# Fig.G — Inequality Change Score (ICS) 2018 -> 2022, using raw axis gaps
sub2 = res.dropna(subset=['ICS']).sort_values('ICS')
fig, ax = plt.subplots(figsize=(9, 12))
colors = [GEO_PALETTE[g] for g in sub2['geo']]
ax.barh(sub2['Reference area'], sub2['ICS'], color=colors, edgecolor='white', linewidth=0.6)
ax.axvline(0, color='black', linewidth=0.8)
ax.set_xlabel('Inequality Change Score (% gaps widened - % gaps shrunk, 2018→2022)', fontsize=11)
ax.set_title('Did internal inequality widen or shrink across COVID? (raw-gap analysis, 2018→2022)',
             fontsize=12, pad=12)
ax.grid(axis='x', alpha=0.2)
ax.legend(handles=patches, title='Region', loc='lower right', frameon=False, fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "fig_G_iii_change.png"), dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: {os.path.join(FIG_DIR, 'fig_G_iii_change.png')}")

print("\nSaved: outputs/covid_resilience.csv")
