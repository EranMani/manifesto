# /parallel-wave-detector — Parallel Wave Detector

**When to invoke:** When planning or replanning the commit sequence — after new commits are added, or when Eran asks whether two pending commits can run simultaneously.

Pass two or more commit specs (or commit numbers). Receive a definitive YES/NO with the exact Wave line ready for commit-protocol.md.

---

## Input

Call with: `/parallel-wave-detector` followed by:
- Two or more commit numbers (e.g. "C17 and C18")
- Or: "check all pending commits for parallelism"

Claude loads the relevant commit specs from `commit-specs/` automatically.

---

## Parallelism Rules

Two commits can run in parallel if and only if ALL of the following are true:

### Rule 1 — No shared files
The file sets touched by each commit must be completely non-overlapping.
Even a shared `__init__.py` or `main.py` edit blocks parallelism.

**Check:** List every file each commit creates or modifies. Is there any overlap? If yes → NOT parallelizable.

### Rule 2 — No data dependency
Neither commit's output is an input to the other.
If Commit A creates a function that Commit B imports → NOT parallelizable.
If Commit A creates a DB table that Commit B queries → NOT parallelizable.

**Check:** Does either commit spec list a "Depends on" that points to the other, or to the same prerequisite? If the dependency chain overlaps → NOT parallelizable.

### Rule 3 — Same phase or adjacent phases with no cross-dependency
Commits in completely different phases (e.g. backend C06 and frontend C03) are candidates.
Commits in the same phase touching the same layer are usually NOT candidates.

### Rule 4 — Same assignee blocks parallelism
Two commits owned by the same agent cannot run in parallel — the agent can only work one commit at a time.

**Exception:** If the Team Lead explicitly assigns two agents to the same role domain (e.g. two backend engineers), this rule is relaxed.

---

## Output Format

For a YES verdict:
```
## Parallel Wave — C[N] ∥ C[M]

Verdict: PARALLELIZABLE ✅

Reason:
- File sets: [C[N] touches X,Y — C[M] touches A,B — zero overlap]
- Data dependency: none
- Assignees: [Rex for C[N], Aria for C[M] — different agents]

Wave line for commit-protocol.md:
  Wave [X]: [N] ∥ [M]  — [brief reason, e.g. "backend models vs frontend scaffold, no shared files"]

Worktree isolation required: [yes — use isolation: "worktree" in Agent call | no]
```

For a NO verdict:
```
## Parallel Wave — C[N] + C[M]

Verdict: NOT PARALLELIZABLE ❌

Blocking reason: [specific rule that fails — e.g. "C[M] depends on C[N]'s output: main.py router registration"]
Must sequence: C[N] → C[M]
```

For a multi-commit scan:
```
## Parallel Wave Scan — Pending Commits

Parallelizable pairs found:
- C[N] ∥ C[M] — [reason]
- C[X] ∥ C[Y] — [reason]

Sequential only:
- C[A] → C[B] — [blocking reason]
```

---

## Rules

- When in doubt, call it sequential. A false negative (missed parallelism) wastes time. A false positive (bad parallelism) causes file conflicts or broken imports.
- Worktree isolation (`isolation: "worktree"`) is required whenever parallelism is confirmed — never run parallel agents in the same working directory.
- Add confirmed wave lines to `commit-protocol.md` under the Parallel Groups section immediately.
