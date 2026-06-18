Parse `$ARGUMENTS` for the `--auto` flag. When `--auto` is present, auto-mode is
active: a READY preflight with zero violations and no decision required is treated as
pre-approved — proceed directly to implementation without waiting for Eran. If the
preflight is BLOCKED, has any warning, or requires a decision, fall back to the normal
approval flow regardless of the flag. Auto mode never skips post-implementation commit
approval — Eran still approves the final commit.

Read `project-state.json` to identify the next pending commit and owner. Check its
dependencies, open handoffs, and unresolved quality-gate findings.

Choose the execution route BEFORE running any preflight tooling:

- Default: `Claude (direct)`.
- Delegate only when at least one concrete justification applies: specialist uncertainty
  that Claude cannot resolve from selected context, independent implementation is needed
  for risk control, or the task is a clearly bounded specialist unit whose expected value
  exceeds invocation overhead.
- Never delegate workflow/governance changes, mechanical wiring, narrow repairs, known
  exact edits, or tests that Claude can implement directly.
- A domain owner is not automatically the executor.
- Record the justification in the card whenever execution is delegated. Without a
  written justification, execution remains Claude-direct.

Then run the readiness check for the chosen route:

- **Claude-direct (default):**
  `python hooks/preflight_commit.py --direct --commit <N> --agent <owner>`
  where `<owner>` is the commit's owner from the spec, not `"claude"` — executor and
  owner are separate concepts. This is a lean, ephemeral check: it validates only the
  active spec, this commit's own dependencies, ownership agreement, planned/forbidden
  files, and verification-command presence. It persists nothing, builds no context
  package, and never touches the dashboard. Returns `{status, proceed, violations}`.
- **Delegated (justified only):**
  `python hooks/prepare_agent_delegation.py --commit <N> --agent <agent-id> --preview`
  Preview mode must not initialize tool-cap state, telemetry, or the tracked dashboard.

The generated preflight result and (if delegated) delegation package are internal
preparation. When preflight is ready, do not narrate prerequisite checks, sequence
rationale, unlocks, token commentary, selected-context counts, contracts, hubs,
forbidden paths, graph refreshes, or other package diagnostics.

For C29B and every later commit, the compact approval card must be the entire
response. Output no preamble, transition sentence, explanation, or conclusion before
or after it. The first output line must be `C[N] PREFLIGHT: ...` and the final output
line must be `Proceed? [yes/no]`.

For Claude-direct, use this card (no numeric score — `evaluate_direct()` returns
`status: "ready"|"blocked"`, not a score):

```text
C[N] PREFLIGHT: [READY|BLOCKED]

Owner: [Name] ([Domain])
Executor: Claude (direct)
Goal: [one plain-language sentence]

Files:
- [Add|Edit|Delete]: path/to/file

Warnings:
- [Exact violation text from the `violations` array, or "None."]
- Decision required: [Yes|No]

Proceed? [yes/no]
```

For delegated execution, use the scored card:

```text
C[N] PREFLIGHT: [READY|BLOCKED] ([score]/100)

Owner: [Name] ([Domain])
Executor: Agent name (delegated)
Goal: [one plain-language sentence]

Files:
- [Add|Edit|Delete]: path/to/file

Warnings:
- [Exact warning text, or "None."]
- Delegation justification: [Reason]
- Decision required: [Yes|No]

Proceed? [yes/no]
```

Resolve the owner name and domain from `hooks/agent-config.json`. Populate `Files`
exclusively from the commit specification's `Files To Modify Or Add` table. Do not list
automatically updated worklogs, telemetry, dashboards, domain maps, tool-cap state, or
other generated/runtime artifacts unless they are explicitly present in that table.
List every warning in plain language. Do not replace the card with a prose preview or
append a second approval question such as "Shall I proceed?"

Show additional diagnostics only when:

- preflight is blocked;
- a warning requires Eran's decision;
- approved scope changed;
- a split or repair invocation is proposed; or
- Eran explicitly asks for details.

Claude-direct authorization follows ORCHESTRATION.md "Claude-Direct Authorization"
(authoritative): Claude-direct does not grant Claude broad domain ownership — an
explicit `Execution: Claude-direct` marker grants narrow, commit-specific authorization
only for the exact files in `Files To Modify Or Add`. `validate_commit_spec.py`
validates this planned authorization at spec-validation time; `pre_commit_check.py`
enforces the staged-file authorization at commit time and fails closed. The eventual
commit message must carry `Execution: Claude-direct` + `Commit #NN` so
`pre_commit_check.py` can resolve the exact allowed-file set.

**Approval gate:**

- **Normal mode (no `--auto`):** Do not start work until Eran explicitly approves.
- **Auto mode (`--auto`):** If preflight status is READY and the `violations` array is
  empty and no warning requires a decision, append `[AUTO-APPROVED]` to the card's
  status line and proceed immediately to implementation. Still show the card so Eran
  can see what is being executed. If preflight is BLOCKED or any violation/warning
  exists, show the card normally with `Proceed? [yes/no]` and wait for Eran.

After approval (explicit or auto), follow the full
commit-loop lifecycle (ORCHESTRATION.md §2 STEPS 4-14, §3 circuit breaker):

- Claude-direct: inspect the selected files before editing, then implement only the
  approved files in `Files To Modify Or Add`. Do not activate agent tool-cap state.
- Delegated: rerun the command without `--preview` to activate tool-cap state and
  telemetry, then invoke the named agent with the generated delegation brief verbatim.

Then, regardless of route:

- Run the spec's verification command and perform logic inspection against the commit
  contract — passing tests alone are not sufficient.
- Apply the orchestrator debugging circuit breaker: stop after 2 failed
  repair/verification cycles or 25 orchestrator tool calls, and request Eran's approval
  before continuing.
- Run `/verify-commit`.
- Present changed files, verification results, deviations, warnings, and remaining work
  to Eran.
- Wait for Eran's explicit commit approval. Commit only after approval.
- Advance project state and report the next commit.

Do not duplicate full file contents in an invocation prompt.
