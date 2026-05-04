# Speculative Watch — Top 40

Previous-day close data for ~50 high-beta small/micro-cap equities, ranked by the **Pattern Escalation (Bullish Override)** composite score.

## Quick start

```bash
# Pull fresh data + score
python3 ingest/fetch.py

# Query top 40 in DuckDB
duckdb data/data.duckdb -c "
  SELECT ticker, close, chg_1d, vol_ratio, rsi_14, score, tier
  FROM raw_daily
  WHERE date = (SELECT MAX(date) FROM raw_daily)
  ORDER BY score DESC
  LIMIT 40;
"
```

## Data source

- **Price/volume**: Yahoo Finance (`yfinance`) — previous business day close
- **Analyst/market data**: Yahoo Finance `info` field (delayed or estimated)

## Scoring — Pattern Escalation (Bullish Override)

| Signal | Points | Logic |
|---|---|---|
| Vol surge | 0–40 | Volume ratio above 20d avg (>1.5× = full 40 pts) |
| 1-day momentum | 0–30 | Positive change, scaled |
| RSI zone bonus | 0–15 | 35–55 = accumulation signal |
| C→X shelf breakout | 0–25 | Close above 5d high + positive day = direct escalation |
| Micro-cap premium | 0–10 | Smaller = higher leverage |
| Overbought penalty | –15 | RSI > 80 = late-cycle exhaustion |
| Pump penalty | –10 | >30% single-day move = reversal risk |

Score range: ~0–100+. Higher = stronger speculative entry.

## Refresh schedule

Twice daily (morning + evening) via automation. Data is always previous-day close — never intraday.

## Tier bands

| Tier | Price range |
|---|---|
| $20+ | $20.00 and above |
| $10–20 | $10.00–$19.99 |
| $5–10 | $5.00–$9.99 |
| $1–5 | $1.00–$4.99 |
| Under $1 | $0.01–$0.99 |

---

*COIL/speculative-watch — built on Pattern Escalation Bullish Override model*
