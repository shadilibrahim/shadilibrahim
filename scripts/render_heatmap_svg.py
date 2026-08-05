"""
render_heatmap_svg.py
~~~~~~~~~~~~~~~~~~~~~
Reads contributions.json (produced by fetch_contributions.py) and
regenerates contrib-heatmap.svg using the same animated neon-box style
that was hand-crafted in the original static SVG.

Behaviour mirrors the original file exactly:
  - 888 × 158 canvas
  - 13 × 13 px cells, 2 px gap → 15 px column stride
  - rows: Sun=0 … Sat=6, but only Mon/Wed/Fri labels shown
  - pop + flash CSS animations with staggered animation-delay
  - month label row at y=16
  - total contribution count footer at y=152
"""

from __future__ import annotations

import json
import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# ── constants ────────────────────────────────────────────────────────────────

CELL   = 13          # cell width & height in px
GAP    = 2           # gap between cells
STRIDE = CELL + GAP  # = 15 px per column / row

CANVAS_W = 888
CANVAS_H = 158

# Left margin (px) where the first column of cells begins
X0 = 34
# Top margin (px) where the first row of cells begins
Y0 = 24

# Day-of-week row labels (only Mon / Wed / Fri are drawn, matching the original)
DOW_LABELS = {1: ("Mon", 51), 3: ("Wed", 83), 5: ("Fri", 115)}

COLOURS = {
    0: "#161b22",
    1: "#0e4429",
    2: "#006d32",
    3: "#26a641",
    4: "#39d353",
}

MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

# Pop + flash animation parameters (match the original exactly)
ANIM_PER_CELL = 0.036   # seconds added per cell index for stagger

CSS = """\
  text.lbl { fill:#7d8590; font-size:13px; font-weight:600; }
  text.total { fill:#e6edf3; font-size:15px; font-weight:700; }
  .c { transform-box:fill-box; transform-origin:center; opacity:0; animation:pop 0.55s ease-out both; }
  .g { animation:pop 0.55s ease-out both, flash 0.7s ease-out both; }
  @keyframes pop { 0%{opacity:0;transform:scale(.2)} 60%{opacity:1;transform:scale(1.1)} 100%{opacity:1;transform:scale(1)} }
  @keyframes flash { 0%{filter:brightness(2.4)} 45%{filter:brightness(2.4)} 100%{filter:brightness(1)} }
  @media (prefers-reduced-motion: reduce) { .c { opacity:1 !important; animation:none !important; } }\
"""

# ── helpers ───────────────────────────────────────────────────────────────────

def _round(v: float, digits: int = 3) -> str:
    """Format float, stripping trailing zeros."""
    return f"{round(v, digits):g}"


def _attr(key: str, val) -> str:
    return f'{key}="{val}"'


def rect_tag(x: int, y: int, colour: str, delay: float, has_contribution: bool) -> str:
    cls  = "c g" if has_contribution else "c e"
    fill = colour
    d    = _round(delay)
    return (
        f'<rect class="{cls}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
        f'rx="2.5" fill="{fill}" style="animation-delay:{d}s"/>'
    )


def text_tag(cls: str, x: int, y: int, content: str) -> str:
    return f'<text class="{cls}" x="{x}" y="{y}">{content}</text>'


# ── core renderer ─────────────────────────────────────────────────────────────

def build_svg(data: dict) -> str:
    days: list[dict] = data["days"]
    total: int       = data["total_contributions"]

    # Build a lookup {date_str → day_dict}
    by_date: dict[str, dict] = {d["date"]: d for d in days}

    # Determine the date window: last 52 full weeks + partial current week,
    # anchored so that today is in the last column.
    today = date.today()
    # end on Saturday of current week (or today if earlier)
    days_since_sat = (today.weekday() + 2) % 7   # Mon=0 … Sun=6 → offset to Sat
    end_date = today + timedelta(days=(6 - (today.weekday() + 1) % 7))
    # Snap to 52 weeks back from end_date's Sunday
    end_dow = end_date.weekday()   # 0=Mon … 6=Sun
    # We want end_date to be a Saturday (weekday==5)
    end_date = today + timedelta(days=(5 - today.weekday()) % 7)
    start_date = end_date - timedelta(weeks=52) + timedelta(days=1)
    # Snap start_date back to Sunday
    start_date -= timedelta(days=(start_date.weekday() + 1) % 7)

    # ── organise into columns (each column = one week, Sun … Sat) ───────────
    columns: list[list[date]] = []
    cur = start_date
    while cur <= end_date:
        week = [cur + timedelta(days=i) for i in range(7) if cur + timedelta(days=i) <= end_date]
        columns.append(week)
        cur += timedelta(days=7)

    num_cols = len(columns)

    # ── month label positions ────────────────────────────────────────────────
    # Show a month label when the month changes between consecutive columns.
    month_labels: list[tuple[int, str]] = []   # (x_pixel, label)
    prev_month = None
    for col_i, week in enumerate(columns):
        first_day = week[0]
        m = first_day.month
        if m != prev_month:
            month_labels.append((X0 + col_i * STRIDE, MONTH_NAMES[m - 1]))
            prev_month = m

    # ── SVG output accumulation ──────────────────────────────────────────────
    parts: list[str] = []

    # Header
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{CANVAS_W}" height="{CANVAS_H}" '
        f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" '
        f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">'
    )
    parts.append(f"<style>\n{CSS}\n</style>")
    parts.append(f'<rect width="{CANVAS_W}" height="{CANVAS_H}" fill="none"/>')

    # Month + day-of-week labels (all in one line, like the original)
    label_line = ""
    for x_px, name in month_labels:
        label_line += text_tag("lbl", x_px, 16, name)
    for dow, (name, y_px) in DOW_LABELS.items():
        label_line += text_tag("lbl", 2, y_px, name)
    parts.append(label_line)

    # Cells
    cell_index = 0
    cell_line_parts: list[str] = []

    for col_i, week in enumerate(columns):
        x = X0 + col_i * STRIDE
        for day_date in week:
            # day_of_week: 0=Mon … 6=Sun in Python; GitHub shows Sun at top
            # GitHub uses Sun=row 0, so map: Sun→0, Mon→1 … Sat→6
            dow_gh = (day_date.weekday() + 1) % 7   # Sun=0
            y = Y0 + dow_gh * STRIDE

            date_str = day_date.isoformat()
            info = by_date.get(date_str)

            if info:
                colour = info["color"]
                has_contrib = info["count"] > 0
            else:
                colour = COLOURS[0]
                has_contrib = False

            delay = cell_index * ANIM_PER_CELL
            cell_line_parts.append(rect_tag(x, y, colour, delay, has_contrib))
            cell_index += 1

    parts.append("".join(cell_line_parts))

    # Footer: total
    total_fmt = f"{total:,}"
    parts.append(text_tag("total", X0, 152, f"{total_fmt} contributions in the last year"))

    parts.append("</svg>")

    return "\n".join(parts) + "\n"


# ── entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    json_path = Path("contributions.json")
    if not json_path.exists():
        print(
            "[ERROR] contributions.json not found. "
            "Run fetch_contributions.py first.",
            file=sys.stderr,
        )
        sys.exit(1)

    with json_path.open(encoding="utf-8") as fh:
        data = json.load(fh)

    svg = build_svg(data)

    out_path = Path("contrib-heatmap.svg")
    out_path.write_text(svg, encoding="utf-8")
    print(
        f"[OK] Written {out_path} "
        f"({data['total_contributions']:,} contributions, "
        f"{len(data['days'])} days)"
    )


if __name__ == "__main__":
    main()
