"""Download Eurostat minimum wage dataset (earn_mw_cur).

This script tries to fetch the dataset in **SDMX-CSV** first and falls back to
instructions if direct download is blocked in your environment.

Usage:
    python scripts/download_eurostat_minwage.py --out data
"""
import argparse
import os
import sys
import time
import requests

SDMX_CSV_URL = (
    # SDMX-CSV (full dataset). If this fails (auth/firewall), open the README links and download manually.
    "https://ec.europa.eu/eurostat/api/discoveries/tgm/sdmx/2.1/data/earn_mw_cur?contentType=csv"
)

FALLBACK_NOTE = """
If the automated download fails, please download manually from one of:
- Eurostat data browser (earn_mw_cur): open the table, then use 'Download' -> SDMX-CSV or TSV.
- Data.europa.eu dataset page (provides SDMX-CSV / TSV links).

Save the file under: {out_dir}/earn_mw_cur.csv  OR  {out_dir}/earn_mw_cur.tsv
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='data', help='Output folder')
    args = ap.parse_args()

    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, 'earn_mw_cur.csv')

    print(f"[*] Attempting SDMX-CSV download from:\n    {SDMX_CSV_URL}")
    try:
        r = requests.get(SDMX_CSV_URL, timeout=60)
        r.raise_for_status()
        # Basic sanity check: small HTML pages indicate a portal, not CSV
        if r.text.strip().lower().startswith('<!doctype') or '<html' in r.text.lower():
            raise RuntimeError('Got HTML page, not CSV. Portal likely requires interactive download.')
        with open(out_csv, 'wb') as f:
            f.write(r.content)
        print(f"[+] Saved: {out_csv}")
        return 0
    except Exception as e:
        print(f"[!] Automated download failed: {e}")
        print(FALLBACK_NOTE.format(out_dir=out_dir))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
