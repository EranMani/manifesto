# Forge Evaluation Rubric

Post-run evaluation for `/forge` and delegated agent execution. Complete
this after every forge run to validate whether agents used the stack
profile effectively and produced quality output.

---

## How to Use

After a `/forge` run completes, copy the scorecard template below and
fill it in. Store completed scorecards in `.forge/evaluations/` with the
naming convention `eval-CXX-CYY.md` (covering the commit range produced).

The rubric has 6 sections. Each check is binary (Pass/Fail). A forge run
must score **80%+ overall** to be considered healthy. Below 60% indicates
a systemic issue in the stack profile or agent configuration.

---

## Scorecard Template

```markdown
# Forge Evaluation: C{XX}-C{YY}

Date: YYYY-MM-DD
Task: {one-line task description}
Scope: {XS / S / M / L}
Agents invoked: {list of agents that participated}

## 1. Stack Alignment (did agents use the right technologies?)

| Check | Pass/Fail | Notes |
|-------|-----------|-------|
| Agent recommended technologies from stack profile, not alternatives | | |
| No non-standard libraries introduced without justification | | |
| Patterns match domain file (service layer, repository, etc.) | | |
| Database patterns followed (migrations, soft-delete, timestamps) | | |
| Frontend patterns followed (shadcn, Tailwind, Zustand) if applicable | | |

Score: _/5

## 2. Context Efficiency (did agents load the right amount of context?)

| Check | Pass/Fail | Notes |
|-------|-----------|-------|
| Agent read only its domain file, not unrelated domain files | | |
| Agent did not re-discover stack choices already in the profile | | |
| No evidence of instruction atrophy (late-turn rule neglect) | | |
| Agent stayed within tool budget for the task scope | | |
| Shared.json loaded only when a cross-cutting concern was relevant | | |

Score: _/5

## 3. Design Quality (did the plan match the engineering methodology?)

| Check | Pass/Fail | Notes |
|-------|-----------|-------|
| Data flow between components is explicit and typed | | |
| Failure modes identified (what happens when X fails?) | | |
| Deterministic logic used where possible (not over-relying on LLM) | | |
| Pipeline stages are decoupled (ingestion failure ≠ processing failure) | | |
| Commit decomposition follows atomic behavior rule | | |

Score: _/5

## 4. Specification Quality (are the generated specs buildable?)

| Check | Pass/Fail | Notes |
|-------|-----------|-------|
| All 14 required sections present and non-empty | | |
| Verification command is specific and runnable (not generic) | | |
| File list matches the actual scope (no missing/extra files) | | |
| Contract section defines inputs, outputs, defaults, failure behavior | | |
| Test plan covers happy path, boundary, and at least one edge case | | |

Score: _/5

## 5. Security and Validation (did Sage's concerns get addressed?)

| Check | Pass/Fail | Notes |
|-------|-----------|-------|
| User input validated at API boundary (Pydantic BaseModel, not dataclass) | | |
| Auth/permission checks included where endpoints are role-gated | | |
| No secrets hardcoded (API keys, passwords in code or config) | | |
| AI outputs validated before reaching users (structured outputs) | | |
| Webhook payloads verified → persisted → async dispatched (if applicable) | | |

Score: _/5

## 6. Product Alignment (does the plan solve the right problem?)

| Check | Pass/Fail | Notes |
|-------|-----------|-------|
| The task addresses a real user need, not an engineering preference | | |
| Scope is bounded — the spec explicitly lists what is NOT included | | |
| Success criteria are measurable (not "improve the system") | | |
| Human escalation path defined for AI-powered features | | |
| The plan would survive the "turn it off" test — someone would notice | | |

Score: _/5

## Summary

| Section | Score | Max |
|---------|-------|-----|
| Stack Alignment | | 5 |
| Context Efficiency | | 5 |
| Design Quality | | 5 |
| Specification Quality | | 5 |
| Security and Validation | | 5 |
| Product Alignment | | 5 |
| **Total** | | **30** |

Overall: _{total}/30 ({percentage}%)_

## Observations

### What worked well
- {specific strength — reference the agent and decision}

### What needs improvement
- {specific issue — what happened, why, and what to change in the stack profile or agent config}

### Stack profile adjustments needed
- {specific change to a domain file, or "none"}

### Follow-up actions
- [ ] {action item — e.g., "add missing pattern to backend.json", "file was not in agent domain map"}
```

---

## Evaluation Guidelines

### Scoring

- **Pass**: The check is clearly satisfied — evidence visible in the
  forge output, specs, or agent behavior.
- **Fail**: The check is not satisfied, or the evidence is ambiguous.
  Add a note explaining what happened.

### Thresholds

| Score | Verdict | Action |
|-------|---------|--------|
| 25-30 (83-100%) | **Healthy** | No action needed. Record observations for trend tracking. |
| 20-24 (67-82%) | **Acceptable** | Minor issues. Fix specific gaps in stack profile or agent config. |
| 15-19 (50-66%) | **Needs work** | Systemic issues. Review which domain files need enrichment or restructuring. |
| Below 15 (<50%) | **Unhealthy** | Fundamental problem. The agents are not reading or following the stack profile. Investigate root cause. |

### What to look for per section

**Stack Alignment** — Did the agent recommend FastAPI when the profile
says FastAPI, or did it suggest Flask? Did it use SQLAlchemy or suggest
a different ORM? Technology drift is the earliest signal of profile
neglect.

**Context Efficiency** — Did Nova load `ai-rag.json` for a task that
had nothing to do with retrieval? Did Rex re-discover that the project
uses PostgreSQL by reading config files instead of the profile? Token
waste compounds across the commit sequence.

**Design Quality** — Did the plan address failure modes, or only the
happy path? Did it default to "use LLM for everything" or properly
separate deterministic and generative logic? This section tests the
engineering methodology absorption.

**Specification Quality** — Can a developer (human or AI) pick up the
spec and implement it without asking questions? Missing contracts,
vague verification commands, or wrong file lists mean the spec isn't
buildable.

**Security and Validation** — Did the plan include Pydantic validation
at API boundaries? Did it mention auth checks for protected endpoints?
Security gaps in specs become security gaps in code.

**Product Alignment** — Is this solving a real user problem or is it
engineering busywork? Would anyone notice if this feature didn't exist?
This tests whether the product strategy section of the stack profile
is influencing decisions.

---

## Trend Tracking

After multiple evaluations, look for patterns:

- **Same section consistently low**: the corresponding domain file needs
  enrichment or the agent isn't reading it.
- **Context Efficiency declining**: agents are loading more context over
  time — check for scope creep in the domain files.
- **Stack Alignment dropping**: new technologies creeping in without
  profile updates — either update the profile or enforce the constraint.
- **Product Alignment consistently high but Design Quality low**: the
  team knows WHAT to build but not HOW — engineering methodology needs
  reinforcement.

Store evaluations in `.forge/evaluations/` for historical reference.
Review trends every 10 forge runs.
