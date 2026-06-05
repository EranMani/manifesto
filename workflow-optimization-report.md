# Workflow Optimization Report
**Authors:** Andrej Karpathy + Boris Cherny · For: Eran Mani (Team Lead)
**Date:** 2026-06-05
**Source:** Claude Code Insights Report (1,089 messages, 136 sessions, 2026-05-07 to 2026-06-05)

---

## Executive Summary

Your manifesto is one of the most disciplined multi-agent orchestration setups we've seen outside of a research lab. The commit-protocol loop, domain isolation, and approval gates are genuinely impressive. But the insights report reveals a clear pattern: **you're burning tokens on re-reads, agents are exhausting tool caps mid-task, and your uniqueness advantage is not yet fully captured in tooling.** This report is split into three parts — fixing what's broken, compressing what's wasteful, and building what makes you different.

---

## Part 1 — What the Insights Report Actually Tells Us

### The real numbers

- **2,341 Read calls** across sessions — the single most-used tool by a wide margin
- **347 Agent spawns** — each costs 10–30k tokens of overhead per your own CLAUDE.md
- **145 "Command Failed" errors** — mostly from fragile shell CWD / hook config breakage
- **25 tool cap** per agent — being hit mid-task by Rex and Nova, causing regressions you had to catch yourself

The data tells one story: **the system is architecturally sound but operationally expensive.** Agents re-read files they shouldn't, spawn for work that could be a direct Edit, and fail at environment boundaries that should have been hardened once and never touched again.

### The token math

A typical commit step today likely looks like this:

```
Boot reads (project-state, team-preferences, commit-protocol, commit spec): ~4k tokens
Agent invocation overhead (context window bootstrap): ~15–25k tokens per agent
Agent re-reads (speculative Globs and Reads): ~3–8k tokens
Worklog write + post-commit checklist: ~2k tokens
─────────────────────────────────────────────────────────────────────────────
Estimate per commit step: 25–40k tokens
```

At 57 messages/day and a median response time of ~2 minutes, you're running a tight loop. The opportunity isn't to slow down — it's to eliminate the re-reads and speculative work that don't add information.

---

## Part 2 — Token Reduction: Concrete Changes

### 2.1 The Context Package is Your Biggest Lever

Your CLAUDE.md already has the right instinct: "load minimum context." But "minimum context" needs to be defined per agent, per tier. Right now agents load what they think they need. The fix is to define it explicitly in the commit spec itself.

**Add a `context:` block to every commit spec:**

```markdown
## context
tier0:
  - .claude/agents/rex.md (lines 1-50 only — Current State header)
tier1:
  - backend/app/routes/questions.py
  - backend/tests/test_questions.py
forbidden:
  - backend/alembic/  # no migrations this commit
  - frontend/         # Rex domain boundary
```

When Claude builds the context package, it reads this block and passes it verbatim to the agent as its allowed read list. Any Read outside this list is a protocol violation. This single change eliminates speculative Glob and Read calls — which is a significant fraction of your 2,341 Read total.

### 2.2 Compress the Boot Sequence

Every session reads four files before anything happens. That's fine for correctness, but the files aren't compressed for skimmability. Add a `## TL;DR` header to each governance file — three lines max — that Claude reads first. If the TL;DR says "no changes since last session," Claude can skip the full read.

**Example addition to `project-state.json`:**

```json
{
  "tldr": "C07 complete. C08 pending. No blockers. No open handoffs.",
  "last_updated": "2026-06-05",
  ...
}
```

Claude reads `tldr` first. If it matches what's in the Commit Preview, no further reads needed for state verification.

### 2.3 Stop Re-Reading Agent Identity Files You Already Know

CLAUDE.md says: load agent's "Current State header (≤50 lines)." But the insights report shows 2,341 Read calls. Some of those are re-reading the same agent files across steps in the same session. 

Add an explicit rule: **within a session, agent identity files are read once and cached in-context.** Only re-read if the agent's worklog timestamp changed since the last read. Add this to CLAUDE.md:

```
5. Agent identity reads are session-cached. If you already read [agent].md this session
   and no commit has landed since, do NOT re-read it. Use the version in context.
```

### 2.4 Haiku for Everything Non-Generative

Your roster already does this for Viktor, Sage, and Mira. Apply the same logic to pre-invocation checks. The `/next-step` command reads four files and synthesizes a situation summary before asking Eran for approval. That synthesis doesn't need Sonnet — it's pattern matching against a known schema. Consider a lightweight "state reader" sub-task that runs on Haiku, returns a structured JSON summary, and passes it to Sonnet for the final Commit Preview render.

---

## Part 3 — Enforcing Tool Limits (So Agents Can't Exceed the Cap)

This is the core reliability problem. Rex and Nova hit 25 tool uses and stop mid-task, leaving stale state. Your EXECUTION CONSTRAINTS block tells them to stop and report — but agents hitting the cap naturally are in unpredictable partial-done states.

### 3.1 Phase Budget: Allocate Tool Uses Explicitly Per Phase

The current constraint is: "Max tool uses: 25. Plan reads upfront. Batch writes."

This isn't tight enough. Replace it with an explicit phase budget:

```
EXECUTION CONSTRAINTS:
- Phase 1 (Reads): max 10 tool uses. If you need more than 10 reads, stop and report — scope is too large.
- Phase 2 (Writes + Tests): max 12 tool uses. This includes Edit, Write, and up to 2 Bash test runs.
- Reserve: 3 tool uses for worklog write + unexpected blockers.
- Total cap: 25. Non-negotiable. If Phase 1 approaches 10, consolidate reads immediately.
```

Now an agent knows at tool-use 8 that it's nearing the read limit — not at tool-use 24 when it's too late. The phase budget creates early warning, not just a hard stop.

### 3.2 Scope Sizing in Commit Specs

The insights report flagged this: Rex hit the cap because commit scopes were too large for a single agent invocation. The fix is upstream — in the commit spec design.

Add a `complexity` field to every commit spec:

```markdown
## complexity
estimated_reads: 8
estimated_edits: 5
fits_single_agent: true   # or false → split into phases A/B
```

When `fits_single_agent: false`, Claude automatically structures the commit as two sequential agent invocations: one for reads/analysis and one for writes. This is a pre-flight check, not a reactive split.

Claude should validate this estimate before invoking the agent:
> "Commit spec estimates 8 reads + 5 edits = 13 tool uses. Within the 25-tool budget. Proceeding."

If the estimate is wrong and the agent reports at tool 24, the scope was miscalculated — that goes into DECISIONS.md as a calibration note.

### 3.3 A Pre-Commit Hook That Counts Tool Uses

This is the enforcement layer. Claude Code hooks fire at `PostToolUse`. Add a counter hook that writes to a session-local file:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": ".*",
      "command": "python hooks/tool_counter.py --increment --session $CLAUDE_SESSION_ID"
    }]
  }
}
```

`tool_counter.py` tracks uses per agent-session. At 20 uses, it writes a warning to stdout that Claude sees. At 25, it writes `TOOL_CAP_REACHED` — a signal Claude is trained (via CLAUDE.md rule) to treat as a hard stop. The agent doesn't decide to stop; the environment forces it.

This is the difference between "we told the agent to stop" and "the environment stops the agent." The latter is reliable.

### 3.4 The "Two-Phase Agent" Pattern for Complex Commits

For commits where `fits_single_agent: false`, standardize this invocation pattern:

```
Phase A invocation: "Rex — READ ONLY phase. Read these 8 files. Output a structured
analysis: which functions change, what the test assertions need to be, any blockers.
Do NOT write anything. Stop after the analysis."

[Claude receives analysis, verifies it makes sense, passes it to Phase B]

Phase B invocation: "Rex — WRITE phase. Here is the analysis from Phase A (attached).
Write these exact changes. Run tests once. Report done."
```

Phase A uses 8–10 tool uses. Phase B uses 10–15. Each is under cap. And critically: Claude sees the Phase A output before Phase B begins — a natural checkpoint for Eran to inspect the plan before code gets written.

---

## Part 4 — Standing Out: Unique Workflow Methods You Can Claim

Most developers using Claude Code fall into one of three patterns: (1) ad-hoc REPL — type a prompt, get code; (2) basic CLAUDE.md — some project context; (3) slash commands — a few custom workflows. You're already well past all three. Here's how to push further into territory almost no one occupies.

### 4.1 The Signed Commit Protocol

Right now your commit protocol enforces: no self-commit, co-author trailer, approval gate. That's already unusual. Take it one step further: **every commit message is machine-verifiable as protocol-compliant before it lands.**

Add a `commit-linter.py` hook that checks:
- Co-Authored-By trailer is present and matches a known agent email from `agent-config.json`
- Commit message references a commit spec ID (e.g., `C08`)
- `CLAUDE_COMMIT=1` env var was set (meaning the orchestrator, not an agent, ran it)
- `project-state.json` was updated in this diff

If any check fails, the commit is rejected with a specific error message. This is something you can demonstrate: "every commit in this repo is cryptographically traceable to a spec, an agent, and an approval event." No one else is doing this at the indie/small-team level.

### 4.2 Context Tiers as a First-Class Concept

Most people dump everything into CLAUDE.md and hope for the best. You already have the instinct for tiered loading. Formalize it as a system:

```
Tier 0: Always loaded (CLAUDE.md, tldr of project-state.json) — ~500 tokens
Tier 1: Per-commit (commit spec, agent identity header, active handoffs) — ~2k tokens  
Tier 2: Per-task (specific source files, test files, relevant worklog entries) — variable
Tier 3: On-demand only (full worklog history, other agents' files, architecture doc)
```

Write this tier system into ORCHESTRATION.md and into every agent identity file. Now every agent invocation brief includes: "Loading: Tier 0 + Tier 1 + Tier 2 [list files]." Any file not in that list cannot be read. This is a systematic token budget, not a soft guideline.

The claim you can make: **"I designed a tiered context loading system that keeps every agent invocation under a defined token budget. Agents operate within resource constraints, not just behavioral ones."**

### 4.3 The Worklog as a Training Signal

Your worklogs are currently write-only artifacts — agents write to them, Claude reads the header. But they contain something valuable: a record of every mistake, every blocker, every successful pattern. 

Add a `lessons:` section to every worklog that Viktor populates during the gate wave:

```markdown
## lessons (Viktor-maintained)
- C07: Rex missed a None-return guard on set_visibility() — add mypy strict to Phase 2 test run
- C05: Scope was too large, hit tool cap at 23. Split into A/B next time for this file count.
```

Now when Claude builds the context package for a similar commit, it searches `lessons:` by file path or commit type and injects the relevant lessons into the agent brief. It's a feedback loop that gets cheaper over time — the system self-calibrates.

The claim: **"My agents learn from past mistakes within the same project. The worklog isn't documentation — it's a live training signal that modifies how future agents are briefed."**

### 4.4 Parallel Wave Detection as Standard Practice

Your `/parallel-wave-detector` command exists but the insights report shows zero parallel Claude sessions. This is leaving performance on the table. For any two commits with non-overlapping domains (Rex + Aria, for example), they should run simultaneously.

The pattern to establish: after every commit, Claude checks whether the next two commits are parallelizable. If yes, it presents a parallel Commit Preview:

```
## Parallel Wave: C09 (Rex) ∥ C10 (Aria)

These commits touch non-overlapping domains. Both can run simultaneously.
Combined estimated time: same as one sequential commit.
Risk: if Rex's changes require a type export that Aria imports, there's a dependency.
Checking... [grep for imports] → no cross-domain dependency detected. Safe to parallelize.

Invoke Rex and Aria simultaneously?
```

This is a concrete workflow claim: **"I run parallel agent commits on non-overlapping domains, with automated dependency checking before the wave launches."**

---

## Part 5 — Immediate Action Items (Priority Order)

These are the changes that pay off fastest, in order:

**This week — stop the bleeding:**

1. Add `context:` blocks with `forbidden:` lists to all pending commit specs. This eliminates speculative reads.
2. Replace the flat "Max tool uses: 25" constraint with the phase-budget version (Part 3.1). Apply to Rex, Adam, Aria immediately.
3. Add `tldr` field to `project-state.json`. Saves a full file parse every session boot.

**Next 2–3 commits — enforce at the environment level:**

4. Write `tool_counter.py` hook. Even a simple counter that prints a warning at tool 20 is better than the current honor-system cap.
5. Add `complexity: fits_single_agent: true/false` to all remaining commit specs. Use this to decide when to invoke the two-phase pattern.

**Before the project gets complex:**

6. Formalize the tier system in ORCHESTRATION.md. Once you have 10+ commits of history, ad-hoc context loading will start causing drift.
7. Add a `lessons:` section to Viktor's review template. Start capturing mistakes now, while there are only a few. Retrofitting this at commit 50 is painful.
8. Run the parallel wave detector after every commit as a standard step — not optional.

---

## Closing Note

The developers who will still have differentiated workflows in 12 months are not the ones who learned the most prompts. They're the ones who built systems — token budgets, enforcement hooks, feedback loops, signed commits — that make their AI teammates more reliable as the codebase grows. You already have the architecture. The work now is closing the gap between the rules you've written and the rules the environment enforces.

The insights report is honest: your gates caught most things, you caught the rest. The goal is to make the gates catch everything.

---

*Report prepared by Andrej Karpathy + Boris Cherny. For implementation questions, route through the standard commit protocol.*
