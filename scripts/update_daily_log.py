"""
update_daily_log.py
~~~~~~~~~~~~~~~~~~~
Generates a meaningful daily-log.md entry with today's date,
a rotating coding tip, and a motivational quote.
Committed daily by the GitHub Actions workflow.
"""

from datetime import datetime, timezone
import json
import math
import random
from pathlib import Path

# ── Content pools ─────────────────────────────────────────────────────────────

CODING_TIPS = [
    "Write code for humans first, computers second. Clarity > cleverness.",
    "Name variables after what they *mean*, not what they *are*.",
    "A function should do one thing — and do it well.",
    "Read error messages carefully; they usually tell you exactly what's wrong.",
    "Version control is your safety net — commit early, commit often.",
    "Comment the *why*, not the *what*. The code already shows the what.",
    "Refactor relentlessly. Leave every file cleaner than you found it.",
    "Test at the boundaries: empty input, zero, max values, and None.",
    "Debugging is twice as hard as writing code, so write the clearest code you can.",
    "DRY: Don't Repeat Yourself — but don't abstract too early either.",
    "Performance optimise *after* you measure, not before.",
    "A good README is as important as good code.",
    "Review your own PRs before asking others — catch the obvious stuff yourself.",
    "Use meaningful commit messages: future-you will thank present-you.",
    "Prefer composition over inheritance; keep your objects loosely coupled.",
    "Keep dependencies minimal — every library is technical debt.",
    "Sleep on hard bugs. A rested brain solves in minutes what exhaustion can't in hours.",
    "The best code is code you don't have to write — check if it exists first.",
    "Document your APIs as if the user has no access to your source code.",
    "Learn the keyboard shortcuts of your editor — speed compounds over time.",
    "Use linters and formatters; remove style debates from code reviews.",
    "Understand Big-O — it matters when data gets large.",
    "Pair programming isn't just for juniors; everyone learns from it.",
    "When stuck, explain the problem aloud — the answer often arrives mid-sentence.",
    "Security is not a feature you add later; bake it in from the start.",
    "Always validate and sanitise user input — never trust it blindly.",
    "Make it work, make it right, make it fast — in that order.",
    "Open source something, even if it's small; giving back accelerates everyone.",
    "Learn one new terminal command per week; the CLI is your superpower.",
    "Code review is a conversation, not a judgement — be kind and specific.",
    "Automate repetitive tasks; your time is better spent solving new problems.",
    "Keep functions short enough to fit on one screen without scrolling.",
    "Use constants instead of magic numbers — names carry intent.",
    "A failing test that you wrote is better than a bug you didn't catch.",
    "Great engineers ask questions — there are no stupid ones.",
    "Data structures matter more than algorithms in most production code.",
    "Ship something imperfect and iterate; perfect is the enemy of shipped.",
    "Logs are your best friend in production — log enough to diagnose, not too much to search.",
    "Understand the problem fully before touching the keyboard.",
    "Every hour spent on good architecture saves ten hours of refactoring.",
    "Avoid global state — it makes code hard to test and reason about.",
    "Learn to read other people's code; it's a skill that pays dividends.",
    "Concurrency is hard — prefer message-passing over shared mutable state.",
    "Build for the 80% use-case first; edge cases come later.",
    "A good API is one you can understand without reading its documentation.",
    "Use descriptive branch names — `fix/login-null-crash` beats `fix2`.",
    "Handle errors explicitly; silent failures are the hardest bugs to find.",
    "Write the test before the fix — it proves the bug existed.",
    "Step away when frustrated — ten minutes of fresh air is worth an hour of staring.",
    "Measure twice, cut once — plan your data model before writing the first line.",
]

QUOTES = [
    ("Any fool can write code that a computer can understand. Good programmers write code that humans can understand.", "Martin Fowler"),
    ("First, solve the problem. Then, write the code.", "John Johnson"),
    ("Experience is the name everyone gives to their mistakes.", "Oscar Wilde"),
    ("In order to be irreplaceable, one must always be different.", "Coco Chanel"),
    ("Java is to JavaScript what car is to carpet.", "Chris Heilmann"),
    ("Knowledge is power.", "Francis Bacon"),
    ("Sometimes it pays to stay in bed on Monday rather than spending the rest of the week debugging Monday's code.", "Dan Salomon"),
    ("Simplicity is the soul of efficiency.", "Austin Freeman"),
    ("Before software can be reusable, it first has to be usable.", "Ralph Johnson"),
    ("Make it work, make it right, make it fast.", "Kent Beck"),
    ("The most important property of a program is whether it accomplishes the intention of its user.", "C.A.R. Hoare"),
    ("Programs must be written for people to read, and only incidentally for machines to execute.", "Harold Abelson"),
    ("There are only two hard things in Computer Science: cache invalidation and naming things.", "Phil Karlton"),
    ("The function of good software is to make the complex appear to be simple.", "Grady Booch"),
    ("One of my most productive days was throwing away 1,000 lines of code.", "Ken Thompson"),
    ("The best error message is the one that never shows up.", "Thomas Fuchs"),
    ("Deleted code is debugged code.", "Jeff Sickel"),
    ("If you think good architecture is expensive, try bad architecture.", "Brian Foote"),
    ("An idiot with a computer is a faster idiot.", "Proverb"),
    ("Programming isn't about what you know; it's about what you can figure out.", "Chris Pine"),
    ("The most disastrous thing you can ever learn is your first programming language.", "Alan Kay"),
    ("Walking on water and developing software from a specification are easy if both are frozen.", "Edward V. Berard"),
    ("It's not a bug — it's an undocumented feature.", "Anonymous"),
    ("Weeks of coding can save you hours of planning.", "Anonymous"),
    ("The best way to predict the future is to implement it.", "David Heinemeier Hansson"),
]

THEMES = [
    "🧩 Algorithm",
    "🐛 Debugging",
    "🏗️ Architecture",
    "🔐 Security",
    "⚡ Performance",
    "🧪 Testing",
    "📦 Tooling",
    "🤝 Collaboration",
    "📖 Learning",
    "🚀 Shipping",
]

# ── Deterministic daily selection (same run = same content) ───────────────────

def day_seed() -> int:
    """Return an integer seed based on today's date."""
    today = datetime.now(timezone.utc).date()
    return today.year * 10000 + today.month * 100 + today.day


def pick(pool: list, seed_offset: int = 0):
    rng = random.Random(day_seed() + seed_offset)
    return rng.choice(pool)


# ── Streak helpers ─────────────────────────────────────────────────────────────

def load_streak() -> int:
    """Read the last recorded streak from a simple state file."""
    state = Path(".daily_streak")
    if state.exists():
        try:
            return int(state.read_text().strip())
        except ValueError:
            pass
    return 0


def save_streak(n: int) -> None:
    Path(".daily_streak").write_text(str(n))


# ── Markdown builder ───────────────────────────────────────────────────────────

def build_log() -> str:
    today = datetime.now(timezone.utc)
    date_str   = today.strftime("%A, %B %d %Y")
    iso_str    = today.strftime("%Y-%m-%d")
    time_str   = today.strftime("%H:%M UTC")

    tip   = pick(CODING_TIPS, seed_offset=0)
    quote, author = pick(QUOTES, seed_offset=1)
    theme = pick(THEMES, seed_offset=2)

    streak = load_streak() + 1
    save_streak(streak)

    # Streak badge emoji
    if streak >= 100:
        badge = "🏆"
    elif streak >= 30:
        badge = "🔥"
    elif streak >= 7:
        badge = "⚡"
    else:
        badge = "🌱"

    lines = [
        f"# 📅 Daily Dev Log — {date_str}",
        "",
        f"> *Auto-generated at {time_str} · Day **{streak}** of consistent coding {badge}*",
        "",
        "---",
        "",
        f"## {theme} — Tip of the Day",
        "",
        f"> {tip}",
        "",
        "---",
        "",
        "## 💬 Quote of the Day",
        "",
        f'> "{quote}"',
        f">",
        f"> — **{author}**",
        "",
        "---",
        "",
        "## 🗓️ Log",
        "",
        f"- **Date**: {iso_str}",
        f"- **Streak**: {streak} day{'s' if streak != 1 else ''} {badge}",
        f"- **Theme**: {theme}",
        "",
        "_Keep building. Every line of code counts._ 🚀",
        "",
    ]
    return "\n".join(lines)


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    content = build_log()
    out = Path("daily-log.md")
    out.write_text(content, encoding="utf-8")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"[OK] Written daily-log.md for {today}")


if __name__ == "__main__":
    main()
