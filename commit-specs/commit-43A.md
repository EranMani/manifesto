# Commit 43A - `shipment-lifecycle-migration-downgrade-fix` - Rex

**Phase:** Demo data foundation
**Owner:** rex
**Depends on:** C43
**Execution mode:** Claude-direct
**Estimated diff lines:** 5
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

`test_shipment_lifecycle.py`'s migration upgrade/downgrade test downgrades to an
explicit revision so it still removes the 0004 lifecycle columns, regardless of how
many migrations now sit above `0004_shipment_lifecycle_fields`.

---

## Semantic Fit Review

- **Atomic outcome:** One test assertion's downgrade target is corrected; no production
  code changes.
- **Failure boundary:** No change to migration files, models, or schemas.
- **Budget rationale:** 1-line change to 1 file; tiny, mechanical, letter-suffix repair
  commit (C33A/C38A/C42A precedent).

---

## Background

C43 added `0005_shipment_event_storage.py`, moving the alembic head past
`0004_shipment_lifecycle_fields`.
`test_shipment_lifecycle.py::test_migration_upgrade_adds_lifecycle_columns_and_downgrade_removes_them`
calls `command.upgrade(cfg, "head")` then `command.downgrade(cfg, "-1")`, expecting the
0004 lifecycle columns (`tracking_code`, `purchase_order_id`, `actual_arrival_at`, etc.)
to be gone afterward. With 0005 now on top, `-1` only undoes 0005, landing on 0004 —
those columns are still present, so `assert "tracking_code" not in columns` fails
(152/153 full suite after C43).

`validate_commit_spec.py` hard-locks `max_changed_files` at 4 (not overridable in the
spec), so this 1-line fix could not be folded into C43's 4-file budget and was queued
as this letter-suffix commit instead.

---

## Execution Budget

```yaml
execution_budget:
  max_primary_files: 1
  max_changed_files: 1
  max_context_files: 2
  max_context_chars: 6000
  max_estimated_diff_lines: 20
  max_agent_invocations: 1
  max_tool_calls: 18
  max_expansions: 2
  max_implementor_tokens: 45000
```

---

## Context

```yaml
primary_files:
  - backend/tests/models/test_shipment_lifecycle.py
initial_context:
  - backend/tests/models/test_shipment_lifecycle.py
  - backend/alembic/versions/0005_shipment_event_storage.py
forbidden:
  - frontend/
  - backend/app/
  - backend/alembic/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/tests/models/test_shipment_lifecycle.py` | edit | Change the downgrade target in `test_migration_upgrade_adds_lifecycle_columns_and_downgrade_removes_them` from `"-1"` to the explicit revision `"0003_purchase_order_storage"`, so the downgrade always removes both `0005` and `0004` (and thus the lifecycle columns), regardless of how many migrations sit above `0004`. |

---

## Contract

In `test_migration_upgrade_adds_lifecycle_columns_and_downgrade_removes_them`, replace:

```python
command.downgrade(cfg, "-1")
```

with:

```python
command.downgrade(cfg, "0003_purchase_order_storage")
```

No other lines change. The subsequent `command.upgrade(cfg, "head")` and assertions
are unchanged.

---

## Environment Prerequisites

- C43 (`0005_shipment_event_storage`) is migrated.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest -q
```

---

## Focused Tests

- `test_migration_upgrade_adds_lifecycle_columns_and_downgrade_removes_them` passes:
  after `command.downgrade(cfg, "0003_purchase_order_storage")`, `tracking_code` and
  `actual_arrival_at` are absent and `arrived_at` is present again; after re-upgrading
  to `head`, `tracking_code` and `actual_arrival_at` are present again.
- Full backend suite returns to 153/153.

---

## Done When

- [ ] `test_shipment_lifecycle.py`'s downgrade target is `"0003_purchase_order_storage"`.
- [ ] Full suite passes 153/153.
- [ ] No files outside `backend/tests/models/test_shipment_lifecycle.py` changed.

---

## Developer Test Checkpoint

**Next milestone:** C46 demo data ready.

---

## Not In This Commit

- C44 (`procurement-foundation-seed`, rex) — proceeds after this commit.
- Any change to migration files, models, or schemas.

---

## Return Contract

Claude-direct: report the diff and the full-suite test run output (153/153).
