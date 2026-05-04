#!/usr/bin/env python3
"""
PROJECT_X_MONITOR — SPLASHDOWN v2.3.0
NOAA + SolarMonitor.org dual-source | Data quality validation | Auto-fallback
"""
import requests, time, json, os
from datetime import datetime, timezone
from threading import Thread

BASE_URL    = "https://coil-sync-server-splashdown.zocomputer.io"
MISSION_DIR = "/home/workspace/mission"
CSV_FILE    = f"{MISSION_DIR}/mission_log_APR28.csv"
STATE_F    = f"{MISSION_DIR}/PROJECT_X_STATE.json"
CONFIG_F    = f"{MISSION_DIR}/PROJECT_X_CONFIG.json"

# ─── Config ──────────────────────────────────────────────
DEFAULT_CONFIG = {
    "qqq_entry": 663.88,
    "vix_entry": 18.71,
    "vix_abort_threshold": 2.2,
    "status": "DEPLOYED",
    "target_window": "April 28-30, 2026",
    "vix_threshold": 0.4,
    "abortion_threshold_percent": 3.5,
}

# ─── Solar Sources (in priority order) ─────────────────────
SOLAR_SOURCES = [
    {
        "name": "NOAA SWPC Primary",
        "url": "https://services.swpc.noaa.gov/json/goes/16/xrays_1m.json",
        "timeout": 10,
        "flux_key": lambda d: float(d[-1]["peak_intensity"]) if d else None,
        "time_key": lambda d: d[-1]["time_tag"] if d else None,
        "sat_key": lambda d: d[-1].get("satellite", "GOES-16") if d else "unknown",
    },
    {
        "name": "NOAA SWPC Secondary",
        "url": "https://services.swpc.noaa.gov/json/goes/18/xrays_1m.json",
        "timeout": 10,
        "flux_key": lambda d: float(d[-1]["peak_intensity"]) if d else None,
        "time_key": lambda d: d[-1]["time_tag"] if d else None,
        "sat_key": lambda d: d[-1].get("satellite", "GOES-18") if d else "unknown",
    },
    {
        "name": "SolarMonitor.org",
        "url": "SKIP",  # Dynamic URL — constructed in parser
        "timeout": 12,
        "flux_key": None,
        "time_key": None,
        "sat_key": None,
    },
]

# ─── Helpers ───────────────────────────────────────────────
def load_config():
    return json.load(open(CONFIG_F)) if os.path.exists(CONFIG_F) else DEFAULT_CONFIG.copy()

def load_state():
    if os.path.exists(STATE_F):
        return json.load(open(STATE_F))
    return {"position_open": False, "entry_qqq": 0, "entry_vix": 0,
            "entry_date": "", "alerts": [], "trade_log": [],
            "position_closed": False, "last_solar_flux": None,
            "solar_source": None, "early_onset_triggered": False}

def save_state(s): open(STATE_F,"w").write(json.dumps(s, indent=2))
def save_config(c): open(CONFIG_F,"w").write(json.dumps(c, indent=2))

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] {msg}", flush=True)

# ─── Data Quality Validation ─────────────────────────────
class DataQualityError(Exception): pass

def validate(name, value, lo, hi):
    if value is None:
        raise DataQualityError(f"{name} is None")
    if not (lo <= value <= hi):
        raise DataQualityError(f"{name}={value} outside [{lo},{hi}]")

# ─── Solar ────────────────────────────────────────────────
def get_solar():
    """Try all solar sources in order, return (flux, source_name, class)"""
    # ── NOAA sources first ──
    noaa_sources = [
        {
            "name": "NOAA SWPC Primary",
            "url": "https://services.swpc.noaa.gov/json/goes/16/xrays_1m.json",
            "timeout": 10,
        },
        {
            "name": "NOAA SWPC Secondary",
            "url": "https://services.swpc.noaa.gov/json/goes/18/xrays_1m.json",
            "timeout": 10,
        },
    ]

    for src in noaa_sources:
        try:
            log(f"Trying solar source: {src['name']}")
            r = requests.get(src["url"], timeout=src["timeout"])
            if r.status_code != 200:
                log(f"  {src['name']}: HTTP {r.status_code} — trying next")
                continue
            raw = r.text.strip()
            if not raw or raw.startswith("<"):
                log(f"  {src['name']}: HTML response — trying next")
                continue
            data = json.loads(raw)
            if not isinstance(data, list) or len(data) < 2:
                log(f"  {src['name']}: Unexpected JSON structure — trying next")
                continue
            flux = float(data[-1]["peak_intensity"])
            if flux is None or flux <= 0:
                log(f"  {src['name']}: Invalid flux {flux} — trying next")
                continue
            flux_class = classify_flare(flux)
            ts = data[-1]["time_tag"]
            sat = data[-1].get("satellite", "GOES-16")
            log(f"  ✅ {src['name']}: flux={flux:.2e} [{flux_class}] satellite={sat} at {ts}")
            return flux, src["name"], flux_class
        except DataQualityError as e:
            log(f"  {src['name']}: Data quality failed — {e}")
            continue
        except Exception as e:
            log(f"  {src['name']}: Error — {e}")
            continue

    # ── SolarMonitor.org: parse NOAA events raw file ──
    try:
        log("Trying solar source: SolarMonitor.org")
        today = datetime.now(timezone.utc)
        y, m, d = today.year, f"{today.month:02d}", f"{today.day:02d}"
        url = f"https://solarmonitor.org/data/{y}/{m}/{d}/meta/noaa_events_raw_{y}{m}{d}.txt"
        r2 = requests.get(url, timeout=12)
        if r2.status_code != 200:
            log(f"  SolarMonitor.org: events file HTTP {r2.status_code}")
        else:
            import re
            flares = []
            for line in r2.text.splitlines():
                if not line or line.startswith(('#', ':')): continue
                parts = line.split()
                if len(parts) < 10: continue
                particulars = parts[9]
                match = re.match(r'^([CMX])(\d+\.?\d*)$', particulars)
                if match:
                    cls = match.group(1)
                    val = float(match.group(2))
                    flux = val * 1e-4 if cls == 'X' else val * 1e-5 if cls == 'M' else val * 1e-6
                    sat = parts[4]
                    max_ut = parts[2]
                    flares.append({'class': cls + str(val), 'flux': flux, 'max_ut': max_ut, 'sat': sat})
            if flares:
                strongest = max(flares, key=lambda f: f['flux'])
                log(f"  ✅ SolarMonitor.org: [{strongest['sat']}] {strongest['class']} flux={strongest['flux']:.2e}")
                return strongest['flux'], "SolarMonitor.org", strongest['class'][0]
            else:
                log("  SolarMonitor.org: no flare events found today")
    except Exception as e:
        log(f"  SolarMonitor.org: parse error — {e}")

    return None, "ALL_DOWN", None

def classify_flare(flux):
    if flux is None: return "UNKNOWN"
    if flux >= 1e-4: return "X"
    if flux >= 1e-5: return "M"
    if flux >= 1e-6: return "C"
    if flux >= 1e-7: return "B"
    return "A"

# ─── Market ────────────────────────────────────────────────
def get_live_market():
    """QQQ + VIX from Yahoo Finance with validation"""
    headers = {"User-Agent": "Mozilla/5.0"}
    qqq_price, vix_price = None, None

    try:
        # QQQ
        r = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/QQQ",
            params={"interval": "1d", "range": "5d"},
            headers=headers, timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            result = data.get("chart", {}).get("result", [{}])
            meta = result[0].get("meta", {}) if result else {}
            qqq_price = float(meta.get("regularMarketPrice", 0))
            validate("QQQ", qqq_price, 100, 1200)
            log(f"QQQ: {qqq_price}")
    except Exception as e:
        log(f"QQQ fetch error: {e}")

    try:
        # VIX via data table
        r = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX",
            params={"interval": "1d", "range": "5d"},
            headers=headers, timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            result = data.get("chart", {}).get("result", [{}])
            meta = result[0].get("meta", {}) if result else {}
            vix_price = float(meta.get("regularMarketPrice", 0))
            validate("VIX", vix_price, 8, 80)
            log(f"VIX: {vix_price}")
    except Exception as e:
        log(f"VIX fetch error: {e}")

    if qqq_price is None:
        raise DataQualityError("QQQ unavailable from all sources")
    return qqq_price, vix_price

# ─── CSV Logging ────────────────────────────────────────────
CSV_COLS = ["Timestamp_UTC", "GOES_Sat", "Flux_W_m2", "Flux_Class",
            "Signal", "VIX", "QQQ", "Position", "Note",
            "Solar_Source", "Stool_Source", "Market_Mode"]

def log_row(state, cfg, flux, cls_val, src, signal, vix, qqq, pos, note=""):
    ts = datetime.now(timezone.utc).isoformat()
    line = f"{ts},{cfg.get('goes_sat','GOES-16')},{flux},{cls_val},"
    line += f"{signal},{vix},{qqq},{pos},{note},"
    line += f"{src},YHOO,{cfg.get('market_mode','1d')}"
    # Append or create
    if not os.path.exists(CSV_FILE):
        open(CSV_FILE,"w").write(",".join(CSV_COLS) + "\n")
    open(CSV_FILE,"a").write(line + "\n")
    log(f"Row logged: {signal} | flux={flux} [{cls_val}] | VIX={vix} | QQQ={qqq}")

# ─── Trade Triggers ────────────────────────────────────────
def check_triggers(state, cfg, qqq, vix):
    alerts = []
    stopped = False

    vix_now = vix - state["entry_vix"]
    qqq_pct = (qqq - state["entry_qqq"]) / state["entry_qqq"] * 100
    cfg_mode = cfg.get("market_mode", "1d")

    # Abortion
    if abs(vix_now) > cfg.get("abortion_threshold_percent", 3.5):
        direction = "RISING" if vix_now > 0 else "FALLING"
        alerts.append(f"🛑 VIX {direction} {abs(vix_now):.1f}% > {cfg.get('abortion_threshold_percent',3.5)}% threshold — ABORT TRADE")
        stopped = True

    # Soft stop
    if qqq_pct < -3.5 and not stopped:
        alerts.append(f"⚠️ QQQ DOWN {qqq_pct:.1f}% — close to soft stop")

    # M-class trigger
    if cfg["status"] == "DEPLOYED" and not state["position_open"]:
        if vix >= cfg.get("vix_threshold", 0.4):
            alerts.append(f"✅ VIX trigger confirmed {vix:.2f} >= {cfg['vix_threshold']} threshold")

    return alerts, stopped

# ─── Main Tick ─────────────────────────────────────────────
def tick():
    cfg   = load_config()
    state = load_state()
    now   = datetime.now(timezone.utc)
    day   = now.strftime("%Y-%m-%d")

    log(f"\n{'='*60}")
    log(f"PROJECT_X MONITOR | {day} {now.strftime('%H:%M UTC')}")

    # ── Solar (dual source) ──
    flux, solar_src, cls_val = get_solar()
    if flux:
        log(f"✅ SOLAR: {flux:.2e} [{cls_val}] via {solar_src}")
        state["last_solar_flux"] = flux
        state["solar_source"] = solar_src
        # Auto-trigger on M or X
        if cfg["status"] == "READY_FOR_DEPLOYMENT" and cls_val in ("M", "X"):
            log(f"🚀 SOLAR PEAK CONFIRMED — {cls_val}-class")
            alerts.append(f"SOLAR PEAK {cls_val} via {solar_src}")
            cfg["status"] = "DEPLOYED"
            save_config(cfg)
    else:
        log("⚠️ ALL SOLAR SOURCES DOWN — using screenshot override")
        # Read from screenshot state if available
        screenshot_flux = state.get("screenshot_flux")
        if screenshot_flux:
            flux = screenshot_flux
            cls_val = classify_flare(flux)
            solar_src = state.get("screenshot_source", "SCREENSHOT")
            log(f"Using screenshot data: {flux:.2e} [{cls_val}]")

    # ── Market ──
    vix, qqq = None, None
    try:
        qqq, vix = get_live_market()
        log(f"Market — QQQ:{qqq}  VIX:{vix}")
    except DataQualityError as e:
        log(f"Market data error: {e} — using last known values")
        vix = state.get("last_vix")
        qqq = state.get("last_qqq")

    # ── Position management ──
    alerts = []
    stopped = False

    if not state["position_open"] and cfg["status"] == "DEPLOYED":
        state["position_open"] = True
        state["entry_qqq"] = qqq or state["entry_qqq"]
        state["entry_vix"] = vix or state["entry_vix"]
        state["entry_date"] = now.isoformat()
        alerts.append(f"POSITION OPEN — QQQ:{qqq} VIX:{vix}")
        log(f"📌 POSITION OPEN — QQQ:{qqq}  VIX:{vix}")

    if state["position_open"] and vix and qqq:
        trigger_alerts, stopped = check_triggers(state, cfg, qqq, vix)
        alerts.extend(trigger_alerts)
        if stopped:
            state["position_open"] = False
            state["position_closed"] = True
            state["alerts"].append(f"CLOSED at {now.isoformat()}")
            log("🛑 POSITION CLOSED")

    # ── Log row ──
    signal = "READY" if cfg["status"] == "READY_FOR_DEPLOYMENT" else "ACTIVE"
    pos = "OPEN" if state["position_open"] else ("CLOSED" if state.get("position_closed") else "WAITING")
    note = " | ".join(alerts) if alerts else ""
    log_row(state, cfg, flux or 0, cls_val or "UNKNOWN",
            solar_src or "N/A", signal, vix or 0, qqq or 0, pos, note)

    # ── Save state ──
    if vix: state["last_vix"] = vix
    if qqq: state["last_qqq"] = qqq
    save_state(state)

    # ── COIL heartbeat ──
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        log(f"COIL heartbeat: {r.status_code}")
    except Exception as e:
        log(f"⚠️ COIL unreachable: {e}")

    log(f"State saved — QQQ:{state.get('entry_qqq','—')}  VIX:{state.get('entry_vix','—')}  [{pos}]")

# ─── Main ─────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  PROJECT_X MONITOR — SPLASHDOWN v2.3.0")
    print("  NOAA + SolarMonitor.org dual-source")
    print("  Apr 28-30, 2026  |  Ctrl+C to stop")
    print("=" * 60)

    # Ensure mission dir
    os.makedirs(MISSION_DIR, exist_ok=True)

    while True:
        tick()
        time.sleep(300)  # 5-minute ticks

if __name__ == "__main__":
    main()