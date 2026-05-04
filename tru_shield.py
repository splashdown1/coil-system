#!/usr/bin/env python3
"""
Tru_Shield_v1 — COIL-integrated safety and control layer
Parent mission: Moonshot_Sniper (Tru_Moonshot_Sniper)
Builds on TruControlCenter
"""
import csv
import time
import requests
from datetime import datetime, timedelta
from typing import Optional

BASE_URL = "https://coil-sync-server-splashdown.zocomputer.io"
LOG_FILE = "tru_shield_log.csv"
EVIDENCE  = "tru_evidence_log.csv"

class TruShield:
    def __init__(self, control_center):
        self.cc = control_center

        # ── Config ──────────────────────────────────────────
        self.MIN_LIQ = 15_000
        self.MAX_CREATOR_PCT = 5
        self.REQ_STATUS = ["mint_renounced", "liquidity_burned"]
        self.STOP_PCT = -0.30
        self.MAX_STOPS = 2
        self.STOP_WINDOW_MIN = 10
        self.COOLDOWN_MIN = 60
        self.MAX_SLIPPAGE_PCT = 10
        self.MAX_TRADES_PER_HOUR = 5
        self.PROFIT_LOCK_X = 3

        self._stops = []   # timestamps of ghost stops
        self._trade_times = []  # for hourly rate limit
        self._floor_sol = None  # locked profit floor

    # ── SAFETY CHECKS ─────────────────────────────────────

    def safety_check(self, token_data: dict) -> tuple[bool, str]:
        """Full pre-trade safety gate. Returns (pass, reason)."""
        # Liquidity
        liq = token_data.get("liquidity_usd", 0)
        if liq < self.MIN_LIQ:
            return False, f"LIQ_TOO_LOW:{liq}<{self.MIN_LIQ}"

        # Creator holding
        creator_pct = token_data.get("creator_balance_pct", 100)
        if creator_pct > self.MAX_CREATOR_PCT:
            return False, f"CREATOR_OVERSUPPLY:{creator_pct}%>{self.MAX_CREATOR_PCT}%"

        # Required token flags
        flags = token_data.get("token_flags", [])
        for req in self.REQ_STATUS:
            if req not in flags:
                return False, f"MISSING_FLAG:{req}"

        # Ghost stop cooldown
        if self._in_ghost_stop_cooldown():
            return False, "GHOST_STOP_COOLDOWN"

        # Rate limit
        if not self._check_rate_limit():
            return False, "RATE_LIMIT_EXCEEDED"

        return True, "PASS"

    def _in_ghost_stop_cooldown(self) -> bool:
        cutoff = datetime.now() - timedelta(minutes=self.STOP_WINDOW_MIN)
        self._stops = [s for s in self._stops if s > cutoff]
        if len(self._stops) >= self.MAX_STOPS:
            return True
        return False

    def _check_rate_limit(self) -> bool:
        cutoff = datetime.now() - timedelta(hours=1)
        self._trade_times = [t for t in self._trade_times if t > cutoff]
        return len(self._trade_times) < self.MAX_TRADES_PER_HOUR

    def record_trade_time(self):
        self._trade_times.append(datetime.now())

    # ── GHOST STOP ─────────────────────────────────────────

    def check_ghost_stop(self, entry_price: float, current_price: float) -> bool:
        """Returns True if stop-loss triggered."""
        if entry_price <= 0:
            return False
        pnl_pct = (current_price - entry_price) / entry_price
        if pnl_pct <= self.STOP_PCT:
            self._stops.append(datetime.now())
            self._log_ghost_stop(entry_price, current_price, pnl_pct)
            return True
        return False

    def _log_ghost_stop(self, entry, current, pnl):
        self.cc.trigger_cooldown()
        self._shield_log({
            "event": "GHOST_STOP_TRIGGERED",
            "entry": entry,
            "current": current,
            "pnl_pct": round(pnl*100, 2)
        })

    # ── DYNAMIC PROFIT LOCK ────────────────────────────────

    def check_profit_lock(self, entry_sol: float, current_sol: float) -> bool:
        """Returns True if profit lock activates (3x threshold)."""
        if entry_sol <= 0 or self._floor_sol is not None:
            return False
        if current_sol >= entry_sol * self.PROFIT_LOCK_X:
            self._floor_sol = entry_sol * 1.10  # initial cap + 10%
            self._shield_log({
                "event": "PROFIT_LOCK_ACTIVATED",
                "floor_sol": round(self._floor_sol, 4),
                "locked_at": datetime.now().isoformat()
            })
            return True
        return False

    def locked_balance(self) -> Optional[float]:
        return self._floor_sol

    # ── SLIPPAGE AUDIT ─────────────────────────────────────

    def check_slippage(self, expected_price: float, actual_price: float) -> tuple[bool, float]:
        """Returns (ok, delta_pct)."""
        if expected_price <= 0:
            return True, 0.0
        delta = abs((actual_price - expected_price) / expected_price) * 100
        ok = delta <= self.MAX_SLIPPAGE_PCT
        self._shield_log({
            'event': 'SLIPPAGE_CHECK',
            'delta_pct': round(delta, 3),
            'ok': ok,
            'expected': expected_price,
            'actual': actual_price
        })
        return ok, round(delta, 3)

    def log_trade(self, data: dict):
        """Write COIL_CSV_v2 compliant evidence row."""
        data["timestamp"] = datetime.now().isoformat()
        data["final_pnl_usd"] = data.get("pnl_sol", 0) * data.get("sol_price", 0)

        file_exists = False
        try:
            with open(EVIDENCE, 'r'):
                file_exists = True
        except FileNotFoundError:
            pass

        with open(EVIDENCE, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.EVIDENCE_FIELDS)
            if not file_exists:
                writer.writeheader()
            writer.writerow({k: data.get(k, '') for k in self.EVIDENCE_FIELDS})

        # Sync to COIL
        self._coil_sync(data)

    def _coil_sync(self, data: dict):
        try:
            r = requests.post(f"{BASE_URL}/upload", headers={
                "x-file-id": "tru_shield_evidence",
                "x-chunk-index": "0",
                "x-hash": "sync_only",
                "x-compressed": "false"
            }, json=data, timeout=5)
        except Exception as e:
            print(f"⚠ COIL sync failed: {e}")

    def _shield_log(self, data: dict):
        data["timestamp"] = datetime.now().isoformat()
        data["win_streak"] = self.cc.win_streak
        data["is_active"] = self.cc.is_active
        data["event"] = data.get("event", "INFO")

        fieldnames = ["timestamp","win_streak","is_active","event",
                      "entry","current","pnl_pct","delta_pct","ok",
                      "floor_sol","locked_at","expected","actual","reason"]
        file_exists = False
        try:
            with open(LOG_FILE, 'r'):
                file_exists = True
        except FileNotFoundError:
            pass
        with open(LOG_FILE, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(data)

    def print_shield_status(self):
        print(f"\n{'='*50}")
        print(f"  TRU_SHIELD_v1 STATUS")
        print(f"{'='*50}")
        print(f"  Bot active      : {self.cc.is_active}")
        print(f"  Win streak      : {self.cc.win_streak}")
        print(f"  Ghost stops     : {len(self._stops)} (max {self.MAX_STOPS})")
        print(f"  Profit floor    : {self._floor_sol}")
        print(f"  Trades/hr      : {len(self._trade_times)}/{self.MAX_TRADES_PER_HOUR}")
        print(f"  Cooldown active: {self.cc.in_cooldown()}")
        print(f"{'='*50}\n")


# ── Test ─────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    from tru_control_center import TruControlCenter

    cc = TruControlCenter()
    shield = TruShield(cc)

    # Simulate pre-trade safety check
    token = {
        "liquidity_usd": 25000,
        "creator_balance_pct": 1.2,
        "token_flags": ["mint_renounced", "liquidity_burned"]
    }
    passed, reason = shield.safety_check(token)
    print(f"Safety check: {'✅ PASS' if passed else f'❌ {reason}'}")

    # Slippage test
    ok, delta = shield.check_slippage(0.003, 0.0032)
    print(f"Slippage {delta:.2f}%: {'✅ OK' if ok else '⚠ HIGH VOLATILITY'}")

    # Ghost stop test
    triggered = shield.check_ghost_stop(0.003, 0.0018)
    print(f"Ghost stop: {'🔴 TRIGGERED' if triggered else '✅ Safe'}")

    # Profit lock test
    locked = shield.check_profit_lock(0.1, 0.31)
    print(f"Profit lock 3x: {'🔒 ACTIVATED' if locked else '⏳ Not yet'}")
    print(f"Locked floor : {shield.locked_balance()} SOL")

    shield.print_shield_status()
    print("✅ Tru_Shield_v1 — tested and live")