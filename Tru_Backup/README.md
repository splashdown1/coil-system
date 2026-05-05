# Tru Backup — Generated 2026-05-04
# Contains: persona config, rules, automations, verified facts

## WHAT'S BACKED UP
- persona.json       — Dry Truth Steady Nudge persona (full prompt + metadata)
- rules.json         — Workspace rules
- automations.json   — 3 active automations
- verified_facts.json — LOGOS fact store (if present)
- AGENTS.md + SOUL.md — Workspace memory + persona

## WHAT'S NOT IN GIT (lost on restart)
- Persona settings (lives in Zo DB — covered here)
- Automations (lives in Zo DB — covered here)
- Rules (lives in Zo DB — covered here)
- Zo service configs (auto-restored by Zo infra)

## RESTORE INSTRUCTIONS
1. Persona: Settings → AI → Personas → import from persona.json
2. Rules: recreate via create_rule tool using rules.json
3. Automations: recreate via create_automation tool using automations.json
4. AGENTS.md + SOUL.md: copy back to /home/workspace/
