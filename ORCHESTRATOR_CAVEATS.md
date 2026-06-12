# Orchestrator Caveats — Known Gaps To Fix Later

> Honest record of gaps in the orchestration workflow itself (CLAUDE.md /
> ORCHESTRATION.md / next-step protocol), as distinct from gaps in the
> codebase (those live in `project-state.json` → `open_issues`).
>
> Update this file when a gap is fixed (move to "Resolved") or a new one
> is discovered. Cross-reference `open_issues` IDs (OI-NN) where applicable.

---

## Open

### 1. `/verify-commit` implies a quality gate it doesn't provide (OI-07)
CLAUDE.md and team-preferences.md both describe `/verify-commit` as a required
gate. In reality `verify_constraints.py` checks three things only: context
block present, no forbidden-path files, tool budget respected. It does NOT
check test results, logic correctness, doc currency, or spec conformance.

**Risk:** under time pressure, "verify-commit passed" can be misread as "the
implementation is correct" when the only thing actually verified is
structural compliance. The real correctness check (step 6a/6b manual logic
inspection) is the part most likely to get shortcut.

**Fix direction:** rename to something like `verify-structure`, or add an
explicit second gate name for the logic-inspection step so it can't be
silently skipped.

---

### 2. Orchestrator's own token cost is untracked (OI-03)
`TOKEN_RECORDS.md` tracks implementor/reviewer invocation tokens. Claude's own
orchestration tokens (boot, verification passes, correction rounds, commit
authoring) are never measured. "Claude-direct is cheap" is asserted but not
verifiable against real cost — and the orchestrator debugging circuit breaker
(D37) uses *tool-call count*, not tokens, as its proxy.

**Fix direction:** add an "orchestrator" row to the token schema and
instrument `--start-orchestrator` / `--stop-orchestrator` to also capture
token deltas, not just tool-call counts.

---

### 3. Preflight scoring is new and only validated against one commit (C29A history)
C29A's first invocation exhausted its 18-call budget on pure discovery and
returned `SPLIT_REQUIRED` before the spec was narrowed — i.e. the preflight
gate exists precisely because scope-sizing was previously unreliable. The
scoring engine (C29A) and dashboard (C29C) are themselves only a few commits
old; their accuracy across a wider variety of commit shapes (multi-file,
cross-domain, repair commits) is unproven.

**Risk:** a `READY (high score)` card could still mask an under-scoped commit
if the scoring heuristics don't generalize.

**Fix direction:** after a handful more commits, do a retrospective — for any
commit that needed a repair pass or SPLIT_REQUIRED, check whether the
preflight score should have caught it.

---

### 4. Card-only output format trades nuance for consistency
Since C29B, the `/next-step` response for a ready commit must be *only* the
preflight card — no prose, no rationale, no diagnostics unless blocked. This
is good for reducing noise, but it also means borderline judgment calls
(e.g. "this commit touches a file not in the spec table but it's clearly
required") have no natural place to surface before Eran says yes.

**Risk:** edge cases get silently absorbed into "Files" or "Warnings" lines
that may not capture the actual judgment being made.

**Fix direction:** keep the strict format, but make explicit that *any*
judgment call beyond the spec table is itself a "Decision required: Yes" —
don't let format rigidity become a reason to avoid flagging.

---

### 5. Manual logic inspection (step 6a/6b) has no enforcement mechanism
Unlike `/verify-commit` (mechanically checked) or the tool-call budget
(mechanically enforced), "inspect every edited file against the commit
contract" and "does each test fail when the requirement is violated?" are
pure self-discipline items. There's no hook or script that confirms this step
happened or was thorough.

**Risk:** this is the single highest-value check in the whole loop
(per CLAUDE.md rule 6: "structure checks miss logic bugs") and the one with
zero automated backstop.

**Fix direction:** at minimum, require the inspection notes (which files,
which validators/defaults checked, pass/fail per acceptance criterion) to be
written into the worklog before `/verify-commit` runs — turning a mental step
into an artifact that can be reviewed later.

---

## Resolved

*(none yet — move items here with resolution date + commit when fixed)*
