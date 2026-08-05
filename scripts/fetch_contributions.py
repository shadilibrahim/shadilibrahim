"""
fetch_contributions.py
~~~~~~~~~~~~~~~~~~~~~~
Scrapes the public GitHub contribution calendar for shadilibrahim
and writes a structured JSON file consumed by render_heatmap_svg.py.

No authentication token is required; GitHub exposes contribution
data on the public /contributions route used here.
"""

import json
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup

USERNAME = "shadilibrahim"
URL = f"https://github.com/users/{USERNAME}/contributions"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; profile-art-bot/1.0; "
        "+https://github.com/shadilibrahim)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
}

# GitHub contribution level → count bracket used for colour bucketing.
# The actual colour is decided in render_heatmap_svg.py; the level
# attribute (0-4) is the canonical signal exposed by the HTML.
LEVEL_COLOURS = {
    "0": "#161b22",   # no contributions
    "1": "#0e4429",   # 1–3
    "2": "#006d32",   # 4–6
    "3": "#26a641",   # 7–9
    "4": "#39d353",   # 10+
}


def fetch() -> dict:
    """Return parsed contribution data as a dict."""
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[ERROR] Could not fetch {URL}: {exc}", file=sys.stderr)
        sys.exit(1)

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── locate the contribution graph table ──────────────────────────────
    # GitHub renders <td data-date="YYYY-MM-DD" data-level="0..4">
    cells = soup.select("td[data-date][data-level]")

    if not cells:
        # Fallback: try the older rect-based graph (some edge paths)
        cells = soup.select("rect[data-date][data-level]")

    if not cells:
        print(
            "[ERROR] Could not find contribution cells in the page. "
            "GitHub may have changed their HTML structure.",
            file=sys.stderr,
        )
        sys.exit(1)

    days: list[dict] = []
    total = 0

    for cell in cells:
        date_str = cell.get("data-date", "")
        level = cell.get("data-level", "0")
        count_str = cell.get("data-count", "")  # present on newer GH HTML

        # Derive a best-effort count when data-count is absent
        if count_str.isdigit():
            count = int(count_str)
        else:
            # Fall back to bracket midpoints so the renderer has numbers
            count = {"0": 0, "1": 2, "2": 5, "3": 8, "4": 12}.get(level, 0)

        # Parse the tooltip text as another source (older HTML)
        title_tag = cell.find("tool-tip") or cell.find("title")
        if title_tag and not count_str.isdigit():
            import re
            match = re.search(r"(\d[\d,]*)\s+contribution", title_tag.get_text())
            if match:
                count = int(match.group(1).replace(",", ""))

        total += count
        days.append(
            {
                "date": date_str,
                "count": count,
                "level": int(level),
                "color": LEVEL_COLOURS.get(level, "#161b22"),
            }
        )

    # ── sort chronologically just in case ───────────────────────────────
    days.sort(key=lambda d: d["date"])

    payload = {
        "username": USERNAME,
        "fetched_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_contributions": total,
        "days": days,
    }

    return payload


def main() -> None:
    data = fetch()
    out_path = "contributions.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    print(
        f"[OK] Saved {len(data['days'])} days "
        f"({data['total_contributions']:,} contributions) → {out_path}"
    )


if __name__ == "__main__":
    main()
