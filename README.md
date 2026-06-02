# Beyond the Average: Inequality, Sustainability and Resilience Behind the National Well-being Scores

Reproducibility materials for the Data Science Lab project (CdLM Data Science, Università degli Studi di Milano-Bicocca, 2026).

**Authors**
- Samuele Urosevic — 949803 — s.urosevic@campus.unimib.it
- Millaniyage Thilina Lakshan Peiris — 946895 — t.millaniyage@campus.unimib.it

## What this project does

Starting from the OECD *How's Life?* Well-being Database, we build four country-level measures (Average Well-being, Internal Inequality Index, Vertical Inequality Index, Future Sustainability Index), cross them in quadrant analyses for 2022, and study the 2018→2022 change across the COVID-19 period. The full write-up is in the report PDF; this repository contains the code and configuration needed to reproduce every number and figure.

## Repository structure

```
.
├── README.md                       # this file
├── requirements.txt                # Python dependencies
├── indicator_config.py             # single source of truth: indicator directions, axes, geo groups
├── block1_average_wellbeing.py     # Average Well-being score
├── block2_inequality_index.py      # Internal Inequality Index (age / sex / education gaps)
├── block3_vertical_and_future.py   # Vertical Inequality Index + Future Sustainability Index
├── block4_cross_analysis.py        # master table, quadrant scatters, correlation matrix
├── block5_covid_resilience.py      # WBC, ICS, 2018→2022 temporal analysis
├── data/                           # OECD CSVs go here (NOT included — see below)
│   └── README.txt
└── outputs/                        # generated automatically (CSVs + figures)
    └── figures/
```

## Data: how to obtain it

The OECD CSV files are **not** included in this repository (to respect the OECD's terms on
data redistribution). Download them from the OECD Data Explorer (topic: *Well-being and
beyond GDP*) at https://data-explorer.oecd.org/ and place them in the `data/` folder with
these exact filenames:

| Filename | OECD dataset | Used by |
|---|---|---|
| `current_wellbeing.csv` | Current well-being | blocks 1, 2, 5 |
| `vertical_inequality.csv` | Current well-being vertical inequalities | block 3 |
| `future_wellbeing.csv` | Future well-being | block 3 |
| `child_wellbeing.csv` | Child well-being | optional, not used in final analysis |
| `cwb_by_age.csv` | Current well-being by age | optional, not used in final analysis |

Each file must contain the standard OECD Data Explorer columns, including:
`Reference area`, `Measure`, `Age`, `Sex`, `Education level`, `Unit of measure`,
`TIME_PERIOD`, `OBS_VALUE`.

## Setup

Requires **Python 3.12**.

```bash
# (optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Dependencies: `pandas`, `numpy`, `matplotlib`.

## How to run

The blocks must be run **in order**, because each one writes intermediate files into
`outputs/` that the next one reads.

```bash
python block1_average_wellbeing.py
python block2_inequality_index.py
python block3_vertical_and_future.py
python block4_cross_analysis.py
python block5_covid_resilience.py
```

After running all five blocks, `outputs/` contains the master table and every CSV,
and `outputs/figures/` contains the figures used in the report.

## Methodological notes

- All four indices use **min-max normalization to 0–100 within each year**. The scores
  are valid for cross-sectional comparisons within a year, but **cannot be subtracted
  across years** (see Section 3.6 of the report). Temporal change (WBC, ICS) is therefore
  computed on the **raw indicator values**, before normalization.
- Indicator directions (+1 higher = better, −1 lower = better) and the assignment of
  indicators to each index live in `indicator_config.py`. This is the single place to
  edit if you want to change how an indicator is treated.
- Minimum-coverage thresholds (min. countries per indicator, min. indicators per country,
  tolerance band, etc.) are documented in Appendix A of the report and set at the top of
  each block.
- The analysis is intentionally based on interpretable descriptive statistics (Pearson
  correlations and ordinary linear fits) rather than on heavier statistical modelling,
  in line with the small-but-informative sample size (around 40 countries).

## Data licensing

The OECD data are © OECD. This repository links to the original source rather than
re-hosting the raw datasets. Please refer to the OECD Data Explorer for the applicable
licence and cite the original source (see references [1]–[5] in the report).
