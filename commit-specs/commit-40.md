# Commit 40 - `product-delivery-replan` - Claude

**Phase:** Product delivery reset
**Owner:** claude
**Depends on:** C39
**Estimated diff lines:** 320
**Primary behavior count:** 1
**Developer test milestone:** yes

---

## Primary Behavior

Replace the policy-first pending roadmap with the approved milestone-led delivery plan.

---

## Semantic Fit Review

- **Atomic outcome:** The canonical protocol points to one bounded, client-demo roadmap.
- **Failure boundary:** Product implementation and later commit-spec activation remain outside C40.
- **Budget rationale:** Four planning/state files and one structural validation command fit the locked envelope.

---

## Execution Budget

```yaml
execution_budget:
  max_primary_files: 2
  max_changed_files: 4
  max_context_files: 6
  max_context_chars: 15000
  max_estimated_diff_lines: 350
  max_agent_invocations: 1
  max_tool_calls: 18
  max_expansions: 2
  max_implementor_tokens: 45000
```

---

## Context

```yaml
primary_files:
  - commit-protocol.md
  - commit-specs/PRODUCT_DELIVERY_PLANNING.md
initial_context:
  - commit-protocol.md
  - project-state.json
  - commit-specs/commit-40.md
  - commit-specs/TEMPLATE.md
forbidden:
  - backend/
  - frontend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `commit-protocol.md` | edit | Activate C40 and record planned C41-C62 milestones. |
| `commit-specs/PRODUCT_DELIVERY_PLANNING.md` | add | Preserve the reusable planning method and Manifesto example. |
| `commit-specs/commit-40.md` | edit | Define the bounded roadmap-reset contract. |
| `project-state.json` | edit | Point project state at the approved C40 replan. |

---

## Contract

Only C40 is pending. C41-C62 are listed as planned and become pending only after their
focused specs are drafted and validated. The protocol records checkpoints at C46, C50,
C56, C60, and C62 plus the deferred policy-chat backlog.

---

## Environment Prerequisites

- C39 is complete and Eran approved the fast-delivery replan.

---

## Verification Command

```powershell
python hooks/validate_commit_spec.py --all-pending --json
```

---

## Focused Tests

- C40 is the only active pending spec and passes structural validation.
- C41-C62 remain visible as planned work without entering pending validation.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Ready now:** The approved product milestones, atomic delivery sequence, and reusable
planning method are canonical.
**How to test:** Read the Commit Index, Developer Test Milestones, deferred backlog, and
`commit-specs/PRODUCT_DELIVERY_PLANNING.md`; run the verification command.
**Expected result:** The pending graph is valid with C40 as its only pending commit.
**Still incomplete:** No product implementation begins until C41 is separately specified
and approved.

---

## Not In This Commit

- Product code, migrations, seeds, APIs, UI, and C41-C62 detailed specifications.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
