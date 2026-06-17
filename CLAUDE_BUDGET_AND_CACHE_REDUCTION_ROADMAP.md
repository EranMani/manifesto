# Claude Budget and Cache Reduction Roadmap

## Goal

Give Claude-direct and Claude review work the same bounded, observable execution model
as delegated agents, while reducing the instruction context cached on every turn.

## C52A - Live Budget Telemetry

- Track actions, assistant turns, active tokens, and cache-read tokens during a scope.
- Treat active tokens as input + output + cache creation.
- Keep cache reads visible but observational because repeated cache reads are not new
  context growth.

## C52B - Mechanical Enforcement

| Scope | Warn | Stop |
|---|---:|---:|
| Claude direct | 25 actions / 25 turns / 100K active tokens | 40 / 40 / 150K |
| Delegated review | 15 actions / 20 turns / 75K active tokens | 20 / 25 / 100K |

Updated after C55: at the stop threshold, Claude orchestration is advisory-only and
continues with the overage recorded. Product writes after a stop remain blocked unless
Eran explicitly approves a bounded override.

## C52C - Lean Instruction Loading

- Keep `CLAUDE.md` as the short always-loaded operating contract.
- Move explanation and background to `ORCHESTRATION.md`.
- Remove duplicated rules from always-loaded instructions.
- Guard the instruction file with a size regression test.

## Success Measures

- Direct and review scopes cannot silently run without a live budget.
- Hard limits stop additional implementation work mechanically.
- Cache reads are not presented as newly consumed active context.
- `CLAUDE.md` is at least 40% smaller than its 34,798-byte baseline.
