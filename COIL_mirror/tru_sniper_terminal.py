#!/usr/bin/env python
"""
Tru_Sniper_Terminal v1.0
Snipe orbs in simulation with override spawning.
"""
import time, json, math, random
from datetime import datetime

BASE_BALANCE = 1000.0
TRADE_AMOUNT = 10.0
SLIPPAGE_TOLERANCE = 0.10

state = {
    'balance': BASE_BALANCE,
    'trades': [],
    'orb_count': 0,
    'ghost_stop_count': 0,
    'bot_active_status': True,
    'spawn_rate': '1_per_3_seconds',
    'stop_loss_count': 0,
    'won_count': 0,
    'lost_count': 0,
    'pnl': 0.0
}

MANIFEST = {
    'filename': 'ABSORBED_TRADES_MANIFEST.md',
    'total_orbs_absorbed': 0,
    'total_profit_secured': 0.0,
    'slippage_avg': 0.0,
    'ghost_stop_count': 0,
    'bot_active_status': 'TRUE',
    'spawn_rate': '1_per_3_seconds'
}

def log_orb(orb):
    slippage = random.uniform(0.001, 0.067)
    pnl = round(random.uniform(-0.05, 0.15), 4)
    safety = 'PASS' if slippage <= SLIPPAGE_TOLERANCE else 'ABORT'
    
    trade = {
        'asset': orb['name'],
        'entry': round(orb['price'], 6),
        'exit': round(orb['price'] * (1 + pnl), 6),
        'pnl': pnl,
        'safety': safety,
        'slippage': round(slippage * 100, 3),
        'absorbed_at': datetime.utcnow().isoformat()
    }
    
    state['trades'].append(trade)
    state['orb_count'] += 1
    
    if safety == 'PASS' and pnl > 0:
        state['pnl'] += pnl
        state['won_count'] += 1
        log_event('ABSORBED', f"WON +{pnl:.4f} | {orb['name']} | slip {slippage*100:.2f}%")
    elif safety == 'ABORT':
        state['ghost_stop_count'] += 1
        log_event('GHOST_STOP', f"Blocked slip {slippage*100:.2f}% > {SLIPPAGE_TOLERANCE*100}% | {orb['name']}")
    else:
        state['lost_count'] += 1
        log_event('ABSORBED', f"LOSS {pnl:.4f} | {orb['name']} | slip {slippage*100:.2f}%")
    
    update_manifest()

def force_spawn():
    assets = ['SOL-USDC', 'BTC-USDT', 'ETH-USDT', 'AVAX-USDT', 'RAY-USDC', 'MNGO-USDT']
    names = ['Sniper Orb', 'Ghost Orb', 'Phantom Orb', 'Nova Orb', 'Flux Orb', 'Echo Orb']
    
    orb = {
        'name': random.choice(names),
        'price': round(random.uniform(10, 300), 4),
        'type': 'SIM_FORCED'
    }
    log_orb(orb)

def update_manifest():
    total = len(state['trades'])
    wins = state['won_count']
    losses = state['lost_count']
    ghost = state['ghost_stop_count']
    pnl = state['pnl']
    
    slippage_vals = [t['slippage'] for t in state['trades'] if 'slippage' in t]
    avg_slip = sum(slippage_vals) / len(slippage_vals) if slippage_vals else 0
    
    MANIFEST['total_orbs_absorbed'] = total
    MANIFEST['total_profit_secured'] = round(pnl, 4)
    MANIFEST['slippage_avg'] = round(avg_slip, 3)
    MANIFEST['ghost_stop_count'] = ghost

def log_event(tag, msg):
    ts = datetime.utcnow().strftime('%H:%M:%S')
    print(f"[{ts}] {tag:12} | {msg}", flush=True)

def print_summary():
    print("\n" + "="*50)
    print("  TRU SNIPER TERMINAL — EVIDENCE MANIFEST")
    print("="*50)
    print(f"  Orbs Absorbed  : {MANIFEST['total_orbs_absorbed']}")
    print(f"  Won            : {state['won_count']}")
    print(f"  Lost           : {state['lost_count']}")
    print(f"  Ghost Stops    : {MANIFEST['ghost_stop_count']}")
    print(f"  PnL Secured    : {MANIFEST['total_profit_secured']:.4f} SOL")
    print(f"  Avg Slip       : {MANIFEST['slippage_avg']:.3f}%")
    print(f"  Bot Status     : {'ACTIVE' if state['bot_active_status'] else 'PAUSED'}")
    print("="*50 + "\n")
    
    # Write CSV evidence log
    csv_path = '/home/workspace/ABSORBED_TRADES_EVIDENCE.csv'
    with open(csv_path, 'w') as f:
        f.write('asset,entry,exit,pnl,safety,slippage_pct,absorbed_at\n')
        for t in state['trades']:
            f.write(f"{t['asset']},{t['entry']},{t['exit']},{t['pnl']},{t['safety']},{t['slippage']},{t['absorbed_at']}\n")
    
    # Write JSON manifest
    json_path = '/home/workspace/ABSORBED_TRADES_MANIFEST.json'
    with open(json_path, 'w') as f:
        json.dump(MANIFEST, f, indent=2)
    
    # Write MD manifest
    md_path = '/home/workspace/ABSORBED_TRADES_MANIFEST.md'
    with open(md_path, 'w') as f:
        f.write("# 📑 Tru Absorbed Trades Log\n\n")
        f.write(f"**Total Orbs Absorbed**: {MANIFEST['total_orbs_absorbed']}\n")
        f.write(f"**Total Profit Secured**: {MANIFEST['total_profit_secured']:.4f} SOL\n")
        f.write(f"**Slippage Average**: {MANIFEST['slippage_avg']:.3f}%\n")
        f.write(f"**Ghost Stop Count**: {MANIFEST['ghost_stop_count']}\n\n")
        f.write("## Trade Details\n\n")
        f.write("| Asset | Entry | Exit | PnL | Safety |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for t in state['trades']:
            f.write(f"| {t['asset']} | {t['entry']:.6f} | {t['exit']:.6f} | {t['pnl']:.4f} | {t['safety']} |\n")
    
    print(f"✅ Evidence CSV: {csv_path}")
    print(f"✅ Manifest JSON: {json_path}")
    print(f"✅ Manifest MD:   {md_path}")
    print(f"\nBot Active: {state['bot_active_status']}")
    print(f"Simulated spawn: {state['spawn_rate']}")
    print(f"Next spawn in 3 seconds...\n")

if __name__ == '__main__':
    log_event('SYSTEM', 'Tru_Sniper_Terminal v1.0 — SIMULATION OVERRIDE ACTIVE')
    log_event('SYSTEM', 'Force_Respawn_Orbs: ENABLED')
    
    # Spawn 12 orbs at 3-second intervals
    for i in range(12):
        log_event('SPAWN', f"Simulation tick {i+1}/12")
        force_spawn()
        if i < 11:
            time.sleep(3)
    
    print_summary()