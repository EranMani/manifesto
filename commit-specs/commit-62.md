# Commit 62 - `assembled-client-demo` - Adam

**Phase:** Client demo verification
**Owner:** adam
**Depends on:** C61
**Estimated diff lines:** 300
**Primary behavior count:** 1
**Developer test milestone:** yes

## Primary Behavior
Verify and document the complete client demonstration from a clean environment.

## Semantic Fit Review
- **Atomic outcome:** One reproducible command proves the assembled product story.
- **Failure boundary:** Product hardening after external feedback is later work.
- **Budget rationale:** One smoke script and result/runbook document fit two files.

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

## Context
```yaml
primary_files:
  - scripts/smoke_client_demo.ps1
  - SMOKE_TEST_RESULTS.md
initial_context:
  - docker-compose.yml
  - scripts/test_backend.ps1
  - SMOKE_TEST_RESULTS.md
  - backend/tests/services/fixtures/assistant_golden.json
  - README.md
forbidden:
  - backend/app/
  - frontend/src/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `scripts/smoke_client_demo.ps1` | add | Start clean services, migrate, seed, verify APIs, and build frontend. |
| `SMOKE_TEST_RESULTS.md` | edit | Record exact rehearsal steps, expected results, and limitations. |

## Contract
The script starts the stack, applies migrations, runs the seed twice, verifies stable
counts, authenticates manager and employee users, exercises logistics/policy/denial/
fallback API cases, runs C61, and builds the frontend. It fails nonzero on any step and
prints the exact manual `/assistant` rehearsal prompts.

## Environment Prerequisites
- OpenAI credentials are configured; deterministic fallback is also testable.
- C61 golden suite passes.

## Verification Command
```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_client_demo.ps1
```

## Focused Tests
- Clean setup and repeated seed succeed.
- Role access, evidence, fallback, golden suite, and frontend build pass.

## Done When
- [ ] **Ready now:** Complete client demonstration from clean setup.
- [ ] **How to test:** Run the smoke script, then follow the browser rehearsal in `SMOKE_TEST_RESULTS.md`.
- [ ] **Expected result:** Manager logistics graph, employee policy citations, denial, and fallback all work.
- [ ] **Still incomplete:** Only failures observed in external demos drive subsequent hardening.

## Developer Test Checkpoint
**Ready now:** Client-ready prototype.
**How to test:** Run the exact verification command and browser rehearsal.
**Expected result:** The complete product story succeeds without manual database preparation.
**Still incomplete:** Production hardening and external integrations remain deferred.

## Not In This Commit
- New product behavior or speculative hardening.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
