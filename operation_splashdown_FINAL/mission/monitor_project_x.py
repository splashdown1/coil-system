#!/usr/bin/env python3
"""
COIL SPLASHDOWN — PROJECT_X_TRADE
Live monitoring script for Apr 28-30 execution window.
Run via: python3 monitor_project_x.py
"""
import time, json, requests, hashlib
from datetime import datetime, timezone

CONFIG_FILE = "PROJECT_X_TRADE.json"
STATE_FILE  = "PROJECT_X_STATE.json"
BASE_URL    = "https://coil-sync-server-splashdown.zocomputer.io"

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {"entry_vix": None, "entry_qqq": None, "position_open": False, "alerts": []}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    print(f"[{ts}] {msg}")

def get_live_market():
    """Fetch current QQQ and VIX via yfinance."""
    import yfinance as yf
    qqq = yf.Ticker("QQQ").history(period="1d", interval="5m")
    vix = yf.Ticker("^VIX").history(period="1d", interval="5m")
    qqq_price = round(qqq["Close"].iloc[-1], 2)
    vix_price = round(vix["Close"].iloc[-1], 2)
    return qqq_price, vix_price

def get_solar_status():
    """Fetch current GOES X-ray flux via NOAA SWPC."""
    try:
        r = requests.get(
            "https://services.swpc.noaa.gov/json/goes/16/xrays_1m.json",
            timeout=10
        )
        data = r.json()
        latest = data[-1]
        flux = latest.get("flux", 0)
        return flux
    except:
        return None

def classify_flare(flux):
    """Classify flux in W/m^2."""
    if flux >= 1e-4:  return "X"
    if flux >= 1e-5:  return "M"
    if flux >= 1e-6:  return "C"
    if flux >= 1e-7:  return "B"
    return "A"

def check_triggers(state, cfg, qqq, vix):
    alerts = []
    stopped = False

    if state["entry_vix"] is None:
        return alerts, stopped

    vix_entry = state["entry_vix"]
    qqq_entry = state["entry_qqq"]

    # Step 2: VIX velocity check
    vix_pct = (vix - vix_entry) / vix_entry * 100
    if vix_pct > 2.2:
        alerts.append(f"🔥 ABORT VIX SHORT — VIX up {vix_pct:.1f}% (>2.2% trigger)")
        stopped = True

    # Step 3: QQQ strength check
    qqq_pct = (qqq - qqq_entry) / qqq_entry * 100
    if qqq_pct < -10.0:
        alerts.append(f"🛑 QQQ DOWN {qqq_pct:.1f}% — HARD STOP TRIGGERED")
        stopped = True

    return alerts, stopped

def tick():
    cfg  = load_config()
    state = load_state()
    now  = datetime.now(timezone.utc)
    day  = now.strftime("%Y-%m-%d")

    log(f"=== PROJECT_X MONITOR | {day} {now.strftime('%H:%M UTC')} ===")

    # 1. Solar check
    flux = get_solar_status()
    if flux:
        cls = classify_flare(flux)
        log(f"Solar flux: {flux:.2e} W/m²  [{cls}]")
        if cfg["status"] == "READY_FOR_DEPLOYMENT" and cls in ["M","X"]:
            log(f"✅ SOLAR PEAK CONFIRMED — M{cls} or higher active")
    else:
        log("Solar status: UNAVAILABLE")

    # 2. Market check
    try:
        qqq, vix = get_live_market()
        log(f"Market — QQQ: {qqq}  VIX: {vix}")
    except Exception as e:
        log(f"Market data error: {e}")
        return

    # Open position on first check
    if not state["position_open"] and cfg["status"] == "DEPLOYED":
        state["entry_vix"] = vix
        state["entry_qqq"] = qqq
        state["position_open"] = True
        state["alerts"].append(f"Position opened — QQQ:{qqq} VIX:{vix}")
        log(f"📌 POSITION OPEN — QQQ:{qqq}  VIX:{vix}")
        save_state(state)

    # Check triggers
    if state["position_open"]:
        alerts, stopped = check_triggers(state, cfg, qqq, vix)
        for a in alerts:
            log(a)
            state["alerts"].append(f"[{now.isoformat()}] {a}")
        if stopped:
            state["position_open"] = False
            state["alerts"].append(f"Position closed at {now.isoformat()}")
            log("🛑 POSITION CLOSED")
            save_state(state)
            return

    # Healthbeat to COIL
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        log(f"COIL heartbeat: {health.status_code}")
    except:
        log("⚠ COIL server unreachable")

    save_state(state)
    log(f"State saved — entry QQQ:{state['entry_qqq']}  VIX:{state['entry_vix']}")

def main():
    print("==========================================")
    print("  PROJECT_X — LIVE MONITOR")
    print("  Apr 28-30, 2026")
    print("  Ctrl+C to stop")
    print("==========================================")
    while True:
        tick()
        time.sleep(300)  # check every 5 min

if __name__ == "__main__":
    main()