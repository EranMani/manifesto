# /ask-eval — Post-Ask Quality Evaluation

Evaluate the most recent `/ask` response against the ask evaluation
rubric. Read-only — no code changes, no state updates.

Run this immediately after `/ask` completes to evaluate the response
quality. Works for all modes: Q&A, overview, and interview.

---

## Step 1 — Identify What to Evaluate

Look back in the current conversation for the most recent `/ask`
invocation and its response. Extract:

1. **The question**: what was asked
2. **The persona**: which persona was active (default: engineer)
3. **The tier**: which tier was used (quick / standard / deep)
4. **The mode**: Q&A, overview, or interview
5. **The response**: the full answer text

If no recent `/ask` response is found in the conversation, warn:
"No /ask response found in this conversation. Run /ask first, then
/ask-eval immediately after."

---

## Step 2 — Load Persona Rules

1. Read `.claude/persona-profiles.json` to find the persona that was used.
2. Read the matched persona's individual file from `.claude/personas/{name}.json`
   to load the full prompt rules.
3. These rules are the reference standard for Persona Fidelity checks.

---

## Step 3 — Score Each Section

Evaluate 25 binary checks across 5 sections. For each check, determine
Pass or Fail by inspecting the actual response and verifying against the
codebase — not by assuming.

### Section 1 — Persona Fidelity (5 checks)

Read the active persona's `prompt` array and check the response against
each rule:

1. **Language register correct**: engineer uses `file:line` refs and code
   snippets; founder uses plain English with no technical terms; PM uses
   feature/capability language; AI uses pipeline/model terminology;
   frontend uses component/state language; devops uses container/service
   language.
2. **Forbidden content absent**: founder has no code snippets, no file
   paths, no function names; PM has no HTTP methods, no database jargon,
   no enum values; engineer has a confidence rating and Sources section.
3. **Presentation frame used**: correct header format for the persona —
   engineer has `ASK — {summary}` header with route/confidence metadata;
   founder has the header but no metadata; PM has the header with no
   technical metadata.
4. **Follow-ups match persona**: engineer follow-ups are technically
   precise with `file:line` hints; founder follow-ups are plain language;
   PM follow-ups are product-oriented.
5. **Tone consistent throughout**: no mid-answer persona drift — the
   last paragraph follows the same rules as the first. Common failure:
   starting as founder but slipping into technical language when
   explaining implementation details.

### Section 2 — Tier Routing (5 checks)

Assess whether the tier decision was correct and its constraints
were respected:

1. **Tier matches question complexity**: yes/no or single-fact lookup →
   quick; single-concept explanation or enumeration → standard;
   cross-domain, multi-file, or review request → deep. Check by
   asking: "Could this question have been answered at a cheaper tier?"
2. **Tool budget respected**: quick used ≤2 tool calls; standard used
   ≤6 tool calls; deep used ≤15 tool calls (or one agent invocation).
   Count actual tool calls in the response sequence.
3. **Output length proportional**: quick ≤150 words; standard 200-500
   words; deep 500-1500 words. Estimate word count of the answer body
   (excluding headers and metadata).
4. **No over-engineering**: a question that could be answered by reading
   1-2 files was not routed to deep tier with a forge scan and agent
   spawn. The cheapest sufficient tier should have been picked.
5. **Agent use justified** (deep tier only): if an agent was spawned,
   the question genuinely spanned 2+ domains or required 5+ files.
   If no agent was used in deep tier, the direct approach was
   appropriate. Mark Pass if tier is quick or standard (N/A).

### Section 3 — Source Grounding (5 checks)

Verify that claims in the answer are backed by real evidence. This
is the most important section — it catches hallucinated references.

1. **File paths exist**: Glob every file path cited in the answer.
   All must resolve to actual files. Fail if any path is fabricated.
2. **Line references valid**: for the top 2-3 `file:line` references,
   Read the cited file at that line. The code there should be relevant
   to the claim being made. Fail if line numbers point to unrelated
   code or are beyond the file's length.
3. **Function/class names real**: Grep for the top 2-3 function or
   class names cited. They must exist in the cited files. Fail if
   a named symbol doesn't exist.
4. **No fabricated facts**: cross-check the 2 most important factual
   claims against the actual code. Does the function really do what
   the answer says? Does the data really flow the way described?
5. **Confidence rating honest**: if the persona includes a confidence
   rating, verify it matches evidence strength. HIGH = code was read
   directly and claims are grounded. MEDIUM = some inference involved.
   LOW = significant uncertainty. If no confidence rating is required
   by the persona, mark Pass (N/A).

### Section 4 — Answer Quality (5 checks)

Assess whether the answer is complete, well-structured, and accurate:

1. **Question fully addressed**: the core question is answered directly,
   not deflected with "it depends" or partially covered with a promise
   to "look deeper." The user should not need to re-ask.
2. **Bold summary present**: the answer starts with a one-sentence bold
   summary before any detail. All tiers require this.
3. **Structure appropriate**: standard and deep tiers use headers and
   bullets, not wall-of-text. Code snippets are 3-10 lines (not full
   files). Quick tier is concise and direct.
4. **Diagrams used when needed**: questions about flows, architecture,
   or component relationships include ASCII diagrams. Simple factual
   questions do not include unnecessary diagrams.
5. **No hallucinated capabilities**: the answer does not describe
   features, endpoints, models, or behaviors that don't exist in the
   codebase. Check the 1-2 most specific claims about what the system
   "can do" or "supports."

### Section 5 — Actionability (5 checks)

Can the user act on this answer?

1. **Follow-ups relevant**: suggested follow-up questions are natural
   extensions of the answer — they go deeper into the same topic or
   explore adjacent concerns. Not generic questions like "anything
   else you'd like to know?"
2. **Follow-ups runnable**: if follow-ups include `/ask` commands, the
   persona prefixes are valid (match a real alias in persona-profiles.json)
   and the questions are clear.
3. **Forge prompts grounded** (if present): any `/forge` suggestions
   reference real gaps discovered in the answer, not hypothetical
   improvements. If no forge prompts, mark Pass (N/A).
4. **Cross-references useful**: when the answer mentions related
   systems, files, or concepts, these references help the user
   navigate rather than just name-dropping. Each reference should
   connect to the answer's main point.
5. **Next action clear**: after reading the answer, the user knows
   what to do — dig deeper with a follow-up, build something with
   forge, or they have their answer and can move on. The response
   doesn't leave the user uncertain about what to do next.

---

## Step 4 — Mode-Specific Bonus (if applicable)

Score these ONLY when evaluating the corresponding mode. Report
separately from the main 25-check total.

### Overview Bonus (3 checks) — only for `/ask overview`

1. **Attention levels evidence-based**: domains marked "Needs
   Attention" have real evidence (open issues, cold commit activity,
   coverage gaps). Domains marked "Healthy" are genuinely active
   with no outstanding issues. Not all domains are the same level.
2. **Activity heatmap accurate**: the commit activity bars reflect
   actual `git log` history. Run `git log --oneline -15` and verify
   the domain distribution matches what the radar reported.
3. **Recommended action targets real gap**: the suggested next action
   points at the highest-priority real gap, not a generic improvement.
   The `/ask` or `/forge` command is specific and actionable.

### Interview Bonus (3 checks) — only for interview sessions

1. **Challenges codebase-grounded**: non-wildcard challenges reference
   actual code from this repository — real files, real functions, real
   patterns. Verify the top 2 cited references exist.
2. **Difficulty scaled dynamically**: later challenges are harder than
   earlier ones when the user answered well, or simpler when the user
   struggled. Not a static difficulty curve.
3. **Scorecard evidence-backed**: if the session completed (6/6), the
   ratings in the scorecard reference specific answers the user gave.
   Strengths and gaps cite concrete moments, not generic assessments.

---

## Step 5 — Calculate and Present

Present the evaluation as a filled scorecard:

```
ASK EVALUATION — {persona} / {tier}
═══════════════════════════════════════════════════

Question: {the question asked, truncated to ~80 chars}
Persona: {active persona name}
Tier: {quick / standard / deep}
Mode: {Q&A / overview / interview}
Date: {YYYY-MM-DD}

───────────────────────────────────────────────────
Section                    Score   Checks
───────────────────────────────────────────────────
Persona Fidelity           {n}/5   {P/F per check}
Tier Routing               {n}/5   {P/F per check}
Source Grounding            {n}/5   {P/F per check}
Answer Quality             {n}/5   {P/F per check}
Actionability              {n}/5   {P/F per check}
───────────────────────────────────────────────────
TOTAL                      {n}/25  ({percentage}%)

Verdict: {Healthy / Acceptable / Needs Work / Unhealthy}
```

If a mode bonus was evaluated, append:

```
───────────────────────────────────────────────────
{Overview / Interview} Bonus  {n}/3  {P/F per check}
───────────────────────────────────────────────────
```

Then append findings:

```
Failed checks:
  - {section > check: what was wrong and what the evidence showed}
  - {section > check: what was wrong}

What worked well:
  - {specific strength — reference the actual response}

Persona profile adjustments needed:
  - {specific change to a persona file, or "None"}
═══════════════════════════════════════════════════
```

Verdict thresholds:
- 21-25 (84-100%): **Healthy**
- 17-20 (68-83%): **Acceptable**
- 13-16 (52-67%): **Needs Work**
- Below 13 (<52%): **Unhealthy**

---

## Step 6 — Save Evaluation

Write the completed scorecard to `.ask/evaluations/eval-{date}-{persona}-{tier}.md`.
Create the `.ask/evaluations/` directory if it doesn't exist.

Use the naming convention: `eval-2026-06-20-engineer-standard.md`

If previous evaluations exist in `.ask/evaluations/`, show a one-line
trend:

```
Trend: eval-...-engineer-quick (92%) → eval-...-pm-standard (80%) → this run ({n}%)
```

---

## Constraints

- Read-only except for writing the evaluation file.
- Do not modify the original `/ask` response or any persona files
  based on the evaluation.
- Source grounding checks (Section 3) require real verification —
  actually Glob the paths, Read the lines, Grep the symbols. Do not
  assess source grounding from memory alone.
- If a check cannot be assessed (e.g., no confidence rating for a
  persona that doesn't require one), mark as Pass with note "N/A."
- Be honest. A perfect score on a flawed answer is worse than a low
  score that catches real issues. The point is to improve the ask
  pipeline, not to generate passing grades.
