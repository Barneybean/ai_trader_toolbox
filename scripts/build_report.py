#!/usr/bin/env python3
"""
Render a desk report from markdown into a **self-contained, styled HTML file**.

Why: markdown is the natural way to *write* the analysis, but a browser page is
far easier to *read* — cards per recommendation, styled tables, colour-coded
badges, and the charts sitting inline next to the thesis. This tool keeps the
markdown as the editable source and produces a polished HTML twin.

Key property: it **inlines** any `![alt](charts/NAME.svg)` image whose SVG file
exists, so the output is one portable file (no broken image links on GitHub, in
email, or when saved to disk). Images it can't find are left as normal `<img>`.

Pure standard library — a compact markdown-subset converter (headings, lists,
pipe tables, blockquotes, rules, bold/italic/code, links, images). It is tuned
for the desk report scaffold in SKILL.md, not arbitrary markdown.

Usage:
    python3 scripts/build_report.py reports/Trading-Desk-Report-2026-07-03.md
    python3 scripts/build_report.py <in.md> --out <out.html>
    python3 scripts/build_report.py <in.md> --charts-dir reports/charts
"""

import argparse
import html
import os
import re
import sys


# --------------------------------------------------------------------------- #
# Inline formatting
# --------------------------------------------------------------------------- #

_CODE_RE = re.compile(r"`([^`]+)`")
_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
# italic only at word boundaries so snake_case / file_names survive
_ITAL_A = re.compile(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])")
_ITAL_U = re.compile(r"(?<![\w_])_(?=\S)(.+?)(?<=\S)_(?![\w_])")


def _inline(text, base_dir, charts_dir):
    """Convert inline markdown to HTML. Code spans are protected first so their
    contents aren't re-formatted; images are handled by the block layer, but any
    stray inline image is rendered as a plain <img>."""
    codes = []

    def _stash(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    text = _CODE_RE.sub(_stash, text)
    text = html.escape(text, quote=False)
    text = _BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = _ITAL_A.sub(r"<em>\1</em>", text)
    text = _ITAL_U.sub(r"<em>\1</em>", text)
    text = _LINK_RE.sub(r"<a href='\2' target='_blank' rel='noopener'>\1</a>", text)

    def _unstash(m):
        return f"<code>{html.escape(codes[int(m.group(1))], quote=False)}</code>"

    return re.sub(r"\x00(\d+)\x00", _unstash, text)


def _svg_inline(src, base_dir, charts_dir):
    """Return the raw SVG markup for `src` if the file exists, else None."""
    for cand in (os.path.join(base_dir, src),
                 os.path.join(charts_dir, os.path.basename(src)) if charts_dir else None):
        if cand and os.path.isfile(cand):
            with open(cand) as f:
                svg = f.read()
            # strip any xml/doctype prolog; keep from the first <svg
            i = svg.find("<svg")
            return svg[i:] if i >= 0 else svg
    return None


def _render_images(line, base_dir, charts_dir):
    """A line that is only image(s) → a figure row (charts side by side). Inlines
    SVGs when possible. Returns HTML, or None if the line isn't image-only."""
    imgs = _IMG_RE.findall(line)
    if not imgs or _IMG_RE.sub("", line).strip():
        return None
    figs = []
    for alt, src in imgs:
        svg = _svg_inline(src, base_dir, charts_dir) if src.endswith(".svg") else None
        if svg:
            figs.append(f"<figure class='chart'>{svg}</figure>")
        else:
            figs.append(f"<figure class='chart'>"
                        f"<img src='{html.escape(src)}' alt='{html.escape(alt)}'></figure>")
    cls = "charts-row" if len(figs) > 1 else "charts-one"
    return f"<div class='{cls}'>{''.join(figs)}</div>"


# --------------------------------------------------------------------------- #
# Block parsing
# --------------------------------------------------------------------------- #

def _card_accent(heading):
    """Colour-code a recommendation card by the action in its heading — the way a
    desk blotter tags a line: green=add, red=avoid/trim, amber=watch/hold."""
    h = heading.lower()
    if any(k in h for k in ("avoid", "trim", "sell", "pass", "did not clear", "reduce")):
        return "card-neg"
    if any(k in h for k in ("buy", "accumulate", "add", "starter", "long", "overweight")):
        return "card-pos"
    if any(k in h for k in ("watch", "hold", "neutral", "monitor")):
        return "card-warn"
    return "card-neu"


_CALLOUTS = {
    "ACTION":  ("callout-action",  "▶ Action"),
    "TIP":     ("callout-tip",     "💡 In plain English"),
    "PLAIN":   ("callout-tip",     "💡 In plain English"),
    "WATCH":   ("callout-note",    "◔ Watch / wait"),
    "WARNING": ("callout-warning", "⚠ Risk"),
    "RISK":    ("callout-warning", "⚠ What kills it"),
    "NOTE":    ("callout-note",    "ℹ Note"),
}


def _callout(kind, body, base_dir, charts_dir):
    cls, label = _CALLOUTS.get(kind.upper(), ("callout-note", kind.title()))
    return (f"<div class='callout {cls}'><span class='callout-label'>{label}</span>"
            f"{_inline(body, base_dir, charts_dir)}</div>")


# Plain-English definitions for jargon — the builder auto-links the FIRST occurrence of
# each term to a hover tooltip so non-financial readers can decode the desk's shorthand.
GLOSSARY = {
    "variant perception": "The desk's non-consensus view — what we think the market has wrong and why it isn't priced in yet.",
    "chip distribution": "A map of the prices where today's holders actually bought — shows where big money accumulated and where sellers are stuck underwater.",
    "cost basis": "The price a holder originally paid. Clusters of it act as support (buyers defend it) or resistance (trapped sellers exit there).",
    "chip wash": "A deliberate shakeout — pushing price down to scare weak holders into selling before a move up. (Chinese: 洗盘.)",
    "accumulation": "Big money quietly buying over time, usually while price looks flat or weak.",
    "distribution": "Big money quietly selling into strength — the opposite of accumulation; a warning sign.",
    "resistance": "A price ceiling where sellers have repeatedly capped the stock.",
    "support": "A price floor where buyers have repeatedly stepped in.",
    "reward:risk": "Dollars you aim to make for each dollar risked. The desk only takes trades with about 2:1 or better.",
    "risk:reward": "Dollars you aim to make for each dollar risked. The desk wants about 2:1 or better.",
    "stop": "A pre-set exit price that caps your loss if the trade goes against you.",
    "200-dma": "The average closing price over the last 200 days — a common dividing line between a long-term up- and down-trend.",
    "sma200": "200-day average price — the long-term trend line.",
    "sma50": "50-day average price — the medium-term trend line.",
    "sma20": "20-day average price — the short-term trend line.",
    "rsi": "Momentum gauge from 0–100. Above 70 = overbought (may pull back); below 30 = oversold (may bounce).",
    "macd": "A trend-momentum indicator; a 'bullish cross' means upward momentum is starting to build.",
    "atr": "Average daily dollar swing of the stock — used to set stops that respect its real volatility instead of a round number.",
    "adx": "Trend-strength gauge. Above 25 = a real trend is in force; below 20 = choppy/sideways.",
    "obv": "On-Balance Volume — running total of volume that adds on up-days and subtracts on down-days. Rising = buyers in control.",
    "bollinger": "Volatility bands drawn around price; tagging the outer band means the move is stretched.",
    "stochastic": "A 0–100 gauge of where price sits in its recent range. >80 overbought, <20 oversold.",
    "float": "The number of shares actually available to trade in the open market.",
    "starter": "A deliberately small first position, sized so you can add later if the thesis confirms.",
    "conviction": "How strongly the desk believes the idea — sizing scales with it.",
}
# longest terms first so multi-word phrases win over their sub-words
_GLOSSARY_ORDER = sorted(GLOSSARY.items(), key=lambda kv: -len(kv[0]))
_GLOSSARY_SKIP = {"code", "a", "abbr", "svg", "h1", "h2", "h3", "h4", "title", "style"}


def _inject_glossary(body):
    """Wrap the first occurrence of each glossary term in an <abbr> tooltip, skipping
    text inside code/links/headings and — importantly — inside inlined <svg> charts
    (whose axis labels contain words like 'support'/'resistance')."""
    used = set()
    suppress = 0
    out = []
    for tok in re.split(r"(<[^>]+>)", body):
        if tok.startswith("<") and tok.endswith(">"):
            mm = re.match(r"</?\s*([a-zA-Z0-9]+)", tok)
            nm = mm.group(1).lower() if mm else ""
            if nm in _GLOSSARY_SKIP and not tok.endswith("/>"):
                suppress = max(0, suppress - 1) if tok.startswith("</") else suppress + 1
            out.append(tok)
            continue
        if suppress or not tok.strip():
            out.append(tok)
            continue
        for term, definition in _GLOSSARY_ORDER:
            if term in used:
                continue
            m = re.search(r"(?<![\w-])(" + re.escape(term) + r")(?![\w-])", tok, re.I)
            if m:
                used.add(term)
                tip = html.escape(definition, quote=True)
                tok = (tok[:m.start()] + f"<abbr class='gl' title='{tip}'>"
                       + m.group(1) + "</abbr>" + tok[m.end():])
        out.append(tok)
    return "".join(out)


def _is_table_sep(s):
    return bool(re.match(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$", s))


def _split_row(s):
    s = s.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def markdown_to_html(md, base_dir, charts_dir):
    lines = md.replace("\r\n", "\n").split("\n")
    out = []
    i = 0
    open_card = False
    para = []
    list_stack = []   # list of ('ul'|'ol', indent)
    seen_h1 = [False]
    meta_used = [False]

    def close_para():
        if para:
            # the first paragraph after the H1 title is the run's dateline/meta
            cls = ""
            if seen_h1[0] and not meta_used[0]:
                cls = " class='meta'"
                meta_used[0] = True
            out.append(f"<p{cls}>{_inline(' '.join(para), base_dir, charts_dir)}</p>")
            para.clear()

    def close_lists(to_indent=-1):
        while list_stack and list_stack[-1][1] > to_indent:
            tag, _ = list_stack.pop()
            out.append(f"</{tag}>")

    def close_card():
        nonlocal open_card
        close_para()
        close_lists()
        if open_card:
            out.append("</section>")
            open_card = False

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        if not line:
            close_para()
            close_lists()
            i += 1
            continue

        # headings
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            text = m.group(2)
            if level <= 2:
                close_card()
                tag = "h1" if level == 1 else "h2"
                if level == 1:
                    seen_h1[0] = True
                out.append(f"<{tag}>{_inline(text, base_dir, charts_dir)}</{tag}>")
            else:  # h3 / h4 open a recommendation card
                close_card()
                out.append(f"<section class='card {_card_accent(text)}'>")
                open_card = True
                out.append(f"<h3>{_inline(text, base_dir, charts_dir)}</h3>")
            i += 1
            continue

        # horizontal rule
        if re.match(r"^(\*\s*){3,}$", line) or re.match(r"^(-\s*){3,}$", line) or line == "---":
            close_para(); close_lists()
            out.append("<hr>")
            i += 1
            continue

        # image-only line (charts)
        img_html = _render_images(line, base_dir, charts_dir)
        if img_html:
            close_para(); close_lists()
            out.append(img_html)
            i += 1
            continue

        # tables
        if "|" in line and i + 1 < len(lines) and _is_table_sep(lines[i + 1]):
            close_para(); close_lists()
            header = _split_row(line)
            i += 2
            body = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                body.append(_split_row(lines[i]))
                i += 1
            th = "".join(f"<th>{_inline(c, base_dir, charts_dir)}</th>" for c in header)
            rows = ""
            for r in body:
                tds = "".join(f"<td>{_inline(c, base_dir, charts_dir)}</td>" for c in r)
                rows += f"<tr>{tds}</tr>"
            out.append(f"<div class='table-wrap'><table><thead><tr>{th}</tr></thead>"
                       f"<tbody>{rows}</tbody></table></div>")
            continue

        # blockquote / callout ( > [!ACTION] ... )
        if line.startswith(">"):
            close_para(); close_lists()
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            text = " ".join(x for x in buf if x)
            cm = re.match(r"\[!(\w+)\]\s*(.*)$", text, re.S)
            if cm:
                out.append(_callout(cm.group(1), cm.group(2), base_dir, charts_dir))
            else:
                out.append(f"<blockquote>{_inline(text, base_dir, charts_dir)}</blockquote>")
            continue

        # list items (ul: -,* ; ol: 1.)
        lm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", raw)
        if lm:
            close_para()
            indent = len(lm.group(1))
            kind = "ol" if lm.group(2)[0].isdigit() else "ul"
            if not list_stack or indent > list_stack[-1][1]:
                out.append(f"<{kind}>")
                list_stack.append((kind, indent))
            else:
                close_lists(indent)
                if not list_stack or list_stack[-1][1] < indent:
                    out.append(f"<{kind}>")
                    list_stack.append((kind, indent))
            out.append(f"<li>{_inline(lm.group(3), base_dir, charts_dir)}</li>")
            i += 1
            continue

        # paragraph text
        close_lists()
        para.append(line)
        i += 1

    close_card()
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Page shell
# --------------------------------------------------------------------------- #

CSS = """
:root{color-scheme:dark;}
*{box-sizing:border-box;}
body{margin:0;background:#0a0d12;color:#c9d1d9;
  font-family:ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  line-height:1.6;font-size:15px;}
.wrap{max-width:1040px;margin:0 auto;padding:0 22px 80px;}
body::before{content:"";display:block;height:3px;
  background:linear-gradient(90deg,#26a69a,#58a6ff 55%,#bc8cff);}
.wrap>h1:first-child{margin-top:34px;}
h1{font-size:27px;line-height:1.22;margin:.2em 0 .35em;color:#f0f3f6;letter-spacing:-.01em;
  font-weight:720;}
h2{font-size:19px;margin:2.2em 0 .6em;padding-bottom:.3em;border-bottom:1px solid #222b36;color:#e6edf3;}
h3{font-size:16px;margin:0 0 .5em;color:#f0f3f6;}
h4{font-size:14px;margin:1.2em 0 .4em;color:#e6edf3;}
p{margin:.6em 0;}
p.meta{color:#8b949e;font-size:13.5px;margin:0 0 1.4em;padding-bottom:1.2em;
  border-bottom:1px solid #1b2129;line-height:1.55;}
p.meta em{font-style:normal;}
a{color:#58a6ff;text-decoration:none;}a:hover{text-decoration:underline;}
strong{color:#e6edf3;font-weight:650;}
code{background:#161b22;border:1px solid #222b36;border-radius:5px;padding:.08em .38em;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.86em;color:#e6edf3;}
hr{border:none;border-top:1px solid #222b36;margin:2em 0;}
ul,ol{margin:.5em 0 .9em;padding-left:1.3em;}
li{margin:.28em 0;}
blockquote{margin:1em 0;padding:.5em 1em;border-left:3px solid #30363d;
  color:#8b949e;background:#0e131a;border-radius:0 6px 6px 0;font-size:.95em;}
.card{background:#0e131a;border:1px solid #1f2731;border-radius:12px;
  padding:18px 20px;margin:16px 0;box-shadow:0 1px 0 #05070a;}
.card h3{border-left:3px solid #58a6ff;padding-left:10px;margin-left:-10px;}
.card ul{padding-left:1.15em;}
.card li{margin:.4em 0;}
.card-pos{border-color:#193b34;} .card-pos h3{border-left-color:#26a69a;}
.card-neg{border-color:#3b1f22;} .card-neg h3{border-left-color:#ef5350;}
.card-warn{border-color:#3a3115;} .card-warn h3{border-left-color:#f0b90b;}
.card-neu h3{border-left-color:#58a6ff;}
.table-wrap{overflow-x:auto;margin:1em 0;}
table{border-collapse:collapse;width:100%;font-size:.92em;}
th,td{border:1px solid #222b36;padding:7px 10px;text-align:left;vertical-align:top;}
th{background:#161b22;color:#e6edf3;font-weight:600;}
tr:nth-child(even) td{background:#0e131a;}
.charts-row{display:flex;flex-wrap:wrap;gap:14px;margin:16px 0;align-items:flex-start;}
.charts-row .chart{flex:1 1 300px;min-width:0;}
.charts-one{margin:16px 0;}
figure.chart{margin:0;background:#0d1117;border:1px solid #1f2731;border-radius:10px;
  padding:8px;overflow:hidden;}
figure.chart svg,figure.chart img{width:100%;height:auto;display:block;border-radius:6px;}
.meta{color:#8b949e;font-size:13px;margin-top:-.3em;}
.footer{margin-top:48px;padding-top:16px;border-top:1px solid #222b36;
  color:#6e7681;font-size:12px;}
/* jargon tooltips */
abbr.gl{text-decoration:underline dotted #6e7681;text-underline-offset:3px;cursor:help;
  border:0;}
/* callout boxes */
.callout{border:1px solid;border-radius:9px;padding:11px 14px;margin:14px 0;font-size:.95em;}
.callout-label{display:block;font-weight:700;font-size:.74em;letter-spacing:.04em;
  text-transform:uppercase;margin-bottom:4px;}
.callout p{margin:.3em 0;}
.callout-action{background:#0f2620;border-color:#1f6f52;}
.callout-action .callout-label{color:#3fd39a;}
.callout-action strong{color:#eafff6;}
.callout-tip{background:#0d2030;border-color:#1c527d;}
.callout-tip .callout-label{color:#6cb2ff;}
.callout-warning{background:#241417;border-color:#7d2b30;}
.callout-warning .callout-label{color:#ff6b6b;}
.callout-note{background:#141a21;border-color:#2b333d;}
.callout-note .callout-label{color:#8b949e;}
"""


def wrap_page(title, body):
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head><body><div class="wrap">
{body}
<div class="footer">Generated by the trading-desk skill · charts from
<code>scripts/indicators.py</code> + <code>scripts/charts.py</code> · informational only, not financial advice.</div>
</div></body></html>
"""


def _title_from(md, fallback):
    m = re.search(r"^#\s+(.*)$", md, re.M)
    return m.group(1).strip() if m else fallback


def build(md_path, out_path=None, charts_dir=None):
    with open(md_path) as f:
        md = f.read()
    base_dir = os.path.dirname(os.path.abspath(md_path))
    if charts_dir is None:
        charts_dir = os.path.join(base_dir, "charts")
    body = markdown_to_html(md, base_dir, charts_dir)
    body = _inject_glossary(body)
    title = _title_from(md, os.path.basename(md_path))
    page = wrap_page(title, body)
    if out_path is None:
        out_path = os.path.splitext(md_path)[0] + ".html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)
    return out_path


def main():
    p = argparse.ArgumentParser(description="Render a markdown desk report to styled, self-contained HTML.")
    p.add_argument("markdown", help="the report .md file")
    p.add_argument("--out", default=None, help="output .html path (default: alongside the .md)")
    p.add_argument("--charts-dir", default=None,
                   help="dir to resolve chart images from (default: <report_dir>/charts)")
    args = p.parse_args()
    if not os.path.isfile(args.markdown):
        sys.stderr.write(f"no such file: {args.markdown}\n")
        sys.exit(1)
    out = build(args.markdown, args.out, args.charts_dir)
    print(out)


if __name__ == "__main__":
    main()
