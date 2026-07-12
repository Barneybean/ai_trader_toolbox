#!/usr/bin/env python3
"""Unified, compact recall across reports, trades, lessons, and methodology.

HTML remains the human artifact. ``journal/report-memory.jsonl`` is the agent
sidecar: English report text, tickers, methods, and the durable HTML path. Use
``context`` before analysis and ``rebuild`` after importing old reports.
"""
import argparse
import html
from html.parser import HTMLParser
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JOURNAL = os.path.join(ROOT, "journal")
MEMORY = os.path.join(JOURNAL, "report-memory.jsonl")
REPORTS = os.path.join(ROOT, "reports")
sys.path.insert(0, os.path.join(ROOT, "scripts", "lib"))
from jsonl import load_jsonl  # noqa: E402

REPORT_RE = re.compile(r"report_(\d{4}-\d{2}-\d{2})_(.+?)_(.+?)\.(?:html|md)$")
SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
METHOD_FILES = {
    "variant-perception": "skills/edge/variant-perception.md",
    "thematic-wave": "skills/edge/thematic-waves.md",
    "smart-money": "skills/edge/smart-money.md",
    "chip-distribution": "skills/analysis/chip-distribution.md",
    "money-flow": "skills/analysis/money-flow.md",
    "forecast": "skills/analysis/pattern-forecast.md",
    "value-radar": "skills/analysis/value-radar.md",
    "business-inflection": "skills/analysis/business-inflection.md",
    "catalyst-scan": "skills/analysis/catalyst-scan.md",
    "risk-committee": "skills/decision/risk-committee.md",
    "sufficiency": "skills/decision/sufficiency-gate.md",
    "mentor": "skills/playbook/mentor-method.md",
}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "svg"): self.skip += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg") and self.skip: self.skip -= 1
        if not self.skip and tag in ("p", "li", "h1", "h2", "h3", "tr", "div"): self.parts.append("\n")
    def handle_data(self, data):
        if not self.skip: self.parts.append(data)


def _clean_markdown(text):
    text = re.split(r"^<!--\s*lang:zh\s*-->\s*$", text, maxsplit=1, flags=re.M | re.I)[0]
    text = re.sub(r"!\[[^]]*\]\([^)]+\)", "", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _html_text(path):
    raw = open(path, encoding="utf-8", errors="ignore").read()
    english = re.search(r"<div class=['\"]lang lang-en['\"][^>]*>(.*?)<div class=['\"]lang lang-zh['\"]",
                        raw, re.S)
    parser = _Text(); parser.feed(english.group(1) if english else raw)
    text = html.unescape("".join(parser.parts))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", text)).strip()


def _known_symbols():
    """Build the symbol universe from structured desk-owned sources."""
    symbols = set()
    for filename, field in (("decisions.jsonl", "symbol"), ("insights.jsonl", "ticker"),
                            ("action-levels.jsonl", "ticker")):
        for row in load_jsonl(os.path.join(JOURNAL, filename)):
            value = str(row.get(field) or "").upper()
            if SYMBOL_RE.fullmatch(value): symbols.add(value)
    # Chart and market-data filenames are authoritative because their symbols
    # were explicit CLI inputs, not inferred from prose.
    dated = re.compile(r"^(.+?)-(\d{4}-\d{2}-\d{2})(?:-|\.)")
    for base in (os.path.join(REPORTS, "assets", "charts"),
                 os.path.join(REPORTS, "cache", "market-data")):
        for _, _, files in os.walk(base):
            for name in files:
                match = dated.match(name)
                value = match.group(1).upper() if match else ""
                if SYMBOL_RE.fullmatch(value): symbols.add(value)
    return symbols


def _extract_tickers(text, raw=""):
    """Extract explicit report subjects, then retain referenced known symbols."""
    found = set()
    known = _known_symbols()
    explicit = (
        # Markdown/converted heading: "### META — Accumulate"
        re.compile(r"(?:^|\n)\s*#{0,4}\s*\$?([A-Z][A-Z0-9.-]{0,9})\s+(?:—|–|-)", re.M),
        # Decision prose: "BUY META", "WATCH: NKE", etc.
        re.compile(r"\b(?:BUY|SELL|HOLD|TRIM|AVOID|WATCH|ACCUMULATE|EXIT|VETO)\s*[:·-]?\s*\$?([A-Z][A-Z0-9.-]{0,9})\b"),
        # Image source names preserve the chart command's explicit symbol.
        re.compile(r"(?:charts/|charts\\)([A-Z][A-Z0-9.-]{0,9})-\d{4}-\d{2}-\d{2}-"),
    )
    for regex in explicit:
        found.update(regex.findall(text + "\n" + raw))
    for symbol in known:
        if re.search(r"(?<![A-Z0-9.-])\$?" + re.escape(symbol) + r"(?![A-Z0-9.-])", text):
            found.add(symbol)
    # Even action phrases can contain uppercase English ("SELL ALL", "BUY THE
    # DIP"). Requiring membership in desk-owned structured sources removes that
    # ambiguity without a hardcoded vocabulary blacklist.
    return sorted(s for s in found if s in known)


def _record(source_path, html_path, text=None):
    name = os.path.basename(html_path)
    match = REPORT_RE.match(name)
    if not match: return None
    raw = ""
    if source_path and source_path.endswith(".md"):
        raw = open(source_path, encoding="utf-8").read()
    if text is None:
        text = _clean_markdown(raw) if raw else _html_text(html_path)
    methods = [m for m in METHOD_FILES if re.search(re.escape(m).replace(r"\-", "[- ]"), text, re.I)]
    tickers = _extract_tickers(text, raw)
    return {"id": os.path.splitext(name)[0], "date": match.group(1), "title": match.group(2),
            "model": match.group(3), "html": os.path.relpath(html_path, ROOT),
            "tickers": tickers, "methods": methods, "content": text[:24000]}


def _save_record(rec):
    rows = [r for r in load_jsonl(MEMORY) if r.get("id") != rec["id"]]
    rows.append(rec); rows.sort(key=lambda r: (r.get("date", ""), r.get("id", "")))
    tmp = MEMORY + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for row in rows: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.replace(tmp, MEMORY)


def index_report(source_path, html_path, english_markdown=None):
    rec = _record(source_path, os.path.abspath(html_path),
                  _clean_markdown(english_markdown) if english_markdown else None)
    if rec: _save_record(rec)
    return rec


def rebuild():
    markdown = {}
    build = os.path.join(REPORTS, ".build")
    for folder, _, files in os.walk(build):
        for name in files:
            if name.endswith(".md"): markdown[os.path.splitext(name)[0]] = os.path.join(folder, name)
    rows = []
    for folder, dirs, files in os.walk(REPORTS):
        dirs[:] = [d for d in dirs if d not in ("assets", "cache", "examples") and not d.startswith(".")]
        for name in files:
            if not REPORT_RE.match(name) or not name.endswith(".html"): continue
            html_path = os.path.join(folder, name); stem = os.path.splitext(name)[0]
            rows.append(_record(markdown.get(stem), html_path))
    rows = [r for r in rows if r]; rows.sort(key=lambda r: (r["date"], r["id"]))
    with open(MEMORY, "w", encoding="utf-8") as f:
        for row in rows: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return rows


def context(symbol=None, setup=None, query=None, limit=5, max_chars=18000):
    if not os.path.exists(MEMORY):
        rebuild()
    symbol = symbol.upper() if symbol else None
    needles = [x.lower() for x in (symbol, setup, query) if x]
    def matches(row):
        blob = json.dumps(row, ensure_ascii=False).lower()
        return all(n in blob for n in needles) if needles else True
    decisions = [r for r in load_jsonl(os.path.join(JOURNAL, "decisions.jsonl")) if matches(r)]
    insights = [r for r in load_jsonl(os.path.join(JOURNAL, "insights.jsonl")) if matches(r)]
    levels = [r for r in load_jsonl(os.path.join(JOURNAL, "action-levels.jsonl")) if matches(r)]
    reports = []
    for r in load_jsonl(MEMORY):
        score = (100 if symbol and symbol in r.get("tickers", []) else 0) + sum(
            20 for n in needles if n in (r.get("content") or "").lower())
        if not needles or score: reports.append((score, r))
    reports = [r for _, r in sorted(reports, key=lambda x: (x[0], x[1].get("date", "")), reverse=True)[:limit]]
    methods = sorted({m for r in reports for m in r.get("methods", [])})
    if setup:
        methods.extend(m for m in METHOD_FILES if m in setup.lower())
    try:
        from mentor_history import context as mentor_context
        mentor = mentor_context(symbol)
    except Exception as e:
        mentor = {"error": str(e)}
    pack = {"query": {"symbol": symbol, "setup": setup, "text": query},
            "decisions": decisions[-limit:], "insights": insights[-limit:], "action_levels": levels[-limit:],
            "mentor_history": mentor,
            "reports": [{**r, "content": r.get("content", "")[:max(1000, max_chars // max(1, len(reports)))]}
                        for r in reports],
            "methodology_refs": sorted({METHOD_FILES[m] for m in methods if m in METHOD_FILES})}
    return pack


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("rebuild", help="re-index all report HTML/markdown")
    q = sub.add_parser("context", help="retrieve compact pre-analysis memory")
    q.add_argument("--symbol"); q.add_argument("--setup"); q.add_argument("--query")
    q.add_argument("--limit", type=int, default=5); q.add_argument("--max-chars", type=int, default=18000)
    args = ap.parse_args(argv)
    if args.cmd == "rebuild":
        rows = rebuild(); print(f"Indexed {len(rows)} reports into {os.path.relpath(MEMORY, ROOT)}"); return 0
    print(json.dumps(context(args.symbol, args.setup, args.query, args.limit, args.max_chars),
                     indent=2, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
