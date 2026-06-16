#!/usr/bin/env python3
"""Safely reset a failed tool-cap invocation without hand-editing JSON."""

from __future__ import annotations

import argparse
import sys

from tool_cap_start import git_root, load_state, reset_invocation_state, write_state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument(
        "--kind",
        choices=["normal", "repair", "review", "explore"],
        default="normal",
    )
    parser.add_argument(
        "--discard-closed",
        action="store_true",
        help="Also remove prior closed invocations for the same agent/kind and subtract their tokens.",
    )
    args = parser.parse_args()

    root = git_root()
    state_path = root / "hooks" / "tool_cap.json"
    state = load_state(state_path)
    if state is None:
        print("CIRCUIT BREAKER: no valid tool_cap.json state", file=sys.stderr)
        return 2

    expected = args.commit.upper()
    if not expected.startswith("C"):
        expected = f"C{int(args.commit):02d}"
    if str(state.get("commit", "")).upper() != expected:
        print(
            f"CIRCUIT BREAKER: state is for {state.get('commit')}, not {expected}",
            file=sys.stderr,
        )
        return 2

    try:
        reset_invocation_state(
            state,
            agent=args.agent,
            kind=args.kind,
            discard_closed=args.discard_closed,
        )
    except ValueError as exc:
        print(f"CIRCUIT BREAKER: {exc}", file=sys.stderr)
        return 2

    write_state(state_path, state)
    print(f"reset {expected} {args.agent.lower()} {args.kind} invocation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
