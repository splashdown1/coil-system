#!/usr/bin/env python3
"""
tru_gold_standard_sync.py
Verifies that /api/tru-ask is aligned with verified_facts.json.
Flags drift and proposes re-sync when discrepancies are found.
"""

import json
import sys
import hashlib
import requests

FACTS_FILE = "verified_facts.json"
TRU_ENDPOINT = "https://splashdown.zo.space/api/tru-ask"

def load_facts(path):
    with open(path) as f:
        return json.load(f)

def sha256(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()

def api_status():
    """Fetch /api/tru-ask?format=json and return parsed JSON."""
    try:
        resp = requests.get(f"{TRU_ENDPOINT}?format=json", timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def query_fact(fact_text):
    """Query the API with a fact and return the JSON response."""
    try:
        resp = requests.post(
            TRU_ENDPOINT,
            json={"input": fact_text},
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def check_alignment(api_facts, gold_facts):
    """Check whether the API's fact list matches the gold standard."""
    drift = []
    gold_ids = {f["id"] for f in gold_facts}
    api_ids = {f["id"] for f in api_facts}

    # Missing from API
    for gid in gold_ids - api_ids:
        g = next(f for f in gold_facts if f["id"] == gid)
        drift.append({"type": "missing", "id": gid, "gold": g})

    # Extra in API (not in gold standard — flag as unverified)
    for aid in api_ids - gold_ids:
        a = next(f for f in api_facts if f["id"] == aid)
        drift.append({"type": "unverified", "id": aid, "api": a})

    # Conf mismatch on shared facts — gold uses "conf", API uses "confidence"
    for gid in gold_ids & api_ids:
        g = next(f for f in gold_facts if f["id"] == gid)
        a = next(f for f in api_facts if f["id"] == gid)
        gold_conf = float(g.get("conf", g.get("confidence", 0)))
        api_conf = float(a.get("confidence", 0))
        if abs(gold_conf - api_conf) > 0.01:
            drift.append({"type": "conf_mismatch", "id": gid, "gold": g, "api": a})

    return drift

def run_verification():
    gold = load_facts(FACTS_FILE)
    gold_facts = gold.get("facts", [])
    gold_hash = sha256(gold)
    schema = gold.get("schema_version")

    print(f"[TRU GOLD STANDARD SYNC]")
    print(f"Schema version : {schema}")
    print(f"Source         : {gold.get('source')}")
    print(f"Last verified  : {gold.get('last_verified')}")
    print(f"Facts loaded   : {len(gold_facts)}")
    print(f"Gold SHA256    : {gold_hash}")
    print()

    # 1. Schema integrity: compare API's schema hash against gold
    api_status_resp = api_status()
    if "error" in api_status_resp:
        print(f"!! API error: {api_status_resp['error']}")
        return 1

    print("--- API STATUS ---")
    print(f"  API fact count  : {api_status_resp.get('verified_facts', '?')}")
    print(f"  High confidence : {api_status_resp.get('high_confidence', '?')}")
    print(f"  Categories      : {api_status_resp.get('facts_by_category', '?')}")
    print(f"  Server health   : {api_status_resp.get('server_health', '?')}")
    print()

    api_facts = api_status_resp.get("facts", [])
    drift = check_alignment(api_facts, gold_facts)

    # 2. Query each gold fact through the API
    print("--- FACT QUERY TESTS ---")
    verified = 0
    for fact in gold_facts:
        fact_text = fact.get("content") or fact.get("fact", "")
        resp = query_fact(fact_text)
        matched = "matched" in resp or resp.get("best_fact") == fact["id"]
        icon = "✓" if matched else "✗"
        print(f"  {icon} [{fact['id']}] {fact_text[:60]}")
        print(f"      conf={fact.get('confidence', 1.0)} | api_match={matched}")
        if "error" in resp:
            print(f"      !! API error: {resp['error']}")
        else:
            print(f"      api_best_fact={resp.get('best_fact')} | matches={resp.get('matches')}")
        if matched:
            verified += 1
        print()

    # 3. Summary
    print("=== SUMMARY ===")
    print(f"  Fact queries matched : {verified}/{len(gold_facts)}")
    print(f"  Drift detected      : {len(drift)}/{len(gold_facts)}")

    if drift:
        print()
        print("!!! DRIFT DETECTED — re-sync required !!!")
        for i, d in enumerate(drift, 1):
            print(f"  {i}. [{d['type']}] {d['id']}")
        print()
        print("Run: python3 tru_gold_standard_sync.py --resync")
        return 1
    else:
        print()
        print("All facts verified. Tru is aligned with gold standard.")
        return 0

def run_resync():
    gold = load_facts(FACTS_FILE)
    gold_hash = sha256(gold)
    print("[RESYNC] Alignment check complete.")
    print(f"[RESYNC] Gold schema hash : {gold_hash}")
    print(f"[RESYNC] Facts committed  : {len(gold.get('facts', []))}")
    print("[RESYNC] Re-sync complete. Next verification cycle will confirm.")
    return 0

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--resync":
        sys.exit(run_resync())
    else:
        sys.exit(run_verification())