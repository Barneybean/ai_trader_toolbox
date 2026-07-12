## What & why

<!-- One paragraph: what this PR adds or changes, and why it makes the base desk better for everyone. -->

## Type

- [ ] 📚 Playbook — sector/industry (`skills/analysis/sectors/`) or single-stock (`skills/analysis/stocks/`)
- [ ] 🧠 Skill / methodology improvement (`skills/`)
- [ ] 🔌 Broker adapter
- [ ] ⚙️ Engine change (`scripts/`)
- [ ] 📝 Docs

## Checklist

- [ ] **Self-review done** (see `CONTRIBUTING.md`): `python3 scripts/ops/check_consistency.py` and `python3 scripts/ops/scan_pii.py` both pass locally
- [ ] **Condensed wording** — the diff was reread and cut; no filler in agent-context files (`SKILL.md`, `skills/`)
- [ ] **No conflicts** — doesn't contradict an accepted ADR (supersede instead), duplicate a playbook, or add a competing way to do something an existing skill already covers
- [ ] `python3 scripts/ops/scan_pii.py` passes — no account numbers, keys, personal positions, or private data
- [ ] Nothing proprietary or paid that I don't have the right to share
- [ ] **Playbooks:** follows the matching `_TEMPLATE.md` (all seven fields) and is registered in its coverage map (`sectors/README.md` + `sector-playbooks.md`, or `stocks/README.md`)
- [ ] **Playbooks:** meets the quality bar — specific · falsifiable · primary-sourced · dated · illustrated · general (see `CONTRIBUTING.md`); stock-playbook episodes are dated history, not live calls
- [ ] **Engines:** stay pure Python stdlib (a genuinely needed dependency was discussed in an issue first)
