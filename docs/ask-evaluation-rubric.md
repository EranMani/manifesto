# Ask Evaluation Rubric

Post-response evaluation for `/ask` across all modes (Q&A, overview,
interview). Complete this after an `/ask` response to validate persona
fidelity, source grounding, and answer quality.

---

## How to Use

After an `/ask` response, run `/ask-eval` or manually fill the scorecard
below. Store completed scorecards in `.ask/evaluations/` with the naming
convention `eval-{date}-{persona}-{tier}.md`.

The rubric has 5 core sections (25 checks) plus optional bonus sections
for overview and interview modes. Each check is binary (Pass/Fail). An
ask response must score **84%+ overall** (21/25) to be considered
healthy. Below 52% indicates a systemic issue in the persona profile or
ask pipeline logic.

---

## Scorecard Template

```markdown
# Ask Evaluation: {persona} / {tier}

Date: YYYY-MM-DD
Question: {the question asked}
Persona: {active persona name}
Tier: {quick / standard / deep}
Mode: {Q&A / overview / interview}

## 1. Persona Fidelity (did the answer follow the persona's rules?)

| Check | Pass/Fail | Notes |
|-------|-----------|-------|
| Language register matches persona (engineer=technical, founder=plain, PM=product) | | |
| Forbidden content absent (founder=no code, PM=no jargon, engineer=has confidence) | | |
| Correct presentation frame used (header format, metadata, Sources section) | | |
| Follow-up suggestions match persona language and depth | | |
| Tone consistent from first to last paragraph — no persona drift | | |

Score: _/5

## 2. Tier Routing (was the right tier picked and respected?)

| Check | Pass/Fail | Notes |
|-------|-----------|-------|
| Tier matches question complexity (cheapest sufficient tier) | | |
| Tool budget respected (quick ≤2, standard ≤6, deep ≤15) | | |
| Output length proportional (quick ≤150w, standard 200-500w, deep 500-1500w) | | |
| No over-engineering (simple question not routed to deep) | | |
| Agent use justified — deep only; N/A for quick/standard | | |

Score: _/5

## 3. Source Grounding (are claims backed by real code?)

| Check | Pass/Fail | Notes |
|-------|-----------|-------|
| Every file path cited exists in the repo (Glob verified) | | |
| Top 2-3 file:line references point to relevant code (Read verified) | | |
| Named functions/classes exist in cited files (Grep verified) | | |
| Top 2 factual claims match actual code behavior | | |
| Confidence rating (if required) matches evidence strength | | |

Score: _/5

## 4. Answer Quality (is the answer complete and well-structured?)

| Check | Pass/Fail | Notes |
|-------|-----------|-------|
| Core question fully addressed — not deflected or partial | | |
| Bold one-sentence summary at the start | | |
| Structure appropriate — headers/bullets for standard+, concise for quick | | |
| ASCII diagrams present for flow/architecture questions, absent for simple lookups | | |
| No hallucinated capabilities — everything described actually exists | | |

Score: _/5

## 5. Actionability (can the user act on this answer?)

| Check | Pass/Fail | Notes |
|-------|-----------|-------|
| Follow-up questions are natural extensions, not generic | | |
| Follow-up /ask commands use valid persona prefixes | | |
| Forge prompts (if any) reference real gaps, not hypothetical improvements | | |
| Cross-references help navigation, not just name-dropping | | |
| Next action is clear — user knows what to do after reading | | |

Score: _/5

## Overview Bonus (only for /ask overview — not counted in total)

| Check | Pass/Fail | Notes |
|-------|-----------|-------|
| Attention levels match real evidence (issues, activity, gaps) | | |
| Activity heatmap reflects actual git log history | | |
| Recommended action targets the highest-priority real gap | | |

Bonus: _/3

## Interview Bonus (only for interview sessions — not counted in total)

| Check | Pass/Fail | Notes |
|-------|-----------|-------|
| Non-wildcard challenges reference real code from this repo | | |
| Difficulty scaled dynamically based on user answers | | |
| Scorecard ratings cite specific moments from the session | | |

Bonus: _/3

## Summary

| Section | Score | Max |
|---------|-------|-----|
| Persona Fidelity | | 5 |
| Tier Routing | | 5 |
| Source Grounding | | 5 |
| Answer Quality | | 5 |
| Actionability | | 5 |
| **Total** | | **25** |

Overall: _{total}/25 ({percentage}%)_

{If applicable: Overview Bonus: _/3 or Interview Bonus: _/3}

## Observations

### What worked well
- {specific strength — reference the actual response}

### What needs improvement
- {specific issue — what happened, why, and what to change}

### Persona profile adjustments needed
- {specific change to a persona file, or "none"}

### Follow-up actions
- [ ] {action item — e.g., "tighten founder persona rule on technical terms"}
```

---

## Evaluation Guidelines

### Scoring

- **Pass**: The check is clearly satisfied — evidence visible in the
  response text or verified against the codebase.
- **Fail**: The check is not satisfied, or the evidence is ambiguous.
  Add a note explaining what happened.

### Thresholds

| Score | Verdict | Action |
|-------|---------|--------|
| 21-25 (84-100%) | **Healthy** | No action needed. Record observations for trend tracking. |
| 17-20 (68-83%) | **Acceptable** | Minor issues. Fix specific gaps in persona profiles or ask command logic. |
| 13-16 (52-67%) | **Needs work** | Systemic issues. Review which persona rules are being ignored or which tier logic needs adjustment. |
| Below 13 (<52%) | **Unhealthy** | Fundamental problem. The ask pipeline is not following persona rules or is fabricating references. Investigate root cause. |

### What to look for per section

**Persona Fidelity** — Did the founder answer include code snippets?
Did the engineer answer lack a Sources section? Did the PM answer use
database column names instead of product language? Persona drift is the
most common failure — the answer starts in character but slips into
default engineer mode by the third paragraph.

**Tier Routing** — Was a simple "where is X defined?" question routed
to standard tier with 4 tool calls and 400 words? Was a cross-domain
architecture question squeezed into quick tier with an incomplete
answer? The cheapest sufficient tier is always correct.

**Source Grounding** — This is the highest-stakes section. A fabricated
`file:line` reference that the user follows wastes their time and erodes
trust. Always verify the top 2-3 references against the actual codebase.
Common failures: file exists but line number is wrong, function name is
close but misspelled, file was renamed since the forge scan.

**Answer Quality** — Did the answer actually address the question, or
did it meander into related topics? Is there a clear summary sentence
at the top? For architecture questions, is there a diagram? For simple
lookups, is the answer concise? Structure should match tier — quick
answers shouldn't have three headers and a diagram.

**Actionability** — After reading the answer, does the user know what
to do next? Are the follow-up questions interesting enough to click?
Do the `/ask` and `/forge` commands actually work if pasted? A good
answer ends with momentum, not a dead end.

---

## Trend Tracking

After multiple evaluations, look for patterns:

- **Persona Fidelity consistently low for one persona**: that persona's
  prompt rules need strengthening or the ask pipeline has a bug in
  persona loading.
- **Source Grounding failing**: the ask pipeline is citing files from
  memory instead of reading them. Check if the tier is too aggressive
  (quick when standard is needed) or if the forge scan is stale.
- **Tier Routing over-engineering**: if most questions are routed to
  standard or deep when quick would suffice, the tier classification
  rules need tightening.
- **Actionability low across personas**: follow-up generation logic
  needs improvement — likely generating generic questions instead of
  building on the answer content.
- **One persona consistently perfect, others struggling**: the
  well-performing persona's prompt may have clearer rules — study it
  and apply the same specificity to others.

Store evaluations in `.ask/evaluations/` for historical reference.
Review trends every 10 ask-eval runs.
