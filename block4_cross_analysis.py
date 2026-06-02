"""
block4_cross_analysis.py
========================
BLOCK 4 of the data pipeline. The HEART of the project.

Merges the four measures computed in Blocks 1-3 into a single master table per
country-year, then produces the analyses that visualize the project's thesis:

  1. Master table:    avg_wellbeing | III | VII | FSI    (per country-year)
  2. Quadrant scatters (2022) split by the medians of each axis:
       Fig.A   Average well-being   vs   Internal Inequality (III)  <- CENTRAL
       Fig.B   Average well-being   vs   Vertical Inequality (VII)
       Fig.C   Average well-being   vs   Future Sustainability (FSI)
  3. Correlation heatmap between the four measures + per-axis components.

Inputs:  outputs/wb_average.csv, inequality_index.csv,
         vertical_inequality_index.csv, future_sustainability_index.csv
Outputs: outputs/master_table.csv
         outputs/figures/fig_A_avg_vs_iii.png
         outputs/figures/fig_B_avg_vs_vii.png
         outputs/figures/fig_C_avg_vs_fsi.png
         outputs/figures/fig_D_correlation_heatmap.png
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..", "outputs")
FIG_DIR = os.path.join(OUT_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

# Geographic palette (consistent with previous blocks)
GEO_PALETTE = {
    'Northern': '#378ADD',
    'Western':  '#1D9E75',
    'Southern': '#D85A30',
    'Eastern':  '#BA7517',
    'Other':    '#888780',
}

# ---------------------------------------------------------------------------
# 1. Load and merge the four measures into a master table
# ---------------------------------------------------------------------------
wb  = pd.read_csv(os.path.join(OUT_DIR, "wb_average.csv"))
iii = pd.read_csv(os.path.join(OUT_DIR, "inequality_index.csv"))
vii = pd.read_csv(os.path.join(OUT_DIR, "vertical_inequality_index.csv"))
fsi = pd.read_csv(os.path.join(OUT_DIR, "future_sustainability_index.csv"))

# Harmonize key columns: each block used either TIME_PERIOD or year as the time column.
for d in (wb, iii, vii, fsi):
    if 'TIME_PERIOD' in d.columns and 'year' not in d.columns:
        d.rename(columns={'TIME_PERIOD': 'year'}, inplace=True)

# Strip the OECD aggregate row if it leaked into any file
for d_name, d in [('wb', wb), ('iii', iii), ('vii', vii), ('fsi', fsi)]:
    if 'Reference area' in d.columns:
        before = len(d)
        d.drop(d[d['Reference area'] == 'OECD'].index, inplace=True)
        if len(d) < before:
            print(f"Filtered OECD aggregate row from {d_name}")

# Keep only the columns we need from each, then merge
wb_s  = wb[['Reference area', 'year', 'avg_wellbeing', 'geo']]
iii_s = iii[['Reference area', 'year', 'III']]
vii_s = vii[['Reference area', 'year', 'VII']]
fsi_s = fsi[['Reference area', 'year', 'FSI']]

master = (wb_s.merge(iii_s, on=['Reference area', 'year'], how='outer')
              .merge(vii_s, on=['Reference area', 'year'], how='outer')
              .merge(fsi_s, on=['Reference area', 'year'], how='outer'))
master = master.sort_values(['year', 'Reference area']).reset_index(drop=True)
master.to_csv(os.path.join(OUT_DIR, "master_table.csv"), index=False)
print(f"\nMaster table saved: {len(master)} rows (countries x years)")


# ---------------------------------------------------------------------------
# 2. Quadrant scatter — generic builder
# ---------------------------------------------------------------------------
def quadrant_scatter(df, x_col, y_col, year, title, xlabel, ylabel,
                     quadrant_labels, outpath, invert_y_for_inequality=False):
    """
    df: subset for the given year, with x_col, y_col, geo, Reference area columns.
    invert_y_for_inequality=True is a presentation hint only (for labelling).
    Quadrants are split by medians, labelled clockwise from top-right.
    """
    sub = df[(df['year'] == year) & df[x_col].notna() & df[y_col].notna()].copy()
    x_med, y_med = sub[x_col].median(), sub[y_col].median()

    fig, ax = plt.subplots(figsize=(11, 7.5))
    # Quadrant background tints (very subtle)
    xmin, xmax = sub[x_col].min() - 3, sub[x_col].max() + 3
    ymin, ymax = sub[y_col].min() - 3, sub[y_col].max() + 3
    ax.axvspan(x_med, xmax, ymin=(y_med - ymin) / (ymax - ymin), ymax=1,
               color='#1D9E75', alpha=0.05)
    ax.axvspan(xmin, x_med, ymin=0, ymax=(y_med - ymin) / (ymax - ymin),
               color='#D85A30', alpha=0.05)

    # Median crosshairs
    ax.axvline(x_med, color='gray', linestyle='--', linewidth=0.8, alpha=0.6)
    ax.axhline(y_med, color='gray', linestyle='--', linewidth=0.8, alpha=0.6)

    # Scatter points colored by geo
    for geo, color in GEO_PALETTE.items():
        s = sub[sub['geo'] == geo]
        ax.scatter(s[x_col], s[y_col], c=color, s=85, alpha=0.85,
                   edgecolors='white', linewidth=1.2, label=geo)

    # Country labels (small)
    for _, r in sub.iterrows():
        ax.annotate(r['Reference area'], (r[x_col], r[y_col]),
                    xytext=(4, 4), textcoords='offset points',
                    fontsize=7, color='#333', alpha=0.85)

    # Quadrant titles in the corners
    corner_xy = [(0.97, 0.97, 'right', 'top'),    # TR
                 (0.03, 0.97, 'left',  'top'),    # TL
                 (0.03, 0.03, 'left',  'bottom'), # BL
                 (0.97, 0.03, 'right', 'bottom')] # BR
    for (lab, (xf, yf, ha, va)) in zip(quadrant_labels, corner_xy):
        ax.text(xf, yf, lab, transform=ax.transAxes, ha=ha, va=va,
                fontsize=10, fontweight='bold', color='#555',
                bbox=dict(boxstyle='round,pad=0.35', facecolor='white',
                          edgecolor='#ccc', alpha=0.85))

    ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax)
    ax.set_xlabel(xlabel, fontsize=11); ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=13, pad=12)
    ax.legend(loc='center left', bbox_to_anchor=(1.01, 0.5),
              frameon=False, fontsize=9, title='Region')
    ax.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(outpath, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {outpath}")
    return sub, x_med, y_med


# Fig.A — Average vs Internal Inequality (CENTRAL)
quadrant_scatter(
    master, 'avg_wellbeing', 'III', 2022,
    title='Beyond the Average — National well-being vs Internal Inequality (2022)',
    xlabel='Average well-being (0–100, higher = better)',
    ylabel='Internal Inequality Index (0–100, higher = more unequal)',
    quadrant_labels=[
        'High well-being\nhigh inequality',     # TR
        'Low well-being\nhigh inequality',      # TL
        'Low well-being\nlow inequality',       # BL
        'High well-being\nlow inequality\n(balanced winners)',  # BR
    ],
    outpath=os.path.join(FIG_DIR, "fig_A_avg_vs_iii.png"),
)

# Fig.B — Average vs Vertical Inequality
quadrant_scatter(
    master, 'avg_wellbeing', 'VII', 2022,
    title='Average well-being vs Vertical Inequality (top vs bottom, 2022)',
    xlabel='Average well-being (0–100, higher = better)',
    ylabel='Vertical Inequality Index (0–100, higher = wider gap)',
    quadrant_labels=[
        'High well-being\nhigh vertical gap',
        'Low well-being\nhigh vertical gap',
        'Low well-being\nlow vertical gap',
        'High well-being\nlow vertical gap',
    ],
    outpath=os.path.join(FIG_DIR, "fig_B_avg_vs_vii.png"),
)

# Fig.C — Average vs Future Sustainability
quadrant_scatter(
    master, 'avg_wellbeing', 'FSI', 2022,
    title='Average well-being vs Future Sustainability (2022)',
    xlabel='Average well-being (0–100, higher = better)',
    ylabel='Future Sustainability Index (0–100, higher = better prospects)',
    quadrant_labels=[
        'High well-being\nstrong future',       # TR
        'Low well-being\nstrong future',        # TL
        'Low well-being\nweak future',          # BL
        'High well-being\nweak future\n(consuming the future?)',  # BR
    ],
    outpath=os.path.join(FIG_DIR, "fig_C_avg_vs_fsi.png"),
)


# ---------------------------------------------------------------------------
# 3. Correlation heatmap (2022)
# ---------------------------------------------------------------------------
m22 = master[master['year'] == 2022][['avg_wellbeing', 'III', 'VII', 'FSI']].dropna(how='all')
corr = m22.corr()
print("\nPearson correlations (2022):")
print(corr.round(2).to_string())

fig, ax = plt.subplots(figsize=(6.2, 5))
im = ax.imshow(corr, cmap='RdBu_r', vmin=-1, vmax=1, aspect='equal')
ax.set_xticks(range(len(corr.columns))); ax.set_yticks(range(len(corr.columns)))
ax.set_xticklabels(corr.columns); ax.set_yticklabels(corr.columns)
for i in range(len(corr)):
    for j in range(len(corr)):
        ax.text(j, i, f"{corr.iat[i, j]:.2f}", ha='center', va='center',
                color='white' if abs(corr.iat[i, j]) > 0.5 else 'black', fontsize=11)
ax.set_title('Pearson correlation between the four measures (2022)', fontsize=12, pad=10)
plt.colorbar(im, ax=ax, shrink=0.75)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "fig_D_correlation_heatmap.png"), dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: {os.path.join(FIG_DIR, 'fig_D_correlation_heatmap.png')}")


# ---------------------------------------------------------------------------
# 4. "Unbalanced countries" — name and shame (er, name and analyze)
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("UNBALANCED COUNTRIES — 2022")
print("=" * 70)

m22 = master[master['year'] == 2022].copy()
wb_med  = m22['avg_wellbeing'].median()
iii_med = m22['III'].median()
fsi_med = m22['FSI'].median()

# High well-being but high inequality (top-right of Fig.A)
hh = m22[(m22['avg_wellbeing'] > wb_med) & (m22['III'] > iii_med)] \
        .sort_values('III', ascending=False)
print("\nHigh well-being BUT high internal inequality:")
print(hh[['Reference area', 'geo', 'avg_wellbeing', 'III']].round(1).to_string(index=False))

# High well-being but weak future (bottom-right of Fig.C: low FSI + high avg)
hl = m22[(m22['avg_wellbeing'] > wb_med) & (m22['FSI'] < fsi_med)] \
        .sort_values('FSI')
print("\nHigh well-being BUT weak future prospects:")
print(hl[['Reference area', 'geo', 'avg_wellbeing', 'FSI']].round(1).to_string(index=False))
