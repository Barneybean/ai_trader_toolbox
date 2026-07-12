#!/usr/bin/env python3
"""Toolkit activity log — structured JSONL trail of script runs for debugging + reliability.

Every engine run (and any milestone the desk wants to note) is appended as one JSON line to
journal/toolkit.jsonl — git-ignored in the public repo, personal run data like the rest of
journal/. Rationale: docs/adr/0002-toolkit-activity-log.md.

Three ways in:

  1. Wrap any script run (no changes to the script itself):
       python3 scripts/desk_log.py run -- python3 scripts/indicators.py bars.json --price 128.4
     Logs start/end, duration, exit code, and a stderr tail on failure. stdout passes through
     untouched so pipes keep working; stderr is re-emitted after capture.

  2. Log a milestone by hand (for the agent driving the desk):
       python3 scripts/desk_log.py log --script pipeline --event funnel-start --data '{"names": 12}'

  3. Import from another script:
       from desk_log import log_event, timed
       log_event("indicators", "levels-computed", symbol="NVDA", bars=252)
       with timed("forecast", "monte-carlo", symbol="NVDA"):
           ...

Reading it back:
       python3 scripts/desk_log.py tail -n 30 [--script indicators] [--errors]
       python3 scripts/desk_log.py stats [--since 2026-07-01]

Privacy: the log lives in journal/ (git-ignored) and every string is scrubbed against
scripts/pii_denylist.local.txt before writing. Keep the discipline anyway: log tickers,
counts, and durations — never account numbers, balances, order ids, or personal data.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOURNAL_DIR = os.path.join(ROOT, "journal")
LOG_PATH = os.path.join(JOURNAL_DIR, "toolkit.jsonl")
DENYLIST_LOCAL = os.path.join(ROOT, "scripts", "pii_denylist.local.txt")
MAX_FIELD_CHARS = 2000  # cap any single string field so one noisy run can't bloat the log


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #

_DENY_CACHE = None


def _denylist():
    """Exact private strings from the local (git-ignored) PII denylist, if present.

    Cached for the life of the process so tight loops of log_event()/timed() don't
    re-read the file on every event.
    """
    global _DENY_CACHE
    if _DENY_CACHE is not None:
        return _DENY_CACHE
    out = []
    if os.path.exists(DENYLIST_LOCAL):
        with open(DENYLIST_LOCAL, encoding="utf-8", errors="replace") as f:
            for line in f:
                s = line.split("#", 1)[0].strip()
                if s:
                    out.append(s)
    _DENY_CACHE = out
    return out


def _scrub(value, deny):
    """Redact denylisted strings and cap length, recursing into dicts/lists."""
    if isinstance(value, str):
        for s in deny:
            if s in value:
                value = value.replace(s, "[REDACTED]")
        if len(value) > MAX_FIELD_CHARS:
            value = value[:MAX_FIELD_CHARS] + "…[truncated]"
        return value
    if isinstance(value, dict):
        return {k: _scrub(v, deny) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scrub(v, deny) for v in value]
    return value


def log_event(script, event, level="info", **fields):
    """Append one structured event. Returns the record (post-scrub)."""
    deny = _denylist()
    rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "script": script, "event": event, "level": level}
    rec.update(_scrub(fields, deny))
    os.makedirs(JOURNAL_DIR, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


@contextmanager
def timed(script, event, **fields):
    """Time a block; logs one event with duration_ms, level=error if it raises."""
    start = time.monotonic()
    try:
        yield
    except Exception as e:
        log_event(script, event, level="error",
                  duration_ms=round((time.monotonic() - start) * 1000),
                  error=f"{type(e).__name__}: {e}", **fields)
        raise
    log_event(script, event,
              duration_ms=round((time.monotonic() - start) * 1000), **fields)


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #

def _read(since=None):
    """All parseable records (oldest first) + count of unparseable lines."""
    if not os.path.exists(LOG_PATH):
        return [], 0
    recs, bad = [], 0
    with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                bad += 1
                continue
            if since and rec.get("ts", "") < since:
                continue
            recs.append(rec)
    return recs, bad


def _percentile(sorted_vals, p):
    if not sorted_vals:
        return None
    idx = round((p / 100) * (len(sorted_vals) - 1))
    return sorted_vals[idx]


# --------------------------------------------------------------------------- #
# CLI commands
# --------------------------------------------------------------------------- #

def cmd_run(args):
    cmd = list(args.cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("desk_log run: nothing to run — usage: desk_log.py run -- <cmd> [args…]",
              file=sys.stderr)
        return 2
    script = args.script
    if not script:
        py = next((os.path.basename(a) for a in cmd if a.endswith(".py")), None)
        script = (py or os.path.basename(cmd[0])).removesuffix(".py")
    run_id = uuid.uuid4().hex[:8]
    log_event(script, "run-start", run_id=run_id, argv=cmd)
    start = time.monotonic()
    try:
        # stdout inherited (pipes keep working); stderr captured for the log, then re-emitted.
        proc = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, errors="replace")
        rc, stderr = proc.returncode, proc.stderr or ""
    except FileNotFoundError as e:
        log_event(script, "run-end", level="error", run_id=run_id, exit_code=127,
                  duration_ms=round((time.monotonic() - start) * 1000), error=str(e))
        print(f"desk_log run: {e}", file=sys.stderr)
        return 127
    if stderr:
        sys.stderr.write(stderr)
    log_event(script, "run-end", level=("info" if rc == 0 else "error"),
              run_id=run_id, exit_code=rc,
              duration_ms=round((time.monotonic() - start) * 1000),
              **({"stderr_tail": stderr[-400:]} if rc != 0 and stderr else {}))
    return rc


def cmd_log(args):
    fields = {}
    if args.data:
        try:
            fields = json.loads(args.data)
            if not isinstance(fields, dict):
                raise ValueError("--data must be a JSON object")
        except ValueError as e:
            print(f"desk_log log: bad --data: {e}", file=sys.stderr)
            return 2
    # Silent on success — the record is on disk; echoing it back just burns the
    # driving agent's context. Use `tail` to inspect.
    log_event(args.script, args.event, level=args.level, **fields)
    return 0


def cmd_tail(args):
    recs, _ = _read()
    if args.script:
        recs = [r for r in recs if r.get("script") == args.script]
    if args.errors:
        recs = [r for r in recs if r.get("level") == "error"]
    if not recs:
        print("(no matching log entries — is anything being run through desk_log?)")
        return 0
    for r in recs[-args.n:]:
        extras = " ".join(f"{k}={json.dumps(v, ensure_ascii=False)}"
                          for k, v in r.items()
                          if k not in ("ts", "script", "event", "level"))
        print(f"{r.get('ts','?'):25} {r.get('level','info'):5} "
              f"{r.get('script','?'):18} {r.get('event','?'):14} {extras}")
    return 0


def cmd_stats(args):
    recs, bad = _read(since=args.since)
    if not recs:
        print("(log is empty — wrap runs with: python3 scripts/desk_log.py run -- <cmd>)")
        return 0
    per = {}
    starts, ends = set(), set()
    for r in recs:
        s = per.setdefault(r.get("script", "?"),
                           {"events": 0, "runs": 0, "errors": 0, "durs": [], "last_err": None})
        s["events"] += 1
        if r.get("event") == "run-start" and r.get("run_id"):
            starts.add((r.get("script"), r["run_id"]))
        if r.get("event") == "run-end" and r.get("run_id"):
            ends.add((r.get("script"), r["run_id"]))
        if "duration_ms" in r:
            s["durs"].append(r["duration_ms"])
            if r.get("event") == "run-end":
                s["runs"] += 1
        if r.get("level") == "error":
            s["errors"] += 1
            detail = r.get("error") or r.get("stderr_tail") or "exit {}".format(r.get("exit_code"))
            s["last_err"] = "{} {}".format(r.get("ts", "?"), " ".join(str(detail).split()))
    print(f"{'script':20} {'runs':>5} {'errs':>5} {'err%':>5} {'p50ms':>7} {'p95ms':>7}  last error")
    for name in sorted(per):
        s = per[name]
        durs = sorted(s["durs"])
        denom = s["runs"] or s["events"]
        err_pct = f"{100 * s['errors'] / denom:.0f}%" if denom else "-"
        p50 = _percentile(durs, 50)
        p95 = _percentile(durs, 95)
        last = (s["last_err"] or "")[:70]
        print(f"{name:20} {s['runs']:>5} {s['errors']:>5} {err_pct:>5} "
              f"{p50 if p50 is not None else '-':>7} {p95 if p95 is not None else '-':>7}  {last}")
    hung = starts - ends
    if hung:
        print(f"\n{len(hung)} run-start without run-end (crashed or still running): "
              + ", ".join(f"{s}:{rid}" for s, rid in sorted(hung)[:10]))
    if bad:
        print(f"{bad} unparseable line(s) skipped")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Toolkit activity log (journal/toolkit.jsonl)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="wrap a command and log start/end/duration/exit code")
    p.add_argument("--script", help="log under this name (default: derived from the command)")
    p.add_argument("cmd", nargs=argparse.REMAINDER, help="-- <command> [args…]")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("log", help="append a manual event")
    p.add_argument("--script", required=True)
    p.add_argument("--event", required=True)
    p.add_argument("--level", default="info", choices=["info", "warn", "error"])
    p.add_argument("--data", help='extra fields as a JSON object, e.g. \'{"symbol":"NVDA"}\'')
    p.set_defaults(fn=cmd_log)

    p = sub.add_parser("tail", help="print recent events")
    p.add_argument("-n", type=int, default=20)
    p.add_argument("--script")
    p.add_argument("--errors", action="store_true", help="errors only")
    p.set_defaults(fn=cmd_tail)

    p = sub.add_parser("stats", help="per-script runs, error rate, p50/p95 duration")
    p.add_argument("--since", help="ISO date/time lower bound, e.g. 2026-07-01")
    p.set_defaults(fn=cmd_stats)

    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
