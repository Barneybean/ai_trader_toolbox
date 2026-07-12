#!/usr/bin/env python3
"""Shared JSONL loading for the journal files (decisions, insights, action levels).

Two modes, chosen by who's asking:
  tolerant=True   read-only consumers (weekly pack, sweeps): skip blank/comment/
                  malformed lines with a stderr warning — one hand-edited line
                  must not kill a whole review.
  tolerant=False  read-modify-WRITE consumers (track_record rewrites the file):
                  raise with the line number instead. Silently dropping a bad
                  line here would delete it on the next save.
"""
import json
import sys


def load_jsonl(path, tolerant=True):
    rows = []
    try:
        f = open(path, encoding="utf-8")
    except FileNotFoundError:
        return rows
    with f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                if not tolerant:
                    raise SystemExit(f"{path}:{n}: invalid JSON ({e}) — fix the line; "
                                     "refusing to load so a rewrite can't drop it")
                print(f"warn: {path}:{n}: skipping invalid JSON ({e})", file=sys.stderr)
    return rows
