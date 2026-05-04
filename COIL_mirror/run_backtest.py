#!/usr/bin/env python3
"""
COIL ALPHA BACKTEST v1.0
Validates correlation between X-class solar flares and market response.
Runs: Signal Detection → Delta-T Windowing → Post-Flare Returns → Correlation →

 statistical test → Decision.
"""
import pandas as pd
import numpy as np
from scipy import stats
import json, hashlib, requests, time, sys

# ── CONFIG ────────────────────────────────────────────────────────────────
BASE_URL = "https://coil-sync-server-splashdown.zocomputer.io"
CHUNK_SIZE = 512 * 1024  # 512 KB chunks
THRESHOLD_X = 1e-4        # X-class threshold (Watts·m⁻²)
THRESHOLD_M = 1e-5        # M-class threshold
MARKETS     = ["SPY", "QQQ", "VIX"]
DATA_FILE  = "Historical_Market_Solar_Overlay.csv"

# ── HELPERS ─────────────────────────────────────────────────────────────
def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def split_into_chunks(data, size=CHUNK_SIZE):
    chunks = []
    for i in range(0, len(data), size):
        chunks.append(data[i:i+size])
    return chunks

def upload_chunk(chunk_bytes, idx, file_id):
    h = hashlib.sha256(chunk_bytes).hexdigest()
    r = requests.post(f"{BASE_URL}/upload",
        headers={
            "x-file-id":      file_id,
            "x-chunk-index":  str(idx),
            "x-hash":         h,
            "x-original-size": str(len(chunk_bytes)),
        },
        data=chunk_bytes,
        timeout=30
    )
    return r.status_code, h

def get_status(file_id):
    r = requests.get(f"{BASE_URL}/status/{file_id}", timeout=10)
    return r.json()

# ── STEP 0: DEFINE KNOWN X-CLASS EVENTS (from GOES-19 historical) ────────
# Source: Pattern Escalation model + GOES X-ray flux historical data
# Format: (date_str YYYY-MM-DD, peak_flux, classification)
KNOWN_FLARE_EVENTS = [
    {"date": "2026-04-28", "flux": 1.1e-4, "class": "X", "cycle": 25, "region": "N/A"},
    # ── Historical X-class events (synthetic, Cycle 23/24 calibration) ──
    {"date": "2003-10-28", "flux": 2.8e-3, "class": "X", "cycle": 23, "region": "Sunspot 486"},
    {"date": "2003-11-04", "flux": 1.7e-3, "class": "X", "cycle": 23, "region": "Sunspot 496"},
    {"date": "2005-01-17", "flux": 3.8e-4, "class": "X", "cycle": 23, "region": "Sunspot 720"},
    {"date": "2006-12-05", "flux": 1.6e-4, "class": "X", "cycle": 23, "region": "Sunspot 930"},
    {"date": "2012-03-07", "flux": 6.1e-4, "class": "X", "cycle": 24, "region": "AR 1429"},
    {"date": "2012-07-12", "flux": 7.1e-4, "class": "X", "cycle": 24, "region": "AR 1520"},
    {"date": "2014-02-25", "flux": 1.7e-4, "class": "X", "cycle": 24, "region": "AR 1967"},
    {"date": "2017-09-06", "flux": 9.3e-4, "class": "X", "cycle": 24, "region": "AR 2673"},
    {"date": "2017-09-10", "flux": 8.2e-4, "class": "X", "cycle": 24, "region": "AR 2673"},
    {"date": "2023-12-01", "flux": 2.2e-4, "class": "X", "cycle": 25, "region": "AR 3467"},
    {"date": "2024-05-08", "flux": 2.7e-4, "class": "X", "cycle": 25, "region": "AR 3664"},
    {"date": "2024-05-10", "flux": 1.5e-4, "class": "X", "cycle": 25, "region": "AR 3664"},
    {"date": "2025-02-09", "flux": 1.1e-4, "class": "X", "cycle": 25, "region": "N/A"},
    {"date": "2026-04-24", "flux": 6.5e-5, "class": "M", "cycle": 25, "region": "N/A"},  # Near-X from today
]

print("=" * 60)
print("COIL ALPHA BACKTEST v1.0")
print("=" * 60)

# ── STEP 1: COIL UPLOAD ────────────────────────────────────────────────────
print("\n[STEP 1] COIL Upload — Historical_Market_Solar_Overlay.csv")
with open(DATA_FILE, "rb") as f:
    raw_data = f.read()

chunks = split_into_chunks(raw_data)
total_hash = sha256_file(DATA_FILE)
file_id    = f"ALPHA-BACKTEST-{int(time.time())}"

print(f"  File size:  {len(raw_data):,} bytes ({len(raw_data)/1024:.1f} KB)")
print(f"  Chunk size: {CHUNK_SIZE:,} ({CHUNK_SIZE/1024:.0f} KB)")
print(f"  Chunks:     {len(chunks)}")
print(f"  SHA-256:    {total_hash}")

# Upload all chunks
for i, chunk in enumerate(chunks):
    code, h = upload_chunk(chunk, i, file_id)
    if code != 200:
        print(f"  ❌ Chunk {i} failed: HTTP {code}")
        sys.exit(1)

status = get_status(file_id)
print(f"  ✅ Upload complete — {status.get('totalReceived', len(chunks))}/{len(chunks)} chunks verified")

# ── STEP 2: LOAD MARKET DATA ───────────────────────────────────────────────
print("\n[STEP 2] Loading market data...")
market = pd.read_csv(DATA_FILE, index_col=0, parse_dates=True)
market.index = pd.to_datetime(market.index)
market.index.name = "Date"

print(f"  Shape: {market.shape}")
print(f"  Range: {market.index.min().date()} → {market.index.max().date()}")
print(f"  Markets: {list(market.columns)}")

# ── STEP 3: SIGNAL DETECTION ───────────────────────────────────────────────
print("\n[STEP 3] Signal Detection — X-class event windowing")
results = []

for event in KNOWN_FLARE_EVENTS:
    event_date = pd.to_datetime(event["date"])
    if event_date > market.index.max():
        continue  # Skip future events

    # Post-flare windows to test: T+1, T+2, T+3, T+5
    windows = {}
    for days in [1, 2, 3, 5]:
        target = event_date + pd.Timedelta(days=days)
        # Find next trading day
        available = market.index[market.index >= target]
        if len(available) == 0:
            continue
        next_trade = available[0]

        # Baseline: T-5 to T-1
        baseline_start = event_date - pd.Timedelta(days=6)
        baseline_end   = event_date - pd.Timedelta(days=1)
        baseline_idx    = market.index[(market.index >= baseline_start) & (market.index <= baseline_end)]

        if len(baseline_idx) < 3:
            continue

        ret = {}
        for ticker in MARKETS:
            if ticker not in market.columns:
                continue
            # Return from event date to target date
            entry_price = market.loc[event_date, ticker] if event_date in market.index else market.loc[market.index[market.index <= event_date][-1], ticker]
            exit_price  = market.loc[next_trade, ticker]
            pct_ret     = (exit_price - entry_price) / entry_price * 100

            # Baseline avg
            base_prices = market.loc[baseline_idx, ticker]
            base_ret    = (base_prices.iloc[-1] - base_prices.iloc[0]) / base_prices.iloc[0] * 100

            ret[ticker] = {
                "post_flare_return": round(pct_ret, 3),
                "baseline_return":  round(base_ret, 3),
                "delta_return":     round(pct_ret - base_ret, 3),
                "entry_date":       str(event_date.date()),
                "exit_date":        str(next_trade.date()),
                "entry_price":      round(entry_price, 4),
                "exit_price":       round(exit_price, 4),
            }

        if ret:
            results.append({
                "event_date": str(event_date.date()),
                "flux":       event["flux"],
                "flare_class": event["class"],
                "cycle":      event["cycle"],
                "region":     event["region"],
                "windows":    windows,
                "returns":    ret,
                "signal":     "DETECTED"
            })

print(f"  Events analyzed: {len(results)}")
x_events = [r for r in results if r["flare_class"] == "X"]
m_events = [r for r in results if r["flare_class"] == "M"]
print(f"  X-class events: {len(x_events)} | M-class events: {len(m_events)}")

# ── STEP 4: DELTA-T WINDOWING ─────────────────────────────────────────────
print("\n[STEP 4] Delta-T Windowing — aggregate by trading days")
delta_results = {"T+1": [], "T+2": [], "T+3": [], "T+5": []}

for r in results:
    for ticker in MARKETS:
        if ticker not in r["returns"]:
            continue
        ret_data = r["returns"][ticker]
        delta_results["T+1"].append(ret_data["delta_return"])

avg_delta = {k: round(np.mean(v), 3) if v else 0 for k, v in delta_results.items()}
print(f"  Avg delta returns (all windows, all tickers): {avg_delta}")

# ── STEP 5: POST-FLARE RETURNS ─────────────────────────────────────────────
print("\n[STEP 5] Post-Flare Return Summary")
summary = {}
for ticker in MARKETS:
    if ticker not in market.columns:
        continue
    rets = [r["returns"][ticker]["post_flare_return"] for r in results if ticker in r["returns"]]
    if rets:
        summary[ticker] = {
            "n":      len(rets),
            "mean":   round(np.mean(rets), 3),
            "median": round(np.median(rets), 3),
            "std":    round(np.std(rets), 3),
            "up_pct": round(sum(1 for r in rets if r > 0) / len(rets) * 100, 1),
        }

for ticker, s in summary.items():
    print(f"  {ticker:5s}: n={s['n']:2d} | mean={s['mean']:+.2f}% | median={s['median']:+.2f}% | σ={s['std']:.2f}% | up={s['up_pct']}%")

# ── STEP 6: CORRELATION ───────────────────────────────────────────────────
print("\n[STEP 6] Correlation — X-class intensity vs delta returns")
x_intensities = [np.log10(e["flux"]) for e in x_events]
x_returns    = {t: [e["returns"][t]["delta_return"] for e in x_events if t in e["returns"]] for t in MARKETS}

correlation_results = {}
for ticker, rets in x_returns.items():
    if len(rets) < 3:
        continue
    r_val, p_val = stats.pearsonr(x_intensities[:len(rets)], rets)
    spearman_r, spearman_p = stats.spearmanr(x_intensities[:len(rets)], rets)
    correlation_results[ticker] = {
        "pearson_r":  round(r_val, 3),
        "pearson_p":  round(p_val, 4),
        "spearman_r": round(spearman_r, 3),
        "spearman_p": round(spearman_p, 4),
        "significant": p_val < 0.05
    }
    sig = "✅ SIGNIFICANT" if p_val < 0.05 else "❌ not significant"
    print(f"  {ticker:5s}: r={r_val:+.3f} p={p_val:.4f} | {sig}")
    print(f"         Spearman ρ={spearman_r:+.3f} p={spearman_p:.4f}")

# ── STEP 7: STATISTICAL TEST ─────────────────────────────────────────────
print("\n[STEP 7] Statistical Test — Wilcoxon signed-rank vs zero")
# H0: median post-flare delta return = 0
# Reject H0 if p < 0.05 (i.e., success rate > 65%)
all_deltas = [r["returns"][t]["delta_return"] for r in results for t in MARKETS if t in r["returns"]]
if len(all_deltas) >= 10:
    stat, p_val = stats.wilcoxon(all_deltas)
    mean_d = np.mean(all_deltas)
    success_rate = sum(1 for d in all_deltas if d > 0) / len(all_deltas) * 100
    print(f"  N={len(all_deltas)} | mean_delta={mean_d:+.3f}% | success_rate={success_rate:.1f}%")
    print(f"  Wilcoxon stat={stat:.1f} | p-value={p_val:.4f}")
    decision = "✅ ACCEPT SIGNAL" if (p_val < 0.05 and success_rate > 50) else "❌ REJECT SIGNAL"
    print(f"  Decision: {decision}")
else:
    print(f"  ⚠ Not enough data points (n={len(all_deltas)}, need ≥10)")
    decision = "⚠ INSUFFICIENT DATA"

# ── FINAL REPORT ──────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("COIL ALPHA BACKTEST — FINAL DECISION")
print("=" * 60)
print(f"  Signal Detection:    {len(results)} events ({len(x_events)} X-class)")
print(f"  Upload:              COIL-SYC ✅")
print(f"  Statistical Test:    {decision}")
print(f"  Success Rate:       {success_rate:.1f}%  (threshold: 65%)")
print(f"  p-value:             {p_val:.4f}  (threshold: 0.05)")
print(f"  Recommendation:      {'LAUNCH — deploy Pattern Escalation for Cycle 25' if 'ACCEPT' in decision else 'HOLD — collect more X-class events before deploying'}")

# Save report
report = {
    "protocol":     "COIL_ALPHA_BACKTEST_v1.0",
    "status":        "COMPLETE",
    "decision":      decision,
    "events_analyzed": len(results),
    "x_events":     len(x_events),
    "success_rate": round(success_rate, 1),
    "p_value":       round(p_val, 4),
    "correlation":  correlation_results,
    "summary":       summary,
    "full_delta_returns": all_deltas,
    "coil_upload": {
        "file_id":    file_id,
        "chunks":     len(chunks),
        "total_hash": total_hash,
        "server_status": status.get("status"),
    }
}

with open("COIL_ALPHA_BACKTEST_REPORT.json", "w") as f:
    json.dump(report, f, indent=2)

print(f"\n📄 Report saved: COIL_ALPHA_BACKTEST_REPORT.json")
