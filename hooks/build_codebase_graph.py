#!/usr/bin/env python3
"""Build the cached Phase A codebase graph."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from codebase_graph import write_codebase_graph
from context_engine import load_rules


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RULES = Path(__file__).resolve().parent / "context_rules.json"
DEFAULT_OUTPUT = REPO_ROOT / ".context" / "index" / "codebase-graph.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    root = args.repo_root.resolve()
    graph = write_codebase_graph(root, load_rules(args.rules), args.out.resolve())
    print(f"Codebase graph written: {args.out.resolve()}")
    print(
        f"Mapped {graph['totals']['files']} files, "
        f"{graph['totals']['edges']} edges, {graph['totals']['hubs']} hubs"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
