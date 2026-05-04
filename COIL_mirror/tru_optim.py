#!/usr/bin/env python3
"""
Tru_Optimizer_v1 — Audit + Filter Tuner + Social Sync + Auto-Feedback
"""
import csv, json, os, requests
from datetime import datetime

CONFIG_F = "tru_optimization_report.json"
REPORT_CSV = "tru_optimization_report.csv"
COIL_URL = "https://coil-sync-server-splashdown.zocomputer.io"

class AuditEngine:
    def __init__(self):
        self.metrics = {"avg_slippage": 0, "profit_vs_slippage_ratio": 0, "execution_delay_ms": 0}
        self.trades = []

    def log_trade(self, slippage, profit, delay_ms):
        self.trades.append({"slippage": slippage, "profit": profit, "delay_ms": delay_ms})

    def compute(self):
        if not self.trades: return self.metrics
        total = len(self.trades)
        avg_slip = sum(t["slippage"] for t in self.trades) / total
        avg_profit = sum(t["profit"] for t in self.trades) / total
        ratio = avg_profit / avg_slip if avg_slip > 0 else 0
        avg_delay = sum(t["delay_ms"] for t in self.trades) / total
        self.metrics = {"avg_slippage": round(avg_slip, 4), "profit_vs_slippage_ratio": round(ratio, 2), "execution_delay_ms": round(avg_delay, 1)}
        return self.metrics

    def apply_throttle(self):
        m = self.metrics
        throttle = m["avg_slippage"] > 8
        if throttle:
            self._log({"event": "THROTTLE_APPLIED", "reason": "avg_slippage > 8%", "avg_slippage": m["avg_slippage"]})
            print(f"  [AUDIT] ⚠️  avg_slippage={m['avg_slippage']}% > 8% → THROTTLING pulse sensitivity")
        return throttle

    def _log(self, entry):
        entry["ts"] = datetime.utcnow().isoformat()
        entry["layer"] = "audit_engine"
        print(f"  [AUDIT] {entry}")

class FilterTuner:
    def __init__(self):
        self.rules = [
            {"label": "Top_10_Concentration", "max_holding_pct": 30, "action": "Block"},
            {"label": "Dev_Wallet_Cluster", "max_wallet_count": 3, "action": "Flag_Manual_Review"},
            {"label": "Liquidity_to_MC_Ratio", "min_ratio": 0.05, "action": "Block"},
        ]
        self.enhanced = True

    def evaluate(self, token_data):
        flags = []
        for rule in self.rules:
            val = token_data.get(rule["label"], 0)
            if rule["label"] == "Top_10_Concentration" and val > rule["max_holding_pct"]:
                flags.append(("BLOCK", f"Top10={val}% > {rule['max_holding_pct']}%"))
            elif rule["label"] == "Dev_Wallet_Cluster" and val > rule["max_wallet_count"]:
                flags.append(("MANUAL_REVIEW", f"DevWallets={val} > {rule['max_wallet_count']}"))
            elif rule["label"] == "Liquidity_to_MC_Ratio" and val < rule["min_ratio"]:
                flags.append(("BLOCK", f"LiMC={val:.3f} < {rule['min_ratio']}"))
        return flags

    def get_verdict(self, flags):
        if any(f[0] == "BLOCK" for f in flags): return "REJECT"
        if any(f[0] == "MANUAL_REVIEW" for f in flags): return "REVIEW"
        return "APPROVE"

class SocialPulseSync:
    def __init__(self):
        self.min_velocity = 10
        self.sentiment_threshold = 0.7
        self.min_human_pct = 0.4
        self.enabled = os.getenv("X_API_KEY") or os.getenv("TWITTER_BEARER_TOKEN")

    def evaluate(self, pulse_data):
        if not self.enabled:
            print("  [SOCIAL] ⚠️  No X API key — social pulse validation DISABLED")
            return 1.0
        velocity = pulse_data.get("tweet_velocity", 0)
        sentiment = pulse_data.get("sentiment_score", 0)
        human_pct = pulse_data.get("human_pct", 0)
        boost = 1.0
        if velocity >= self.min_velocity and sentiment >= self.sentiment_threshold and human_pct >= self.min_human_pct:
            boost = 2.0
            print(f"  [SOCIAL] ✅ BOOST x2 — velocity={velocity}, sentiment={sentiment}, human={human_pct:.0%}")
        elif velocity >= self.min_velocity:
            boost = 1.3
            print(f"  [SOCIAL] ⚠️  PARTIAL boost x1.3 — some signals weak")
        return boost

class TruOptimizer:
    def __init__(self):
        self.audit = AuditEngine()
        self.filter = FilterTuner()
        self.social = SocialPulseSync()
        self.session_trades = []

    def log_trade(self, slippage=0, profit=0, delay_ms=0):
        self.audit.log_trade(slippage, profit, delay_ms)
        self.session_trades.append({"slippage": slippage, "profit": profit, "ts": datetime.utcnow().isoformat()})

    def run_audit(self):
        m = self.audit.compute()
        print(f"\n  AUDIT REPORT: slippage={m['avg_slippage']}% | ratio={m['profit_vs_slippage_ratio']} | delay={m['execution_delay_ms']}ms")
        throttle = self.audit.apply_throttle()
        return {"metrics": m, "throttle_applied": throttle}

    def filter_token(self, token_data):
        flags = self.filter.evaluate(token_data)
        verdict = self.filter.get_verdict(flags)
        for flag in flags:
            print(f"  [FILTER] 🔸 {flag[0]} — {flag[1]}")
        print(f"  [FILTER] Verdict: {verdict}")
        return verdict

    def evaluate_pulse(self, pulse_data):
        return self.social.evaluate(pulse_data)

    def generate_report(self):
        m = self.audit.metrics
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "optimizer_version": "Tru_Optimizer_v1",
            "total_trades": len(self.session_trades),
            "metrics": m,
            "filters_active": len(self.filter.rules),
            "social_validation": self.social.enabled,
            "recommendations": [],
        }
        if m["avg_slippage"] > 8: report["recommendations"].append("THROTTLE_PULSE_SENSITIVITY")
        if m["profit_vs_slippage_ratio"] < 1.5: report["recommendations"].append("REVIEW_FEE_STRUCTURE")
        if not self.social.enabled: report["recommendations"].append("ENABLE_X_API_FOR_SOCIAL_BOOST")
        # Save JSON
        with open(CONFIG_F, "w") as f: json.dump(report, f, indent=2)
        # Save CSV
        with open(REPORT_CSV, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["ts","slippage","profit"])
            w.writeheader()
            for t in self.session_trades: w.writerow(t)
        print(f"\n  REPORT SAVED:")
        print(f"  JSON: {CONFIG_F}")
        print(f"  CSV:  {REPORT_CSV}")
        # Sync to COIL
        self._sync_to_coil(report)
        return report

    def _sync_to_coil(self, report):
        try:
            r = requests.post(f"{COIL_URL}/upload", headers={
                "x-file-id": "tru-optim-report",
                "x-chunk-index": "0",
                "x-hash": "sync",
                "x-compressed": "false"
            }, data=json.dumps(report), timeout=10)
            print(f"  COIL sync: {r.status_code}")
        except Exception as e:
            print(f"  COIL sync failed: {e}")

if __name__ == "__main__":
    opt = TruOptimizer()
    # Simulate a session
    for i in range(5):
        opt.log_trade(slippage=2.3 + i*0.5, profit=1.1 + i*0.2, delay_ms=120 + i*10)
    opt.run_audit()
    # Test filter
    test_token = {"Top_10_Concentration": 28, "Dev_Wallet_Cluster": 2, "Liquidity_to_MC_Ratio": 0.08}
    opt.filter_token(test_token)
    # Test pulse
    opt.evaluate_pulse({"tweet_velocity": 15, "sentiment_score": 0.75, "human_pct": 0.55})
    # Generate report
    opt.generate_report()
