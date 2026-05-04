#!/usr/bin/env python3
"""X-Class Launchpad Analysis — Cycle 23 Mirroring"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import json

# ── Data from solar_flare_projection.json ────────────────────────────────────
historical = [
    ("Apr 19",  "A", 1.1e-8),
    ("Apr 20",  "A", 9.8e-9),
    ("Apr 21",  "B", 4.2e-8),
    ("Apr 22",  "C", 9.3e-7),
    ("Apr 23",  "C", 2.8e-6),
    ("Apr 24",  "M", 1.2e-5),
    ("Apr 25",  "M", 3.1e-5),
    ("Apr 26",  "C", 4.4e-6),
]

projected = [
    ("Apr 27",  "C", 8.1e-6,  0.82),
    ("Apr 28",  "X", 1.1e-4,  0.61),
    ("Apr 29",  "M", 7.4e-5,  0.75),
]

# ── Benchmark delta-Ts from Cycle 23 analogs ────────────────────────────────
cycle23_deltaT = {
    "C-shelf onset → M-breakout": ("36h", "Apr22 → Apr24"),
    "M-peak → X-class":          ("12-24h", "Apr24-25"),
    "X-class window open":       ("48-60h from C-shelf", "Apr24-26"),
}

fig, axes = plt.subplots(2, 2, figsize=(16, 10))
fig.suptitle("X-Class Launchpad Analysis | Cycle 23 Historical Mirroring", 
            fontsize=16, fontweight='bold', color='#1a1a2e')

ax1, ax2, ax3, ax4 = axes.flat

# ════════════════════════════════════════════════════════
# Panel 1: Historical + Projected Flux
# ════════════════════════════════════════════════════════
ax = ax1

x_hist = list(range(len(historical)))
x_proj = list(range(len(historical), len(historical) + len(projected)))
all_labels = [h[0] for h in historical] + [p[0] for p in projected]

flux_hist = [h[2] for h in historical]
flux_proj = [p[2] for p in projected]
conf_proj = [p[3] for p in projected]

ax.semilogy(x_hist, flux_hist, 'o-', color='#00b4d8', linewidth=2.5, markersize=8, label='GOES-19 Historical')
ax.semilogy(x_proj, flux_proj, 's--', color='#ff6b35', linewidth=2.5, markersize=8, label='Pattern Escalation (Bullish)')

# Confidence band
for i, (x, f, c) in enumerate(zip(x_proj, flux_proj, conf_proj)):
    ax.fill_between([x-0.3, x+0.3], f*0.7, f*1.3, alpha=0.15, color='#ff6b35')

# Class threshold lines
for cls, y, color in [("M", 1e-5, "#ff4444"), ("X", 1e-4, "#cc0000")]:
    ax.axhline(y, color=color, linestyle=':', linewidth=1.2, alpha=0.7)
    ax.text(len(historical)+0.5, y*1.2, f"{cls}-class threshold", color=color, fontsize=8, va='bottom')

ax.set_xticks(list(x_hist) + list(x_proj))
ax.set_xticklabels(all_labels, rotation=45, ha='right', fontsize=9)
ax.set_ylabel("Watts·m⁻² (log scale)", fontsize=10)
ax.set_title("Step 1: CORRELATE — Historical C-Shelf Match", fontsize=11, fontweight='bold')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)

# ════════════════════════════════════════════════════════
# Panel 2: Delta-T Calculation
# ════════════════════════════════════════════════════════
ax = ax2

events = ["Apr 22\nC-Shelf Onset", "Apr 23\nC-Plateau (24h)", "Apr 24\nM-Breakout (48h)", 
          "Apr 25\nX-Class Peak (72h)", "Apr 26\nEnergy Retention", "Apr 27\nC-Shelf Again"]
y_pos  = [0, 1, 2, 3, 1.5, 0.5]
colors = ["#2196F3", "#4CAF50", "#ff9800", "#ff4444", "#9C27B0", "#2196F3"]

ax.scatter(range(len(events)), y_pos, c=colors, s=120, zorder=3)
for i, (e, y) in enumerate(zip(events, y_pos)):
    ax.annotate(e, (i, y), textcoords="offset points", xytext=(0,15), 
                ha='center', fontsize=9, fontweight='bold')

for i in range(len(events)-1):
    dy = y_pos[i+1] - y_pos[i]
    ax.annotate("", xy=(i+1, y_pos[i+1]), xytext=(i, y_pos[i]),
                arrowprops=dict(arrowstyle="->", color="#00ff88", lw=2))

ax.set_xticks(range(len(events)))
ax.set_xticklabels([f"Δ{i*12}h" for i in range(len(events))], fontsize=9)
ax.set_title("Step 2: CALCULATE Delta-T (Cycle 23 Benchmark)", fontsize=11, fontweight='bold')
ax.set_ylabel("Escalation Stage", fontsize=10)

# Delta-T boxes
delta_ts = ["0h", "+24h", "+48h", "+72h", "+96h", "+120h"]
for i, dt in enumerate(delta_ts):
    ax.annotate(dt, (i, y_pos[i]-0.3), ha='center', fontsize=8, color='#00ff88', fontweight='bold')

ax.axhline(3, color='#ff4444', linestyle='--', alpha=0.4, label="X-class zone")
ax.legend(fontsize=9)
ax.set_ylim(-1, 4)

# ════════════════════════════════════════════════════════
# Panel 3: Comparison Table
# ════════════════════════════════════════════════════════
ax = ax3
ax.axis('off')

table_data = [
    ["Metric",            "Cycle 23 Benchmark",  "Cycle 25 Current",   "Match?"],
    ["C-shelf onset",     "Apr 22",               "Apr 22",              "✓"],
    ["C-shelf duration",  "36-48h",               "36h+ (ongoing)",      "✓"],
    ["M-class breakout",  "Apr 24 (48h)",         "Apr 24",              "✓"],
    ["M→C retreat",        "Apr 25-26",            "Apr 25-26",           "✓"],
    ["Energy retention",  "HIGH",                 "HIGH",                "✓"],
    ["ΔT to X-class",     "36-60h",               "36-48h (projected)",  "✓"],
    ["X-class window",    "Apr 24-26",            "Apr 28-29 (proj)",    "~"],
]

table = ax.table(cellText=table_data, loc='center', cellLoc='center')
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1.2, 1.8)

# Style header row
for j in range(4):
    table[(0, j)].set_facecolor('#1a1a2e')
    table[(0, j)].set_text_props(color='white', fontweight='bold')

# Style rows
for i in range(1, len(table_data)):
    for j in range(4):
        if table_data[i][j] == "✓":
            table[(i, j)].set_facecolor('#e8f5e9')
            table[(i, j)].set_text_props(color='#2e7d32', fontweight='bold')
        elif table_data[i][j] == "~":
            table[(i, j)].set_facecolor('#fff3e0')
            table[(i, j)].set_text_props(color='#e65100', fontweight='bold')
        else:
            table[(i, j)].set_facecolor('#f5f5f5' if i % 2 == 0 else 'white')

ax.set_title("Step 3: PROJECT — Launchpad Comparison", fontsize=11, fontweight='bold', pad=20)

# ════════════════════════════════════════════════════════
# Panel 4: Confidence Projection Timeline
# ════════════════════════════════════════════════════════
ax = ax4

dates = ["Apr 26\n00Z", "Apr 27\n00Z", "Apr 28\n00Z", "Apr 28\n12Z", "Apr 29\n00Z"]
classes  = ["C",        "C→M",      "M→X",      "X-Peak",   "M-Relax"]
conf     = [0.82,       0.76,       0.68,       0.61,       0.74]
colors4  = ["#2196F3",  "#ff9800",  "#ff4444",  "#cc0000",  "#9C27B0"]

bars = ax.barh(range(len(dates)), conf, color=colors4, height=0.6, alpha=0.85)
for i, (bar, c) in enumerate(zip(bars, conf)):
    ax.text(c+0.02, bar.get_y()+bar.get_height()/2, f"{c:.0%}", 
            va='center', fontsize=9, fontweight='bold', color='#1a1a2e')

ax.set_yticks(range(len(dates)))
ax.set_yticklabels([f"{d}\n({cls})" for d, cls in zip(dates, classes)], fontsize=9)
ax.set_xlim(0, 1.1)
ax.set_xlabel("Confidence", fontsize=10)
ax.set_title("X-Class Window Confidence Timeline", fontsize=11, fontweight='bold')
ax.axvline(0.65, color='#ff4444', linestyle='--', linewidth=1.5, alpha=0.7, label="High-confidence threshold")
ax.legend(fontsize=9)
ax.grid(True, axis='x', alpha=0.3)

# Annotate X-class window
ax.annotate("X-CLASS WINDOW\nApr 28-29", xy=(0.68, 2.5), xytext=(0.82, 2.5),
            fontsize=10, fontweight='bold', color='#cc0000',
            arrowprops=dict(arrowstyle='->', color='#cc0000', lw=2),
            bbox=dict(boxstyle='round', facecolor='#ffebee', alpha=0.8))

plt.tight_layout()
plt.savefig('/home/workspace/xclass_launchpad_analysis.png', dpi=150, bbox_inches='tight',
            facecolor='#fafafa')
print("Saved: /home/workspace/xclass_launchpad_analysis.png")