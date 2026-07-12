#!/usr/bin/env python3
"""Compatibility launcher; canonical implementation: scripts/lib/desk_log.py."""
from pathlib import Path
import runpy
import sys

_SCRIPTS = Path(__file__).resolve().parent
for _group in ("lib", "analysis", "journal", "report", "ops"):
    sys.path.insert(0, str(_SCRIPTS / _group))
runpy.run_path(str(_SCRIPTS / "lib" / "desk_log.py"), run_name="__main__")
