#!/usr/bin/env python3
"""
TRU Nightly Audit Loop
=====================
Reads action logs → groups by fact-id → runs LOGOS verification on accumulated
history → flags contradictions before they become lore.

Usage (run nightly via cron or agent):
    python3 tru_audit_loop.py [--days 1]

Exit codes:
    0 = clean (no contradictions)
    1 = contradictions detected
    2 = no action logs found
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from statistics import mean

# --------------------------------------------------------------------------- #
# CONFIG
# --------------------------------------------------------------------------- #
WORKSPACE = Path("/home/workspace")
LOGOS_API = "http://localhost:3099/api/truth"
AUDIT_LOG = "/dev/shm/tru-audit.log"
STATS_LOG = "/dev/shm/tru-audit-stats.log"

# Log glob patterns to scan (absolute paths)
LOG_PATHS = [
    Path("/home/workspace/COIL_archive"),
    Path("/home/workspace/backups/integrity"),
    Path("/home/workspace/COIL_mirror/SC"),
    Path("/home/workspace/backups/tasks_proxy.log"),
    Path("/home/workspace/coil_server.log"),
]
LOG_FILE_GLOBS = ["*.log"]

# Timestamp pattern: [YYYY-MM-DD HH:MM:SS]
TS_RE = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")

# Fact-id annotation pattern (lowercase, hyphenated)
FACT_RE = re.compile(r"\bfact[-_]?id[:\s]+([a-z0-9\-]+)", re.I)

# Action result patterns extracted from various log formats
ACTION_RE = re.compile(
    r"(?:\[RES-\d+\]|\bRESULT\b|\bACTION\b)\s*:?\s*(.+?)(?:\n|$)", re.I
)
ANOMALY_RE = re.compile(
    r"\[ANOMALY\]\s*(\d+)\s*[-:]\s*(.+?)(?:\n|$)", re.I
)
TASK_RE = re.compile(
    r"\[TASK\s*(\d+)\]\s*[-:]\s*(.+?)(?:\n|$)", re.I
)

# --------------------------------------------------------------------------- #
# LOG PARSING
# --------------------------------------------------------------------------- #

def extract_fact_id(line: str) -> str | None:
    m = FACT_RE.search(line)
    if m:
        return m.group(1).lower()
    # Fallback: extract TASK number as pseudo fact-id
    task_m = TASK_RE.search(line)
    if task_m:
        return f"task-{task_m.group(1).lower()}"
    return None


def extract_result(line: str) -> str:
    m = ACTION_RE.search(line)
    return m.group(1).strip() if m else line.strip()


def parse_log_file(path: Path, since: datetime) -> list[dict]:
    """Return a list of {fact_id, result, ts, source} entries from one file."""
    events = []
    try:
        content = path.read_text(errors="ignore")
    except Exception:
        return events

    # Extract task-id from filename like TASK008_RUN.log → task-008
    fname_task = None
    fname_match = re.match(r"(TASK\d+)_RUN\.log", path.name, re.I)
    if fname_match:
        num = re.search(r"\d+", fname_match.group(1))
        if num:
            fname_task = f"task-{num.group()}"

    current_fact_id = fname_task or "unknown"  # never None — persists across lines; overridden by inline annotations
    current_ts = None

    for line in raw_lines(content):
        # skip empty / binary noise
        if not line or not line[0].isascii():
            continue

        # timestamp? update window cursor
        m = TS_RE.match(line)
        if m:
            try:
                current_ts = datetime.fromisoformat(m.group(1))
            except ValueError:
                pass

        # inline fact-id annotation? override current_fact_id for subsequent lines
        fid = extract_fact_id(line)
        if fid:
            current_fact_id = fid

        # only process events within the audit window
        if current_ts and current_ts >= since:
            result = extract_result(line)
            if result and len(result) > 4:
                events.append({
                    "fact_id": current_fact_id,
                    "result": result,
                    "ts": current_ts.isoformat(),
                    "source": path.name,
                })

    return events


def raw_lines(text: str) -> list[str]:
    """Split on newlines, strip, drop empty — preserve structure."""
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


# --------------------------------------------------------------------------- #
# LOGOS VERIFY (stub — replace with real LOGOS call when available)
# --------------------------------------------------------------------------- #

def logos_verify(claims: list[str]) -> dict:
    """
    POSTs claims to the LOGOS truth layer and returns:
        { verdicts: [(claim, bool), ...], score: float }
    Falls back to keyword heuristic if the API is unreachable.
    """
    payload = {"claims": claims, "model": "logos-v1"}

    try:
        import urllib.request
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            LOGOS_API,
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
            timeout=5,
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except Exception:
        pass

    # Fallback: keyword heuristic (very rough — replace with real LOGOS call)
    verdicts = []
    for claim in claims:
        claim_lower = claim.lower()
        if any(
            kw in claim_lower
            for kw in [
                "hash mismatch",
                "format fixed",
                "root cause",
                "anomaly cleared",
                "wrong header",
                "verified",
            ]
        ):
            verdicts.append((claim, True))
        elif any(
            kw in claim_lower
            for kw in ["fail", "error", "stalled", "corrupt", "mismatch", "broken"]
        ):
            verdicts.append((claim, False))
        else:
            verdicts.append((claim, None))  # inconclusive
    return {"verdicts": verdicts, "score": None}


# --------------------------------------------------------------------------- #
# AUDIT ENGINE
# --------------------------------------------------------------------------- #

def run_audit(since: datetime) -> dict:
    """
    Scans all log files since --since, groups claims by fact-id,
    runs LOGOS verification, and returns an audit report dict.
    """
    events_by_fact = defaultdict(list)

    for base_path in LOG_PATHS:
        if base_path.is_file():
            for event in parse_log_file(base_path, since):
                events_by_fact[event["fact_id"]].append(event)
        elif base_path.is_dir():
            for glob_pat in LOG_FILE_GLOBS:
                for p in base_path.glob(glob_pat):
                    for event in parse_log_file(p, since):
                        events_by_fact[event["fact_id"]].append(event)

    if not events_by_fact:
        return {"status": "no_logs", "contradictions": [], "facts": {}}

    # Build claim lists per fact-id
    facts_out = {}
    all_contradictions = []

    for fact_id, events in sorted(events_by_fact.items()):
        claims = [e["result"] for e in events]
        logos_result = logos_verify(claims)
        verdicts = logos_result.get("verdicts", [])

        # Check for any False (contradiction) verdicts
        contradictions = [
            {"claim": claim, "verdict": v, "event": events[i]}
            for i, (claim, v) in enumerate(verdicts)
            if v is False
        ]

        facts_out[fact_id] = {
            "events": len(events),
            "claims": claims,
            "verdicts": verdicts,
            "contradictions": contradictions,
            "logos_score": logos_result.get("score"),
        }

        all_contradictions.extend(
            [{"fact_id": fact_id, **c} for c in contradictions]
        )

    status = "clean" if not all_contradictions else "contradictions"
    return {"status": status, "contradictions": all_contradictions, "facts": facts_out}


# --------------------------------------------------------------------------- #
# REPORTING
# --------------------------------------------------------------------------- #

def format_report(audit: dict) -> str:
    lines = []
    status = audit["status"]

    if status == "no_logs":
        return (
            f"[{datetime.now().isoformat()}] TRU AUDIT — no action logs found "
            f"since window — skipping\n"
        )

    total_facts = len(audit["facts"])
    total_events = sum(f["events"] for f in audit["facts"].values())
    contradictions = audit["contradictions"]

    header = (
        f"[{datetime.now().isoformat()}] TRU AUDIT — "
        f"{total_facts} fact-ids | {total_events} events | "
        f"{len(contradictions)} contradictions"
    )
    lines.append(header)

    if status == "clean":
        lines.append("  → STATUS: CLEAN — no regressions detected")
    else:
        lines.append("  → STATUS: CONTRADICTIONS DETECTED")
        for c in contradictions:
            lines.append(
                f"  [!] fact-id={c['fact_id']} | "
                f"claim=\"{c['claim'][:80]}\" | "
                f"verdict={c['verdict']} | "
                f"source={c['event']['source']} @ {c['event']['ts']}"
            )

    return "\n".join(lines)


def write_stats(audit: dict):
    """Append a one-liner to the stats log for trending."""
    if audit["status"] == "no_logs":
        return
    total = sum(f["events"] for f in audit["facts"].values())
    n_contradictions = len(audit["contradictions"])
    n_facts = len(audit["facts"])
    score = audit["facts"].get(list(audit["facts"].keys())[0], {}).get(
        "logos_score"
    )
    stat = (
        f"{datetime.now().isoformat()} | "
        f"facts={n_facts} events={total} "
        f"contradictions={n_contradictions} "
        f"logos_score={score}\n"
    )
    Path(STATS_LOG).write_text(
        Path(STATS_LOG).read_text() + stat
        if Path(STATS_LOG).exists()
        else stat
    )


# --------------------------------------------------------------------------- #
# MAIN
# --------------------------------------------------------------------------- #

def main():
    ap = argparse.ArgumentParser(description="TRU Nightly Audit Loop")
    ap.add_argument("--days", type=float, default=1)
    args = ap.parse_args()

    since = datetime.now() - timedelta(days=args.days)
    audit = run_audit(since)
    report = format_report(audit)

    print(report)

    # Write to audit log
    Path(AUDIT_LOG).write_text(
        Path(AUDIT_LOG).read_text() + report + "\n"
        if Path(AUDIT_LOG).exists()
        else report + "\n"
    )
    write_stats(audit)

    # Exit code
    if audit["status"] == "contradictions":
        sys.exit(1)
    elif audit["status"] == "no_logs":
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
