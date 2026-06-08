#!/usr/bin/env python3
"""Generate a shadow Context Package V2 preview for a Manifesto commit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from context_engine import ContextPackageBuilder, load_rules


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RULES = Path(__file__).resolve().parent / "context_rules.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True, help="Commit number, for example 25")
    parser.add_argument("--agent", required=True, help="Agent id, for example nova")
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--out", type=Path, help="Optional output path")
    parser.add_argument(
        "--shadow",
        action="store_true",
        help="Explicitly confirm preview-only mode",
    )
    args = parser.parse_args()

    if not args.shadow:
        parser.error("Phase A supports shadow mode only; pass --shadow")

    rules = load_rules(args.rules)
    package = ContextPackageBuilder(REPO_ROOT, rules).build(
        args.commit,
        args.agent.lower(),
    )
    output = args.out or (
        REPO_ROOT
        / ".context"
        / "runs"
        / f"{package['commit']}-{args.agent.lower()}-shadow.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")

    print(f"Shadow context written: {output.relative_to(REPO_ROOT)}")
    print(
        "Selected "
        f"{package['budget']['selected_files']} files, "
        f"~{package['budget']['estimated_selected_chars']} chars"
    )
    print(f"Graph source: {package['graph']['source']}")
    if package["expansion_triggers"]:
        print("Expansion triggers:")
        for trigger in package["expansion_triggers"]:
            print(f"- {trigger}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
