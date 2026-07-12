# ADR-0003: Contribution self-review — condensed wording + consistency gate before any PR

- **Status:** Accepted
- **Date:** 2026-07-11
- **Deciders:** desk owner + desk agent

## Context

The toolkit's Markdown is not documentation in the ordinary sense — `SKILL.md` and `skills/`
are loaded into agent context on every desk run, so verbose contributions tax every future
run in tokens. And as contributors add playbooks, skills, and engines, nothing mechanically
prevented conflicting additions: a playbook written twice, a reference to a renamed file, an
ADR contradicted rather than superseded, a coverage map that drifts from the directory.
Review caught these late, after the contributor considered the work done.

## Decision

We will require a **self-review before any PR**, documented in `CONTRIBUTING.md` and echoed
in the PR template: (1) run the gates locally, (2) a condensed-wording pass over the diff,
(3) a conflict pass against `docs/adr/`, the coverage maps, and neighboring skills.

The mechanical half is enforced by `scripts/check_consistency.py` (stdlib), run in the
pre-push hook and in CI (`.github/workflows/consistency.yml`). **Errors (block):** broken
internal links, ADR-integrity violations, unregistered sector/stock playbooks,
case-colliding filenames. **Warnings (reviewer judgment):** word budgets (~2,600 words per
skill file, ~5,500 for `SKILL.md` — calibrated so the existing tree passes clean) and
engines no doc mentions. The gate includes untracked files so it works before anything is
staged.

Semantic conflicts — contradicting an accepted ADR's method, adding a competing mechanism —
stay a human/reviewer responsibility; the checklist names them explicitly.

## Consequences

- Conflicts and bloat surface on the contributor's machine, not in review.
- Word budgets create pressure to condense; the stated rule is "condense, don't split" —
  reviewers must watch for budget-dodging file splits.
- Every new engine must be registered in a doc or it warns forever — mild friction, but it
  keeps `SKILL.md`'s reference map complete.
- The gate's checks are curated in one script; as new conflict classes appear, they get
  added there (with an ADR if the policy itself changes).

## Alternatives considered

- **Review-only enforcement** — too late and inconsistent; mechanical checks belong to
  machines, and the public repo may see drive-by PRs that never read CONTRIBUTING.
- **Hard word-count errors** — a hard fail on prose length punishes legitimately deep
  playbooks; warnings plus a named reviewer judgment is the right altitude.
- **LLM-based conflict detection in CI** — could catch semantic conflicts, but adds a paid
  dependency to a stdlib-only, fork-anywhere repo; revisit if drift actually bites.
