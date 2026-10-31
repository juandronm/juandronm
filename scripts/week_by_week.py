"""Generate animated "Week by week" contribution SVGs (dark + light) for the profile README.

Usage: GITHUB_TOKEN=... python scripts/week_by_week.py [username]
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

USER = sys.argv[1] if len(sys.argv) > 1 else "juandronm"
OUT = Path(__file__).resolve().parent.parent / "assets"

QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""

THEMES = {
    "dark": dict(text="#e6edf3", muted="#8b949e", grid="#21262d", accent="#00C9A7",
                 levels=["#161b22", "#0b4a42", "#00806b", "#00a88c", "#00C9A7"]),
    "light": dict(text="#1f2328", muted="#656d76", grid="#d0d7de", accent="#00977d",
                  levels=["#ebedf0", "#b3efe3", "#5fdcc4", "#00b393", "#00866f"]),
}
LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

CELL, GAP = 12, 3
STEP = CELL + GAP
LEFT, LINE_TOP, LINE_BOTTOM, GRID_TOP = 40, 78, 170, 186
W = LEFT * 2 + 53 * STEP - GAP  # 53 week columns, equal side margins


def fetch(user):
    token = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("Set GITHUB_TOKEN (or GH_PAT).")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        sys.exit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def fmt(date):
    d = dt.date.fromisoformat(date)
    return f"{d.day} {d.strftime('%b %Y')}"


def render(cal, t):
    weeks = cal["weeks"]
    totals = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks]
    peak_i = max(range(len(totals)), key=totals.__getitem__)
    peak = totals[peak_i] or 1  # avoid /0 on an empty year
    cx = lambda i: LEFT + i * STEP + CELL / 2
    cy = lambda v: LINE_BOTTOM - (v / peak) * (LINE_BOTTOM - LINE_TOP)
    pts = " ".join(f"{cx(i):.1f},{cy(v):.1f}" for i, v in enumerate(totals))
    area = f"{cx(0):.1f},{LINE_BOTTOM} {pts} {cx(len(totals) - 1):.1f},{LINE_BOTTOM}"
    grid_bottom = GRID_TOP + 7 * STEP
    h = grid_bottom + 44

    cells, months, last_month = [], [], None
    for i, w in enumerate(weeks):
        days = w["contributionDays"]
        m = days[-1]["date"][:7]  # label a month at the week that reaches into it, like GitHub
        if m != last_month and i < len(weeks) - 2:
            months.append(f'<text x="{LEFT + i * STEP}" y="{grid_bottom + 14}" class="m">'
                          f'{dt.date.fromisoformat(days[-1]["date"]).strftime("%b")}</text>')
            last_month = m
        for d in days:
            row = dt.date.fromisoformat(d["date"]).isoweekday() % 7  # Sunday = row 0
            delay = 1.4 + i * 0.025 + row * 0.03  # line draws first, then columns pour left to right
            cells.append(
                f'<rect x="{LEFT + i * STEP}" y="{GRID_TOP + row * STEP}" width="{CELL}" height="{CELL}" rx="2.5" '
                f'fill="{t["levels"][LEVEL[d["contributionLevel"]]]}" style="animation-delay:{delay:.3f}s">'
                f'<title>{d["contributionCount"]} on {d["date"]}</title></rect>')

    px, py = cx(peak_i), cy(totals[peak_i])
    anchor = "end" if peak_i > len(totals) * 0.7 else "start"
    lx = px - 8 if anchor == "end" else px + 8
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">
<style>
.t{{fill:{t['text']};font-size:15px;font-weight:600}} .s,.m,.l{{fill:{t['muted']};font-size:11px}}
.line{{fill:none;stroke:{t['accent']};stroke-width:2;stroke-linejoin:round;stroke-dasharray:1;stroke-dashoffset:1;animation:draw 1.4s ease-out forwards}}
.area{{fill:url(#g);opacity:0;animation:fade .8s ease-out 1s forwards}}
.peak{{opacity:0;animation:fade .5s ease-out 1.3s forwards}}
.cells rect{{animation:pour .45s cubic-bezier(.2,.8,.3,1.2) both}}
@keyframes draw{{to{{stroke-dashoffset:0}}}}
@keyframes fade{{to{{opacity:1}}}}
@keyframes pour{{from{{opacity:0;transform:translateY(-36px)}}to{{opacity:1;transform:none}}}}
@media (prefers-reduced-motion:reduce){{.line{{stroke-dashoffset:0}} .area,.peak{{opacity:1}} *{{animation:none!important}}}}
</style>
<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t['accent']}" stop-opacity=".28"/><stop offset="1" stop-color="{t['accent']}" stop-opacity="0"/></linearGradient></defs>
<text x="{LEFT}" y="28" class="t">Week by week</text>
<text x="{LEFT}" y="48" class="s">{cal['totalContributions']} contributions in the last year · biggest week {totals[peak_i]}, from {fmt(weeks[peak_i]['contributionDays'][0]['date'])}</text>
<line x1="{LEFT}" y1="{LINE_BOTTOM}" x2="{LEFT + len(weeks) * STEP - GAP}" y2="{LINE_BOTTOM}" stroke="{t['grid']}" stroke-dasharray="2 3"/>
<polygon class="area" points="{area}"/>
<polyline class="line" pathLength="1" points="{pts}"/>
<g class="peak"><circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{t['accent']}"/><text x="{lx:.1f}" y="{py + 4:.1f}" text-anchor="{anchor}" class="l">{totals[peak_i]}</text></g>
<g class="cells">{''.join(cells)}</g>
{''.join(months)}
<text x="{W - 40}" y="{grid_bottom + 34}" text-anchor="end" class="l">less {''.join(f'<tspan fill="{c}">■</tspan>' for c in t['levels'])} more</text>
</svg>
""", totals, peak_i


def main():
    cal = fetch(USER)
    OUT.mkdir(exist_ok=True)
    for name, theme in THEMES.items():
        svg, totals, peak_i = render(cal, theme)
        # self-check: one column per week, peak really is the max, every week has a point
        assert len(totals) == len(cal["weeks"]) and 52 <= len(totals) <= 54
        assert all(totals[peak_i] >= v for v in totals)
        assert svg.count("<rect") == sum(len(w["contributionDays"]) for w in cal["weeks"])
        (OUT / f"week-by-week-{name}.svg").write_text(svg, encoding="utf-8")
    print(f"wrote {len(THEMES)} SVGs, {len(totals)} weeks, peak {totals[peak_i]}")


if __name__ == "__main__":
    main()
