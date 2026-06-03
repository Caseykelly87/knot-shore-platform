#!/usr/bin/env python3
"""Drift guard for the platform README.

Every service repo guards its own README test count with a
``tests/test_docs_count.py`` that compares the README number against a
live ``--collect-only``. The orchestration README, which summarizes all
four services plus portal-derived facts (decision count, about-page set)
and the detection rule set, had no equivalent guard. This script is that
guard: it asserts the platform README's cross-cutting claims still match
their sources in the checked-out submodules.

What it checks, and where each fact comes from:

1. Per-service test counts. The authoritative live count lives in each
   service's own suite; running four ``pytest --collect-only`` passes in
   CI is heavy and, for the sim engine, flaky — three of its 142 tests
   need the optional SQLAlchemy extra and a bare checkout collects 139.
   Rather than re-run the suites, this guard cross-checks the platform
   README against each submodule's own README headline (which that
   service's own guard keeps honest against its live count). The chain is
   transitive: platform README == submodule README == live count, as long
   as the submodule is pinned at a commit whose own guard passed. Residual
   gap: if a submodule's own count guard is wrong or absent, this guard
   inherits that. That is the trade for an environment-stable check that
   needs no service dependencies and no optional extras.

2. Decision count. Derived live from ``lib/about/decisions.ts`` in the
   portal submodule (the source of truth the about page renders) and
   asserted against the README's "N architectural decisions".

3. About-page set. Derived live from the portal's ``app/about/*`` route
   directories and asserted against the README's page count and the
   named sub-page list.

4. Detection framing. Asserts the README names the department-grain rules
   (``gross_margin_band``, ``department_reconciliation``) and states the
   nine-defined / six-firing framing, so a future detection change that
   the README doesn't reflect fails here.

5. ``.gitmodules`` branch tracking. The README claims ``--remote`` tracks
   each service's ``main``; this asserts ``.gitmodules`` actually declares
   ``branch = main`` for all four and that the URLs carry the ``.git``
   suffix.

Run from anywhere; paths resolve relative to the repo root. Exits 0 when
every claim holds, 1 (listing each failure) otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
GITMODULES = REPO_ROOT / ".gitmodules"
SERVICES = REPO_ROOT / "services"

# Expected per-service full-suite counts. These are the released-state
# headline numbers; the guard verifies both the submodule README and the
# platform README still agree with them.
EXPECTED_SERVICE_TESTS = {
    "sim-engine": 142,
    "etl": 287,
    "api": 180,
    "portal": 222,
}
EXPECTED_TOTAL = sum(EXPECTED_SERVICE_TESTS.values())  # 831

# Regex that pulls each submodule README's own headline count.
SUBMODULE_COUNT_PATTERNS = {
    "sim-engine": r"test suite has (\d+) tests",
    "etl": r"contains (\d+) tests",
    "api": r"all (\d+) tests",
    "portal": r"\((\d+) tests across \d+ files\)",
}

# The department-grain rules whose omission was the original drift, plus
# the firing-rule framing the README must carry.
REQUIRED_RULE_NAMES = ("gross_margin_band", "department_reconciliation")

WORD_TO_NUM = {
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

# The about route set the README's count and list must match.
EXPECTED_ABOUT_PAGES = {
    "architecture", "decisions", "detection-quality", "lessons",
    "operations", "sim-engine", "etl", "api", "portal",
}
PER_SERVICE_PAGES = {"sim-engine", "etl", "api", "portal"}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_service_counts(readme: str, failures: list[str]) -> None:
    """Per-service counts: submodule headline == expected == in platform README."""
    for service, expected in EXPECTED_SERVICE_TESTS.items():
        sub_readme = SERVICES / service / "README.md"
        if not sub_readme.is_file():
            failures.append(
                f"[counts] submodule README missing: {sub_readme} "
                f"(is the submodule checked out?)"
            )
            continue
        text = _read(sub_readme)
        match = re.search(SUBMODULE_COUNT_PATTERNS[service], text)
        if not match:
            failures.append(
                f"[counts] could not find a test-count headline in "
                f"{service}/README.md (pattern: "
                f"{SUBMODULE_COUNT_PATTERNS[service]!r})"
            )
            continue
        found = int(match.group(1))
        if found != expected:
            failures.append(
                f"[counts] {service}/README.md headline is {found}, "
                f"expected {expected}"
            )
        if not re.search(rf"\b{expected}\b", readme):
            failures.append(
                f"[counts] platform README does not cite {service}'s "
                f"{expected} tests"
            )

    if EXPECTED_TOTAL != 831:
        failures.append(
            f"[counts] expected per-service counts sum to {EXPECTED_TOTAL}, "
            f"not 831"
        )


def check_decision_count(readme: str, failures: list[str]) -> None:
    """README decision count must match the entries in decisions.ts."""
    decisions = SERVICES / "portal" / "lib" / "about" / "decisions.ts"
    if not decisions.is_file():
        failures.append(f"[decisions] source missing: {decisions}")
        return
    # Each DecisionEntry begins with an indented `title: "..."`. The
    # interface declaration uses `title: string;` (no quote), so anchoring
    # on the opening quote counts entries and not the type definition.
    entry_count = len(re.findall(r'^\s+title:\s*"', _read(decisions), re.M))
    match = re.search(r"(\d+) architectural decisions", readme)
    if not match:
        failures.append(
            "[decisions] platform README has no 'N architectural decisions' "
            "claim to check"
        )
        return
    stated = int(match.group(1))
    if stated != entry_count:
        failures.append(
            f"[decisions] README says {stated} architectural decisions; "
            f"decisions.ts has {entry_count}"
        )


def check_about_pages(readme: str, failures: list[str]) -> None:
    """README about-page count and list must match the portal's routes."""
    about_dir = SERVICES / "portal" / "app" / "about"
    if not about_dir.is_dir():
        failures.append(f"[about] route directory missing: {about_dir}")
        return
    pages = {
        d.name for d in about_dir.iterdir()
        if d.is_dir() and (d / "page.tsx").is_file()
    }
    if pages != EXPECTED_ABOUT_PAGES:
        missing = EXPECTED_ABOUT_PAGES - pages
        extra = pages - EXPECTED_ABOUT_PAGES
        detail = []
        if missing:
            detail.append(f"missing {sorted(missing)}")
        if extra:
            detail.append(f"unexpected {sorted(extra)}")
        failures.append(f"[about] route set drift: {', '.join(detail)}")

    # "<word>-page about section" must resolve to the live page count.
    match = re.search(r"(\w+)-page about\s+section", readme)
    if not match:
        failures.append("[about] README has no '<word>-page about section' claim")
    else:
        word = match.group(1).lower()
        stated = WORD_TO_NUM.get(word)
        if stated is None:
            failures.append(f"[about] unrecognized page-count word: {word!r}")
        elif stated != len(pages):
            failures.append(
                f"[about] README says {word}-page ({stated}); "
                f"portal ships {len(pages)} about pages"
            )

    # The sub-page count (non-per-service) must match too.
    sub_match = re.search(r"(\w+) sub-pages plus four\s+per-service", readme)
    expected_sub = len(pages - PER_SERVICE_PAGES)
    if not sub_match:
        failures.append("[about] README has no 'N sub-pages plus four per-service' claim")
    else:
        word = sub_match.group(1).lower()
        stated = WORD_TO_NUM.get(word)
        if stated != expected_sub:
            failures.append(
                f"[about] README says {word} sub-pages; "
                f"portal ships {expected_sub} non-per-service about pages"
            )

    if "/about/detection-quality" not in readme:
        failures.append(
            "[about] README does not list /about/detection-quality"
        )


def check_detection_framing(readme: str, failures: list[str]) -> None:
    """README must name the department-grain rules and the firing framing."""
    for name in REQUIRED_RULE_NAMES:
        if name not in readme:
            failures.append(f"[detection] README does not mention `{name}`")
    # "Nine ... defined; six fire" (case-insensitive, allowing prose between).
    if not re.search(r"[Nn]ine\b[^.]*\bdefined\b", readme):
        failures.append("[detection] README does not state nine rules defined")
    if not re.search(r"\bsix\b[^.]*\bfire", readme):
        failures.append("[detection] README does not state six rules fire")
    if "178" not in readme:
        failures.append("[detection] README does not cite the 178-flag total")


def check_gitmodules(failures: list[str]) -> None:
    """README claims --remote tracks main; .gitmodules must back that."""
    if not GITMODULES.is_file():
        failures.append(f"[gitmodules] missing: {GITMODULES}")
        return
    text = _read(GITMODULES)
    branch_count = len(re.findall(r"^\s*branch\s*=\s*main\s*$", text, re.M))
    if branch_count != 4:
        failures.append(
            f"[gitmodules] expected 4 'branch = main' lines, found "
            f"{branch_count}"
        )
    url_lines = re.findall(r"^\s*url\s*=\s*(\S+)$", text, re.M)
    non_git = [u for u in url_lines if not u.endswith(".git")]
    if non_git:
        failures.append(
            f"[gitmodules] submodule URLs missing .git suffix: {non_git}"
        )


def main() -> int:
    if not README.is_file():
        print(f"FAIL: platform README not found at {README}", file=sys.stderr)
        return 1
    readme = _read(README)

    failures: list[str] = []
    check_service_counts(readme, failures)
    check_decision_count(readme, failures)
    check_about_pages(readme, failures)
    check_detection_framing(readme, failures)
    check_gitmodules(failures)

    if failures:
        print("Platform README drift guard FAILED:\n")
        for f in failures:
            print(f"  - {f}")
        print(
            f"\n{len(failures)} check(s) failed. Update the README to match "
            f"current source (or the source to match intent)."
        )
        return 1

    print(
        "Platform README drift guard passed: per-service counts "
        f"({', '.join(f'{k} {v}' for k, v in EXPECTED_SERVICE_TESTS.items())}; "
        f"total {EXPECTED_TOTAL}), decision count, about-page set, detection "
        "framing, and .gitmodules branch tracking all match current source."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
