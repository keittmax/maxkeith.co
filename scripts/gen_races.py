#!/usr/bin/env python3
"""
Generate pages/races/index.html from activities.csv.
Run from the repo root:  python3 scripts/gen_races.py
"""

import pandas as pd
from pathlib import Path
from collections import defaultdict

CSV = Path.home() / "training" / "activities.csv"
OUT = Path(__file__).parent.parent / "pages" / "races" / "index.html"

df = pd.read_csv(CSV, dayfirst=True, parse_dates=["Date"])
races = df[df["Session Purpose"].isin(["Race", "Test"])].copy()
races = races.sort_values("Date", ascending=False)

# Group by year
by_year = defaultdict(list)
for _, r in races.iterrows():
    by_year[r["Date"].year].append(r)

def fmt_dist(v):
    try: return f"{float(v):.1f}"
    except: return "—"

def fmt_elev(v):
    try: return f"{int(float(v)):,}"
    except: return "—"

rows_html = ""
for year in sorted(by_year.keys(), reverse=True):
    rows_html += f'<tr class="year-row"><td colspan="4">{year}</td></tr>\n'
    for r in by_year[year]:
        date   = r["Date"].strftime("%m/%d")
        is_tt  = r["Session Purpose"] == "Test"
        title  = str(r["Title"]) if pd.notna(r["Title"]) else "—"
        dist   = fmt_dist(r["Distance (km)"])
        elev   = fmt_elev(r["Elevation Gain"])
        tt_tag = '<span class="tt-tag">TT</span>' if is_tt else ""
        cls    = ' class="tt-row"' if is_tt else ""
        rows_html += f"""<tr{cls}>
  <td class="col-date">{date}</td>
  <td class="col-name">{tt_tag}{title}</td>
  <td class="col-dist">{dist} km</td>
  <td class="col-elev">↑ {elev}</td>
</tr>\n"""

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>races &amp; tt — max keith</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{
  --bg:    #e1cdcb;
  --ink:   #718858;
  --dim:   #91a07a;
  --faint: #d0bcba;
  --font:  'IBM Plex Mono', 'Courier New', Courier, monospace;
}}
html {{ font-size: 15px; }}
body {{
  background: var(--bg);
  color: var(--ink);
  font-family: var(--font);
  min-height: 100vh;
  padding: 0 24px;
}}
a {{ color: var(--ink); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

/* ── Header / nav ── */
.site {{ max-width: 700px; margin: 0 auto; padding: 40px 0 80px; }}
.site-header {{
  display: flex; align-items: baseline; justify-content: space-between;
  flex-wrap: wrap; gap: 12px; margin-bottom: 52px; position: relative;
}}
.site-logo {{ font-size: 14px; font-weight: 600; letter-spacing: .03em; }}
.site-nav {{ display: flex; flex-wrap: wrap; gap: 4px 20px; justify-content: flex-end; }}
.site-nav a {{ font-size: 13px; opacity: 0.6; white-space: nowrap; }}
.site-nav a:hover {{ opacity: 1; text-decoration: none; }}
.burger {{
  display: none; background: none; border: none; cursor: pointer;
  font: inherit; color: var(--ink); font-size: 13px; padding: 0;
}}

/* ── Page heading ── */
.page-heading {{
  font-size: 11px; font-weight: 600; letter-spacing: .12em;
  text-transform: uppercase; opacity: 0.45; margin-bottom: 28px;
}}

/* ── Table ── */
table {{
  width: 100%; border-collapse: collapse; font-size: 13px; line-height: 1.5;
}}
tr {{ border-bottom: 1px solid var(--faint); }}
td {{ padding: 7px 0; vertical-align: middle; }}

.year-row td {{
  padding-top: 28px; padding-bottom: 6px;
  font-size: 11px; font-weight: 600; letter-spacing: .08em;
  opacity: 0.45; border-bottom: 1px solid var(--faint);
}}
.tt-row {{ opacity: 0.55; font-style: italic; }}

.col-date  {{ width: 52px; opacity: 0.6; white-space: nowrap; }}
.col-name  {{ padding-left: 12px; }}
.col-dist  {{ text-align: right; white-space: nowrap; padding-left: 12px; opacity: 0.75; }}
.col-elev  {{ text-align: right; white-space: nowrap; padding-left: 16px; opacity: 0.5; min-width: 72px; }}

.tt-tag {{
  display: inline-block; font-size: 9px; font-weight: 600; letter-spacing: .08em;
  text-transform: uppercase; opacity: 0.6; border: 1px solid currentColor;
  padding: 0 4px; margin-right: 7px; vertical-align: middle; font-style: normal;
  line-height: 1.6; border-radius: 2px;
}}

/* ── Mobile ── */
@media (max-width: 600px) {{
  body {{ padding: 0 16px; }}
  .col-elev {{ display: none; }}
  .site-nav {{
    display: none !important; position: absolute; top: 100%; left: 0; right: 0;
    background: var(--bg); flex-direction: column; gap: 14px;
    padding: 20px 0 4px; z-index: 100;
  }}
  .site-nav.open {{ display: flex !important; }}
  .burger {{ display: block !important; }}
}}
</style>
</head>
<body>
<div class="site">
  <header class="site-header">
    <a href="/" class="site-logo"><strong>max keith</strong></a>
    <button class="burger" onclick="var n=document.querySelector('.site-nav');var o=n.classList.toggle('open');this.textContent=o?'[ close ]':'[ menu ]';">[ menu ]</button>
    <nav class="site-nav">
      <a href="/posts/">posts</a>
      <a href="/archive/">archive</a>
      <a href="/tags/">tags</a>
      <a href="/currently/">currently</a>
      <a href="/stats">stats</a>
      <a href="/about/">about</a>
    </nav>
  </header>

  <p class="page-heading">races &amp; tt</p>

  <table>
    {rows_html}
  </table>
</div>
</body>
</html>
"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT}  ({len(by_year)} years, {sum(len(v) for v in by_year.values())} entries)")
