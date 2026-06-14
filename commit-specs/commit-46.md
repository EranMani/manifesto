# Commit 46 - `bundled-policy-seed` - Rex

**Phase:** Demo data foundation
**Owner:** rex
**Depends on:** C45
**Estimated diff lines:** 300
**Primary behavior count:** 1
**Developer test milestone:** yes

## Primary Behavior
Preload a bundled mock policy corpus into query-ready policy documents and chunks.

## Semantic Fit Review
- **Atomic outcome:** Fresh demo setup includes immediately searchable policies.
- **Failure boundary:** Online policy retrieval remains C51.
- **Budget rationale:** One bundle, seed integration, and focused test fit three files.

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
  - backend/app/data/demo_policies.json
  - backend/seed.py
initial_context:
  - backend/seed.py
  - backend/app/models/policy.py
  - backend/app/services/ingestion.py
  - backend/tests/test_seed.py
forbidden:
  - frontend/
  - backend/app/api/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/data/demo_policies.json` | add | Hold curated mock policy titles and sections. |
| `backend/seed.py` | edit | Insert deterministic ready documents and chunks. |
| `backend/tests/test_seed.py` | edit | Verify policy coverage, provenance, and idempotency. |

## Contract
Bundle procurement approvals, shipment delays, damaged goods, partial delivery, returns,
lost shipments, and employee escalation policies. Seed deterministic ready documents and
chunks with source title, section, chunk index, active embedding profile, and embeddings
obtained through the configured `EmbeddingService`; skip unchanged ready documents.

## Environment Prerequisites
- Embedding provider is reachable and C45 scenarios exist.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/test_seed.py -k bundled_policy -q
```

## Focused Tests
- All required policy topics are present and ready.
- Chunks preserve title/section provenance.
- Repeated preload creates no duplicate profile/checksum rows.

## Done When
- [ ] Automated verification passes.
- [ ] **Ready now:** Stable mock procurement data and query-ready policy documents.
- [ ] **How to test:** Run migrations and `uv run python seed.py`, then query counts/statuses in PostgreSQL.
- [ ] **Expected result:** 50 shipments with all outcome classes and all bundled policies in `ready`.
- [ ] **Still incomplete:** No assistant retrieval or browser experience.

## Developer Test Checkpoint
**Ready now:** Stable mock procurement data and query-ready policy documents.
**How to test:** Run the seed twice and inspect shipment outcome counts plus ready policy titles.
**Expected result:** Counts remain stable and every required logistics/policy scenario is present.
**Still incomplete:** Retrieval starts at C47.

## Not In This Commit
- Policy answering or logistics retrieval.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
