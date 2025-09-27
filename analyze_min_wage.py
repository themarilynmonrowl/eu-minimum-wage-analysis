"""Analyze Eurostat minimum wage data (earn_mw_cur) and produce tidy outputs.

Looks for a dataset file in ./data named either 'earn_mw_cur.csv' (SDMX-CSV)
or 'earn_mw_cur.tsv' (Eurostat TSV). Produces:

- outputs/eu_min_wage_latest.csv
- outputs/eu_min_wage_bar.png

Usage:
    python scripts/analyze_min_wage.py --in data --out outputs
"""
import argparse
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

EU_MEMBERS = {
    # 27 EU members (as of 2025)
    'AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IE','IT',
    'LV','LT','LU','MT','NL','PL','PT','RO','SK','SI','ES','SE'
}

NO_NATIONAL_MIN_WAGE = {'DK','IT','AT','FI','SE'}

def find_input_file(in_dir: str) -> Path:
    p = Path(in_dir)
    for name in ['earn_mw_cur.csv', 'earn_mw_cur.tsv']:
        cand = p / name
        if cand.exists():
            return cand
    # try any csv/tsv
    for ext in ('*.csv','*.tsv','*.txt'):
        lst = list(p.glob(ext))
        if lst:
            return lst[0]
    raise FileNotFoundError("No input file found in {}".format(in_dir))

def read_dataset(path: Path) -> pd.DataFrame:
    name = path.name.lower()
    if name.endswith('.csv'):
        df = pd.read_csv(path)
    elif name.endswith('.tsv') or name.endswith('.txt'):
        df = pd.read_csv(path, sep='\t')
    else:
        raise ValueError("Unsupported file type: {}".format(path))
    return df

def normalize_sdmx(df: pd.DataFrame) -> pd.DataFrame:
    """Handle common SDMX-CSV shapes.

    Expect columns like: TIME_PERIOD, geo, unit, VALUE  (names vary)
    """
    cols = {c.lower(): c for c in df.columns}
    # Flexible column resolution
    time_col = cols.get('time_period') or cols.get('time') or cols.get('timeperiod') or 'TIME_PERIOD'
    geo_col = cols.get('geo') or cols.get('GEO') or 'geo'
    value_col = cols.get('value') or cols.get('OBS_VALUE') or cols.get('value (code)') or 'VALUE'
    unit_col = cols.get('unit') or 'unit'

    for c in (time_col, geo_col, value_col):
        if c not in df.columns:
            # try case-insensitive fallback
            for dcol in df.columns:
                if dcol.lower() == c.lower():
                    locals()[c] = dcol

    tidy = df[[time_col, geo_col, value_col]].copy()
    tidy.columns = ['date', 'country', 'value']
    # Keep only country codes (two-letter) and drop aggregates (EA, EU27_2020, etc.)
    tidy = tidy[tidy['country'].str.len() == 2]
    return tidy

def normalize_tsv(df: pd.DataFrame) -> pd.DataFrame:
    """Eurostat TSV usually has a 'unit,geo\time' pivot-like column and year columns.
    For bi-annual data we may see multiple columns per year (Jan, Jul) or a single code.
    We'll melt to long format.
    """
    first_col = df.columns[0]
    # Split 'unit,geo\time' into unit and geo
    unit_geo = df[first_col].str.split(',', n=1, expand=True)
    unit_geo.columns = ['unit','country']
    long = df.drop(columns=[first_col]).copy()
    long = long.melt(var_name='date', value_name='value')
    # Attach unit & country repeated
    unit = unit_geo['unit'].repeat(len(df.columns)-1).reset_index(drop=True)
    country = unit_geo['country'].repeat(len(df.columns)-1).reset_index(drop=True)
    long['unit'] = unit
    long['country'] = country
    long = long[['date','country','unit','value']]
    # Clean numeric
    long['value'] = pd.to_numeric(long['value'].astype(str).str.extract(r'([\d\.]+)')[0], errors='coerce')
    return long

def latest_per_country(tidy: pd.DataFrame) -> pd.DataFrame:
    # Drop NA and pick latest date per country
    tidy = tidy.dropna(subset=['value']).copy()
    tidy['date'] = tidy['date'].astype(str)
    tidy = tidy.sort_values(['country','date'])
    last = tidy.groupby('country', as_index=False).tail(1)
    # Keep only EU members
    last = last[last['country'].isin(EU_MEMBERS)].copy()
    return last

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='in_dir', default='data')
    ap.add_argument('--out', dest='out_dir', default='outputs')
    args = ap.parse_args()

    in_path = find_input_file(args.in_dir)
    os.makedirs(args.out_dir, exist_ok=True)

    raw = read_dataset(in_path)

    # Heuristic: detect SDMX-CSV (has TIME_PERIOD / VALUE) vs TSV (first column has 'unit,geo')
    if any(c.lower() in {'time_period','obs_value','value'} for c in raw.columns):
        tidy = normalize_sdmx(raw)
    else:
        tidy = normalize_tsv(raw)

    latest = latest_per_country(tidy)
    latest = latest.rename(columns={'value':'monthly_min_wage_eur'})
    latest.to_csv(os.path.join(args.out_dir, 'eu_min_wage_latest.csv'), index=False)

    # Plot
    dfp = latest.copy()
    dfp = dfp.sort_values('monthly_min_wage_eur', ascending=True)
    labels = dfp['country'].tolist()
    values = dfp['monthly_min_wage_eur'].tolist()

    plt.figure(figsize=(10, 8))
    plt.barh(labels, values)
    plt.title('EU Monthly Minimum Wages (latest available, EUR)')
    plt.xlabel('EUR per month')
    plt.tight_layout()
    out_png = os.path.join(args.out_dir, 'eu_min_wage_bar.png')
    plt.savefig(out_png, dpi=200)
    print(f"[+] Wrote: {out_png}")
    print(f"[+] Wrote: {os.path.join(args.out_dir, 'eu_min_wage_latest.csv')}")

if __name__ == '__main__':
    main()
