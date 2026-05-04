#!/usr/bin/env python3
"""
fetch.py — Pulls previous-day close data for a curated speculative ticker list
using yfinance, then writes raw rows to data.duckdb for scoring.

Run: python3 ingest/fetch.py
Refresh: Twice daily (morning and evening) via automation or manual trigger.
"""

import yfinance as yf
import duckdb
import pandas as pd
from pathlib import Path
from datetime import date, timedelta

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
while YESTERDAY.weekday() >= 5:
    YESTERDAY -= timedelta(days=1)

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "data.duckdb"

TICKERS = [
    "ALDX", "RXRX", "CLOV", "OCGN", "NVIV", "CTRM", "SENS",
    "TNXP", "RNA",  "REGN",
    "DNN", "CCJ", "UUUU", "ENZC", "URG", "NXE",
    "SLDP", "QS",   "LIT",  "ALB",
    "GPRO", "VISL", "RIOT", "MSTR", "BIDU",
    "IONQ", "QUBT", "ARQQ", "QMCO",
    "SPCE", "AUVI", "BNGO", "OPK",
]

def fetch_ticker(ticker: str) -> tuple | None:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d", auto_adjust=True)
        if not isinstance(hist, pd.DataFrame) or hist.empty:
            return None
        row = hist.iloc[-1]
        close     = float(row["Close"])
        open_val  = float(row["Open"])
        high      = float(row["High"])
        low       = float(row["Low"])
        vol       = int(row["Volume"])
        prev_c    = float(hist.iloc[-2]["Close"]) if len(hist) >= 2 else close
        chg_1d    = (close - prev_c) / prev_c if prev_c else 0.0
        high_5d   = float(hist["High"].iloc[-5:].max())
        low_5d    = float(hist["Low"].iloc[-5:].min())
        vol_avg   = float(hist["Volume"].iloc[-20:].mean()) if len(hist) >= 20 else float(vol)
        vol_ratio = float(vol) / vol_avg if vol_avg else 1.0
        delta     = hist["Close"].diff()
        gain      = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        loss      = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
        rs_val    = float(gain.iloc[-1] / loss.iloc[-1]) if loss.iloc[-1] != 0 else 100.0
        rsi_val   = float(100 - (100 / (1 + rs_val)))
        info      = t.info
        return (
            ticker,
            str(YESTERDAY),
            close, open_val, high, low, vol,
            chg_1d, high_5d, low_5d, vol_ratio, rsi_val,
            int(info.get("marketCap", 0) or 0),
            float(info.get("trailingPE") or 0),
            float(info.get("forwardPE") or 0),
            int(info.get("totalRevenue") or 0),
            float(info.get("profitMargins") or 0),
        )
    except Exception as e:
        print(f"[WARN] {ticker}: {e}")
        return None

def write_db(rows: list):
    if not rows:
        return
    con = duckdb.connect(str(DB_PATH))
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_daily (
            ticker VARCHAR, date VARCHAR, close DOUBLE, open_ DOUBLE, high DOUBLE, low_ DOUBLE,
            volume BIGINT, chg_1d DOUBLE, high_5d DOUBLE, low_5d DOUBLE, vol_ratio DOUBLE,
            rsi_14 DOUBLE, mkt_cap BIGINT, pe DOUBLE, fwd_pe DOUBLE, revenue BIGINT, profit_margin DOUBLE,
            score DOUBLE, tier VARCHAR
        )
    """)
    con.execute("DELETE FROM raw_daily WHERE date = ?", [str(YESTERDAY)])
    # Batch insert using parameterized executemany
    cols = "ticker, date, close, open_, high, low_, volume, chg_1d, high_5d, low_5d, vol_ratio, rsi_14, mkt_cap, pe, fwd_pe, revenue, profit_margin"
    placeholders = ",".join(["?"] * 17)
    con.executemany(f"INSERT INTO raw_daily ({cols}) VALUES ({placeholders})", rows)
    con.close()
    print(f"[OK] Wrote {len(rows)} rows for {YESTERDAY}")

def score_db():
    con = duckdb.connect(str(DB_PATH))
    con.execute("""
        UPDATE raw_daily
        SET score = (
            LEAST(40.0, GREATEST(0.0, (vol_ratio - 1.0) * 26.7))
            + LEAST(30.0, GREATEST(0.0, chg_1d * 300.0))
            + CASE WHEN rsi_14 BETWEEN 35 AND 55 THEN 15.0
                   WHEN rsi_14 BETWEEN 30 AND 70 THEN 8.0 ELSE 0.0 END
            + CASE WHEN close > high_5d AND chg_1d > 0 THEN 25.0 ELSE 0.0 END
            + CASE WHEN mkt_cap < 100_000_000   THEN 10.0
                   WHEN mkt_cap < 500_000_000   THEN 6.0
                   WHEN mkt_cap < 2_000_000_000 THEN 3.0 ELSE 0.0 END
            - CASE WHEN rsi_14 > 80 THEN 15.0 ELSE 0.0 END
            - CASE WHEN chg_1d > 0.30 THEN 10.0 ELSE 0.0 END
        ),
            tier = CASE WHEN close >= 20 THEN '$20+'
                   WHEN close >= 10 THEN '$10-20'
                   WHEN close >= 5  THEN '$5-10'
                   WHEN close >= 1  THEN '$1-5' ELSE 'Under $1' END
        WHERE date = ?
    """, [str(YESTERDAY)])
    con.close()
    print("[OK] Scoring complete")

if __name__ == "__main__":
    print(f"Fetching {len(TICKERS)} tickers for {YESTERDAY}…")
    rows = [r for t in TICKERS if (r := fetch_ticker(t)) is not None]
    if not rows:
        print("[ERROR] No data fetched. Check network / ticker list.")
        raise SystemExit(1)
    write_db(rows)
    score_db()
    print(f"[DONE] DB: {DB_PATH}")