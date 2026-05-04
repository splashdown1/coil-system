# Ingestion Checklist

- [x] `ingest/fetch.py` — fetches yfinance data, writes DuckDB, runs scoring
- [x] `data/data.duckdb` — created on first run
- [ ] **Add tickers** — edit `TICKERS` list in `ingest/fetch.py`
- [ ] **Adjust scoring** — edit SQL in `score_db()` function in `ingest/fetch.py`
- [ ] **Wire to UI** — `ingest/fetch.py` output feeds the zo.space top-40 page
- [ ] **Schedule** — connect to [Automations](/?t=automations) for twice-daily refresh

## Common issues

| Problem | Fix |
|---|---|
| `No data fetched` | Check network; some tickers delisted/renamed — remove from list |
| `DuckDB write fails` | Ensure `data/` dir exists; check disk space |
| Score shows `NULL` | Run `score_db()` separately or re-run full `fetch.py` |
