# EU Minimum Wage Analysis

A small, reproducible analysis of **minimum wages across European countries** using the official **Eurostat** dataset.

- Primary dataset: **Eurostat — Monthly minimum wages (bi-annual)**, online data code: `earn_mw_cur` (current prices, EUR).  
- We compute latest available values, make a clean country table, and plot a ranked bar chart.

## Data source

- Eurostat data browser (dataset `earn_mw_cur` — Monthly minimum wages, bi-annual): link in the script and below.
- Eurostat short-code indicator page (`tps00155` — Minimum wages): also linked below.

> You can download in **SDMX-CSV** or **TSV**; the scripts handle both formats.

## Quickstart

```bash
# 1) (Optional) create a venv
python -m venv .venv && source .venv/bin/activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Download the dataset (guide + automated attempt)
python scripts/download_eurostat_minwage.py --out data

# 4) Run the analysis (reads the downloaded file from ./data)
python scripts/analyze_min_wage.py --in data --out outputs

# 5) Open the results
ls outputs/
```

### What you get
- `outputs/eu_min_wage_latest.csv` — tidy table (country, date, monthly_min_wage_eur).
- `outputs/eu_min_wage_bar.png` — ranked bar chart of latest monthly minimum wages (EUR).

## Notes & Caveats
- Some European countries **do not have a statutory national minimum wage** (e.g., DK, IT, AT, FI, SE). They will not appear in the main series.
- Eurostat updates the series **twice a year** (reference dates around **January** and **July**).
- Values are **monthly** and in **EUR**; some source countries define minimum wages hourly/weekly but are **converted by Eurostat** to monthly comparable values.

## Official references
- Eurostat data browser: **Monthly minimum wages — bi-annual (earn_mw_cur)**  
  https://ec.europa.eu/eurostat/databrowser/view/earn_mw_cur/default/table?lang=en
- Eurostat indicator page: **Minimum wages (tps00155)**  
  https://ec.europa.eu/eurostat/databrowser/view/tps00155/default/table?lang=en
- Data.europa.eu dataset entry (download in SDMX-CSV/TSV):  
  https://data.europa.eu/data/datasets/gicnh24uvraqmknqji7s6q?locale=en
