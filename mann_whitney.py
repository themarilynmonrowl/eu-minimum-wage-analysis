"""
Mann–Whitney U tests for differences in (median) minimum-wage distributions
between countries, using Eurostat's `earn_mw_cur` time series.

This script can:
  1) Load a Eurostat file (SDMX-CSV or Eurostat TSV) OR a pre-tidied CSV.
  2) Build per-country time series (monthly minimum wage in EUR).
  3) For a chosen pair of countries (A vs B), align on overlapping years and
     run a Mann–Whitney U test (two-sided by default). Each *year's value* is
     treated as one observation in the distribution.

CLI usage
---------
# Example using the original Eurostat file in ./data
python scripts/mann_whitney.py --in data --country-a IE --country-b DE --start 2010 --end 2025

# Example on a pre-tidied long CSV (columns: date,country,value)
python scripts/mann_whitney.py --tidy data/eu_min_wage_long.csv --country-a FR --country-b ES

Outputs
-------
- Prints test statistic, p-value, sample sizes, medians, and years used.
- Optionally writes a JSON result with --out-json.
"""
import argparse
import os
from pathlib import Path
import pandas as pd
from scipy.stats import mannwhitneyu


EU_MEMBERS = {
    'AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IE','IT',
    'LV','LT','LU','MT','NL','PL','PT','RO','SK','SI','ES','SE'
}


def find_input_file(in_dir: str) -> Path:
    p = Path(in_dir)
    for name in ['earn_mw_cur.csv', 'earn_mw_cur.tsv']:
        cand = p / name
        if cand.exists():
            return cand
    for ext in ('*.csv','*.tsv','*.txt'):
        lst = list(p.glob(ext))
        if lst:
            return lst[0]
    raise FileNotFoundError(f"No input file found in {in_dir}")


def read_dataset(path: Path) -> pd.DataFrame:
    name = path.name.lower()
    if name.endswith('.csv'):
        df = pd.read_csv(path)
    elif name.endswith('.tsv') or name.endswith('.txt'):
        df = pd.read_csv(path, sep='\t')
    else:
        raise ValueError(f"Unsupported file type: {path}")
    return df


def normalize_sdmx(df: pd.DataFrame) -> pd.DataFrame:
    cols = {c.lower(): c for c in df.columns}
    time_col = cols.get('time_period') or cols.get('time') or cols.get('timeperiod') or next(iter(df.columns))
    geo_col = cols.get('geo') or next(iter(df.columns))
    value_col = cols.get('value') or cols.get('obs_value') or next(iter(df.columns))
    tidy = df[[time_col, geo_col, value_col]].copy()
    tidy.columns = ['date', 'country', 'value']
    tidy = tidy[tidy['country'].astype(str).str.len() == 2]
    return tidy


def normalize_tsv(df: pd.DataFrame) -> pd.DataFrame:
    first_col = df.columns[0]
    unit_geo = df[first_col].astype(str).str.split(',', n=1, expand=True)
    unit_geo.columns = ['unit','country']
    long = df.drop(columns=[first_col]).copy()
    long = long.melt(var_name='date', value_name='value')
    unit = unit_geo['unit'].repeat(len(df.columns)-1).reset_index(drop=True)
    country = unit_geo['country'].repeat(len(df.columns)-1).reset_index(drop=True)
    long['unit'] = unit
    long['country'] = country
    long = long[['date','country','unit','value']]
    long['value'] = pd.to_numeric(long['value'].astype(str).str.extract(r'([\d\.]+)')[0], errors='coerce')
    long = long.drop(columns=['unit'])
    return long


def load_tidy_from_dir(in_dir: str) -> pd.DataFrame:
    path = find_input_file(in_dir)
    raw = read_dataset(path)
    if any(c.lower() in {'time_period','obs_value','value'} for c in raw.columns):
        tidy = normalize_sdmx(raw)
    else:
        tidy = normalize_tsv(raw)
    tidy = tidy[tidy['country'].isin(EU_MEMBERS)].copy()
    tidy['date'] = tidy['date'].astype(str)
    tidy['year'] = tidy['date'].str.extract(r'(\d{4})').astype(float).astype('Int64')
    tidy = tidy.dropna(subset=['value','year']).copy()
    tidy['year'] = tidy['year'].astype(int)
    return tidy[['country','year','value']]


def load_tidy_from_csv(tidy_csv: str) -> pd.DataFrame:
    df = pd.read_csv(tidy_csv)
    if 'year' not in df.columns:
        df['year'] = pd.to_numeric(df.get('date', '' ).astype(str).str.extract(r'(\d{4})')[0], errors='coerce')
    df = df.rename(columns={
        'VALUE':'value',
        'obs_value':'value',
        'country_code':'country'
    })
    need = {'country','year','value'}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"tidy CSV missing columns: {missing}")
    df = df.dropna(subset=['value','year']).copy()
    df['year'] = df['year'].astype(int)
    return df[['country','year','value']]


def mann_whitney_between_countries(df: pd.DataFrame,
                                   country_a: str,
                                   country_b: str,
                                   start_year: int | None = None,
                                   end_year: int | None = None,
                                   alternative: str = 'two-sided') -> dict:
    a = df[df['country'] == country_a].copy()
    b = df[df['country'] == country_b].copy()
    if start_year is not None:
        a = a[a['year'] >= start_year]
        b = b[b['year'] >= start_year]
    if end_year is not None:
        a = a[a['year'] <= end_year]
        b = b[b['year'] <= end_year]
    years = sorted(set(a['year']).intersection(set(b['year'])))
    if len(years) < 2:
        raise ValueError(f"Not enough overlapping years between {country_a} and {country_b}. Found: {years}")
    a_vals = a[a['year'].isin(years)]['value'].astype(float).tolist()
    b_vals = b[b['year'].isin(years)]['value'].astype(float).tolist()
    stat, p = mannwhitneyu(a_vals, b_vals, alternative=alternative, method='asymptotic')
    return {
        'country_a': country_a,
        'country_b': country_b,
        'years_used': years,
        'n_a': len(a_vals),
        'n_b': len(b_vals),
        'median_a': float(pd.Series(a_vals).median()) if a_vals else None,
        'median_b': float(pd.Series(b_vals).median()) if b_vals else None,
        'mw_stat': float(stat),
        'p_value': float(p),
        'alternative': alternative
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='in_dir', help='Folder containing earn_mw_cur.(csv|tsv)')
    ap.add_argument('--tidy', dest='tidy_csv', help='Optional pre-tidied CSV with columns country,year,value')
    ap.add_argument('--country-a', required=True)
    ap.add_argument('--country-b', required=True)
    ap.add_argument('--start', type=int, default=None, help='Start year (inclusive)')
    ap.add_argument('--end', type=int, default=None, help='End year (inclusive)')
    ap.add_argument('--alternative', default='two-sided', choices=['two-sided','less','greater'])
    ap.add_argument('--out-json', default=None, help='Optional path to save JSON result')
    args = ap.parse_args()

    if args.tidy_csv:
        df = load_tidy_from_csv(args.tidy_csv)
    elif args.in_dir:
        df = load_tidy_from_dir(args.in_dir)
    else:
        ap.error("Provide either --in <dir> with Eurostat file or --tidy <csv>")

    res = mann_whitney_between_countries(
        df, args.country_a, args.country_b, args.start, args.end, args.alternative
    )

    import json
    print(json.dumps(res, indent=2))
    if args.out_json:
        out_dir = os.path.dirname(args.out_json) or '.'
        os.makedirs(out_dir, exist_ok=True)
        with open(args.out_json, 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=2)


if __name__ == '__main__':
    main()
