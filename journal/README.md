# Journal — private runtime memory

This directory is where AI Trader Toolbox keeps a user's decisions, action levels, reflections,
insights, mentor overlay, and report memory. Those records describe a real person and portfolio,
so the data files are git-ignored and are not shipped from the maintainer's Trading Desk.

The tools under `scripts/journal/` create and read the local files as needed. New users begin with
an empty journal and build their own history through normal use. Commit only fictional fixtures
that are clearly labeled and reviewed against `docs/open-source-boundary.md`.
