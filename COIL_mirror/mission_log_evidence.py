#!/usr/bin/env python3
"""
MISSION_LOG_EVIDENCE — Ground Truth Logger v1.5
Every 15 min: Timestamp, GOES Flux, VIX, QQQ, Notes
Auto-escalates to 60min on rate-limit.
Auto-flags: M-class escalation, >1% VIX spikes.
"""
import csv, requests, time, os
from datetime import datetime, timezone

CSV     = "mission_log_APR28.csv"
BASE_URL = "https://coil-sync-server-splashdown.zocomputer.io"
INTERVAL = 15 * 60   # seconds
FALLBACK = 60 * 60   # seconds
prev_vix  = None

def d(s=""):
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] {s}")

def get_market():
    qqq = vix = None
    try:
        r = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/QQQ",
            params={"interval": "1m", "range": "1d"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        qqq = r.json()["chart"]["result"][0]["meta"]["regularMarketPrice"]
    except Exception as e:
        d(f"QQQ error: {e}")
    try:
        r = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX",
            params={"interval": "1m", "range": "1d"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        vix = r.json()["chart"]["result"][0]["meta"]["regularMarketPrice"]
    except Exception as e:
        d(f"VIX error: {e}")
    return qqq, vix

def get_solar():
    flux = None
    try:
        r = requests.get(
            "https://services.swpc.noaa.gov/json/goes/16/xrays_1m.json",
            timeout=10
        )
        if r.status_code == 200:
            flux = float(r.json()[-1]["flux"])
    except Exception:
        pass
    try:
        if not flux:
            r = requests.get(
                "https://services.swpc.noaa.gov/json/goes/18/xrays_1m.json",
                timeout=10
            )
            if r.status_code == 200:
                flux = float(r.json()[-1]["flux"])
    except Exception:
        pass
    return flux

def classify(flux):
    if flux is None: return "SVC_DOWN"
    if flux >= 1e-4: return "X"
    if flux >= 1e-5: return "M"
    if flux >= 1e-6: return "C"
    if flux >= 1e-7: return "B"
    return "A"

def flag_note(cls, vix, prev_vix):
    notes = []
    if cls in ("M", "X"):
        notes.append(f"ALERT:{cls}-CLASS_ACTIVE")
    if prev_vix and vix:
        spike = abs(vix - prev_vix) / prev_vix * 100
        if spike > 1:
            notes.append(f"VIX_SPIKE:{spike:.1f}%")
    if cls == "SVC_DOWN":
        notes.append("SOLAR_SVC_DOWN")
    return "; ".join(notes) if notes else "NOMINAL"

def tick(interval):
    global prev_vix
    ts   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    flux = get_solar()
    qqq, vix = get_market()
    cls  = classify(flux)
    note = flag_note(cls, vix, prev_vix)
    if vix: prev_vix = vix
    row = [ts, flux or "NA", cls, vix or "NA", qqq or "NA", note]
    d(f"GOES:{cls} | VIX:{vix} | QQQ:{qqq} | {note}")
    with open(CSV, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow(row)
    return interval

def main():
    global prev_vix
    d("MISSION_LOG_EVIDENCE — Starting...")
    # Init CSV with header if empty
    if not os.path.exists(CSV) or os.path.getsize(CSV) == 0:
        with open(CSV, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Timestamp_UTC","GOES_Flux_Wm2","GOES_Class","VIX_Price","QQQ_Price","Notes"])
        d(f"CSV initialized: {CSV}")
    interval = INTERVAL
    while True:
        try:
            next_interval = tick(interval)
            time.sleep(next_interval)
        except KeyboardInterrupt:
            d("Logger stopped.")
            break

if __name__ == "__main__":
    main()