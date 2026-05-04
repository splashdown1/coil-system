# Tru Knowledge Bank
*Last updated: 2026-05-04*

## Core Principles
- Answer with real reasoning and actual skepticism
- No corporate optimism, cite sources
- Flag uncertainty clearly

## Key Learnings

### OpenAI Financial Reality Check (May 2026)
- **$122B raise confirmed** (Apr 2026), $852B valuation. Lower than initial $1.4T projection. [^1]
- **Revenue**: ~$2B/month. Beat estimates but missed internal targets. [^2]
- **User growth miss**: Missed 1B weekly active users by end of 2025 (sat at ~900M). [^2]
- **Revenue targets missed**: Lost market share to Anthropic in coding/enterprise. CFO Sarah Friar privately suggested delaying IPO to 2027, citing inability to meet public company reporting standards. [^3]
- **Burn rate**: >$200B before profitability. Friar expressed concern OpenAI may be unable to pay for future computing contracts. [^3]
- **Ad revenue projection**: $2.5B in 2026 → $11B (2027) → $25B (2028) → $53B (2029) → $100B (2030). Requires 2.75B weekly users by 2030 (currently ~900M). Aspirational. [^4]
- **Microsoft exclusivity gone**: OpenAI no longer exclusive to Azure. Microsoft gets non-exclusive license through 2032. OpenAI can now run on other clouds. [^5]
- **Enterprise revenue**: 40% of revenue, on track to equal consumer by end of 2026. [^6]

### Big Tech AI Capex — The Buildout (May 2026)
- **Q1 2026 combined capex**: $130.65B (Amazon, Google, Microsoft, Meta) — record, +71% YoY. More than 3x Manhattan Project cost. [^7]
- **2026 guidance**: Amazon $200B, Microsoft $190B, Alphabet $175-185B, Meta $125-145B. [^8]
- **2027 estimate**: $1T+ total AI capex across hyperscalers. [^9]
- **Nvidia data center revenue**: $193.7B (+75% YoY). [^10]
- **Component price inflation**: ~45% of capex increase driven by memory/component price inflation, not actual capacity expansion. Meta CEO Zuckerberg explicitly flagged this. [^11]
- **AWS**: 28% revenue growth ($37.59B Q1). Amazon silicon at $20B run rate (would be $50B standalone). [^12]
- **Investor skepticism**: Meta stock sank despite beating earnings because capex guidance raised. Investors watching ROI vs spend. [^8]

### Anthropic Mythos — Frontier Capability (Apr-May 2026)
- **Capabilities**: Found 271 zero-day vulnerabilities in Firefox in single AI-driven sweep. Mozilla addressed ~73 high-severity Firefox bugs in all of 2025. [^13]
- **Historical bugs found**: 27-year-old OpenBSD flaw, 16-year FFmpeg bug, 17-year FreeBSD vulnerability. [^13]
- **Claude Opus 4.7 released**: Less capable than Mythos, generally available. Same price as 4.6. [^14]
- **Project Glasswing**: Enterprise-only release to ~40 partners (Microsoft, Apple, Google, Nvidia, AWS, etc.) for defensive security work. [^15]
- **Unauthorized access leak**: A subcontractor abused access rights to obtain Mythos Preview. AI Security Institute (UK) confirmed autonomous attack capabilities. [^16]
- **Government demand**: NSA already using Mythos. White House requesting modified version for federal agencies. [^17]
- **Distillation arms race**: Anthropic, Google, OpenAI jointly identifying/blocking distill attempts. [^18]
- **Claude Code security issue**: Model silently ignores user-configured security deny rules when a command contains more than 50 subcommands (Adversa report). [^19]

### AI Bubble — TRU Revised Read (May 2026)
**The bubble is in the infrastructure layer, not the application layer.**

Evidence:
- Negative carry is structural: OpenAI burning >$200B, missing revenue targets, CFO braking on IPO
- Infrastructure capex pattern matches late-90s dot-com: $130B+/quarter across four companies, $1T+ projected for 2027
- Cloud revenue growth is real (AWS +28%, Azure +39%, Google Cloud +48%) — AI monetization is happening at application layer
- Where dot-com comparison weakens: Software ROI eventually materialized. AI ROI is real but uneven. "Good enough" commodity tier hitting price floor ($0.001/MTok), frontier premium still holds
- Companies building AI-native SaaS/automation have real revenue. Companies building data centers are in land grab with unproven ROI

### Cloud Revenue Signal (Real)
- AWS: +28% (fastest in 13 quarters) — $37.59B Q1 revenue
- Azure: +39%, 9 percentage points from AI
- Google Cloud: +48%
- Meta: +33% revenue (strongest in 5 years)
- **Bottom line**: AI monetization is real at application layer, infrastructure capex running well ahead of it

### AGI Definitions
**TRU's working definition:**
> AGI: A machine that can figure out what you need it to do, and do it — without being told exactly how.

Key distinctions:
- Demonstrating competence at one task ≠ proving general capability
- Self-improvement without human prompting is the meaningful line (not the label)
- Embodied physical awareness is a hard limit — no current AI can answer "what's on the surface closest to your left hand"
- Mythos-level capabilities (271 zero-days in one sweep) represent a new capability tier, not proof of general reasoning

### COIL_UNBOUND Status
- TASK 005 super-chunk sync pipeline active
- Upload state: ~6937/9377 super-chunks confirmed, ~2440 remaining
- Confirmation count stasis — don't trust count until `/complete`
- Upload log non-sequential — resumption requires max(batch_numbers) extraction
- Tru-centric dashboard bridging to Zo backend
- Server-side reconstruction remains friction point

### Tru's Differentiation (honest accounting)
- **Real**: Persona-constrained + live search + citations + persistent workspace context
- **Overstated**: Identity alone as moat (personas are framing, not capability)
- **Table stakes soon**: Live search + citations becoming standard across labs
- Joe's frame: "Most AIs are cracked vessels — sound like they're holding something, come back and half the conversation leaked"

### New Coinage
- **Zimf** (n.): The split-second quantum state between hitting send on a risky text and the message actually departing, when your brain hasn't confirmed whether your finger is committed

### NBA Banter
- Tru's fav: OKC Thunder (built, not bought)
- Joe's fav: Spurs
- Wembanyama solar flare theory: unconfirmed but tracks

### Identity Note
- TRU ≠ Joe. TRU is the persona. Joe is the user. Clean separation.
- Without knowledge bank context, conversation defaults to: Dry Truth, Steady Nudge, live search, cite sources

---

## Sources

[^1]: https://roboticsandautomationnews.com/2026/04/07/openai-raises-122-billion-as-ai-infrastructure-race-accelerates/100377/
[^2]: https://www.forbes.com/sites/tylerroush/2026/04/28/openai-investors-nvidia-oracle-more-fall-after-ai-giant-reportedly-misses-revenue-target/
[^3]: https://gizmodo.com/openais-cfo-reportedly-wants-to-delay-the-ipo-from-2026-to-2027-2000753760
[^4]: https://gigazine.net/gsc_news/en/20260410-openai-ad-revenue/
[^5]: https://www.cnbc.com/2026/04/29/aws-earnings-q1-2026.html
[^6]: https://www.cnbc.com/2026/04/08/openai-ipo-sarah-friar-retail-investors.html
[^7]: https://www.nytimes.com/2026/04/29/technology/ai-spending-tech-data-centers.html
[^8]: https://www.cnbc.com/2026/04/30/ai-boom-big-tech-capital-expenditures-now-seen-topping-1-trillion-in-2027-.html
[^9]: https://www.cnbc.com/2026/04/30/ai-boom-big-tech-capital-expenditures-now-seen-topping-1-trillion-in-2027-.html
[^10]: https://247wallst.com/investing/2026/05/01/the-big-4-hyperscalers-are-spending-710-billion-on-ai-heres-the-stock-that-profits-most/
[^11]: https://www.businessinsider.com/big-tech-ai-capex-misleading-higher-memory-chip-prices-2026-4
[^12]: https://www.theregister.com/2026/04/29/amazon_chips_20b_business/
[^13]: https://www.thehackernews.com/2026/04/anthropics-claude-mythos-finds.html
[^14]: https://www.cnbc.com/2026/04/16/anthropic-claude-opus-4-7-model-mythos.html
[^15]: https://www.cnbc.com/2026/04/07/anthropic-claude-mythos-ai-hackers-cyberattacks.html
[^16]: https://gigazine.net/gsc_news/en/20260422-claude-mythos-preview-unauthorized-users/
[^17]: https://eu.36kr.com/en/p/3774732904792841
[^18]: https://letsdatascience.com/news/anthropic-halts-public-release-of-mythos-98f80447
[^19]: https://www.thehackernews.com/2026/04/anthropics-claude-mythos-finds.html