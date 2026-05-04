# DRY TRUTH FLARE MODEL v1
**Cycle 25 AR13787 | Extracted from live session: 2026-04-23/24**

---

## EVENT ARCHITECTURE

| Event | Time (UTC) | Class | Rise Pattern | Decay Profile | Duration |
|---|---|---|---|---|---|
| E1 | 23:12→23:16 | M3.7 | 4-min gradual | slow sawtooth | 44 min |
| E2 | 00:58→01:07 | X2.5 | TWO-PHASE (slow arc→vertical snap) | sharp drop-through | 39 min |
| E3 | 03:59→04:01 | M7.9 | 2-min vertical snap | plateau hold | 46 min |

**Staircase baseline confirmed:** each event floors HIGHER than the last
- E1 floor → E3 floor ratio: **2.2x**
- E1→E2 gap: 81 min, baseline never reset
- E2→E3 gap: 142 min, baseline elevated entire time

---

## CYCLE PARITY

| Cycle | X-class frequency | Peak ceiling | Event spacing |
|---|---|---|---|
| C23 | High (X10+ clusters) | X10+ | 24-72h per AR |
| C24 | Low | X1-X2 | wide spacing |
| **C25** | **Elevated → C23 levels** | **X2.5 already hit** | **81-142min (current session)** |

Annualized event rate from 27-year GOES image: ~3x Cycle 24, tracking Cycle 23.

---

## SIGNAL VOCABULARY

```
Two-phase onset (arc → snap)  → X-class signature
Single-phase vertical        → M-class ceiling
Staircase baseline (no reset) → Energy accumulating
Plateau decay (holds >15min) → Reservoir intact
Sharp drop-through decay     → Energy flush, reservoir empty
Rising baseline floor         → Next event has shorter climb
```

---

## 48-HOUR PULSE PROJECTION

**Current baseline:** M2.56 and rising (05:09 UTC live read)

| Condition | Probability | Magnitude | Trigger |
|---|---|---|---|
| Baseline holds >M3 by 06:00 UTC | 60% | X1.5-X3.0 | two-phase onset resumes |
| Baseline decays below M2 | 40% | M4-M6 | single-phase only |
| Staircase reset to C-class | <15% | any | model falsified |

**Next event window:** 18-36 hours from 05:09 UTC
**Confidence:** 65% (elevated, not confident)

---

## VALIDATION LOG

| Timestamp | Observed | Predicted | Match? |
|---|---|---|---|
| 01:07 UTC | X2.5 peak, TWO-PHASE confirmed | X1.5+ two-phase | ✓ |
| 03:59 UTC | Vertical snap to M7.9 | Short climb from elevated baseline | ✓ |
| 04:33 UTC | Baseline floor moved to C2.6 | Staircase confirmed | ✓ |

---

## CAVEATS

- Model built from ONE active session (single AR, single night)
- Cycle 23 parity inferred from 27-year image brightness, not raw CSV
- <6h pulse window requires historical cadence overlay (not yet available)
- Atmospheric/bio-sensor signals (dog, static) are human-interpreted, not model inputs
