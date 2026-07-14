# ADR-0013: Verified issue traceability and no routine branch bypass

- **Status:** Accepted
- **Date:** 2026-07-13
- **Deciders:** Repository owner and toolkit maintainer

## Context

The contribution template required `Closes #…`, but CI only recognized issue-shaped text in the PR
description. It did not prove that the issue existed in this repository or contained a rationale and
acceptance criteria. The governance bootstrap also demonstrated that an administrator could bypass
the host's PR rule, leaving no review record despite file-based checks.

The same audit found a stale `manual` public-default statement and an unclassified
`scripts/execution/` path. Both weaken the source-sync policy precisely where execution authority
requires the strongest review.

## Decision

We will validate closing references through GitHub's read-only issue API. Every referenced issue
must be open, belong to the current repository, be an issue rather than a PR, and contain a
completed use-case/reason section plus acceptance criteria. The PR keeps its separate rationale
requirement. The policy lives in a stdlib-only tested script invoked by CI and the smoke suite.

We will classify `scripts/execution/**` as sanitization-required, keep `semi` as the single public
default with `manual` as the kill switch, and prohibit routine administrator or automation bypass
of branch protection. A break-glass path is limited to audited, reversible containment.

## Consequences

Traceability now depends on the GitHub issue API being available to CI, and older issues may need
their rationale or acceptance criteria filled in before a PR can close them. Contributors get a
clear failure instead of a syntactic pass. High-authority execution code cannot silently enter the
generic reusable-candidate path, and repository settings remain an explicit administrative duty.

## Alternatives considered

- **Continue checking PR text only** — rejected because an unrelated or nonexistent reference can
  satisfy a regex without creating an auditable issue.
- **Copy full-auto files before classifying the directory** — rejected because execution authority,
  broker scope, and private configuration require sanitization before code review.
- **Allow routine administrator bypass** — rejected because it defeats the required review trail.
