# /ask — Codebase Q&A

Parse `$ARGUMENTS` for a persona prefix and a question. Read-only — no code
changes, no commit protocol updates.

---

## Phase 0 — Persona Selection

Check the first word of `$ARGUMENTS` against these known persona prefixes:
`founder`, `nontechnical`, `plain`, `simple`, `pm`, `product`,
`product-manager`, `engineer`, `eng`, `dev`, `senior`, `technical`,
`ai`, `ml`, `nova`, `frontend`, `fe`, `ui`, `react`, `aria`,
`devops`, `infra`, `ops`, `docker`, `adam`,
`interviewer-founder`, `interview-founder`, `if`, `interviewer-pm`,
`interview-pm`, `ip`, `interviewer-eng`, `interview-eng`, `ie`,
`interviewer-ai`, `interview-ai`, `ia`, `interviewer-devops`,
`interview-devops`, `id`.

**Overview path** — if the first word (after optional persona prefix
stripping) is `overview` or `ov`:
- Skip to **Phase 0.7 — Overview Radar**. This short-circuits the
  entire Q&A pipeline.
- If a persona prefix was provided before `overview`, use that persona's
  language rules for the output. Otherwise use the default engineer persona.

**Readiness path** — if the first word (after optional persona prefix
stripping) is `readiness` or `ready`:
- Skip to **Phase 0.8 — Readiness Assessment**. This short-circuits
  the entire Q&A pipeline.
- If a persona prefix was provided before `readiness`, use that persona's
  language rules. Otherwise use the default engineer persona.

**Fast path** — if the first word does NOT match any prefix AND the
remaining text is not `questions`, `q`, `overview`, `ov`, `readiness`,
or `ready`:
- Use the default engineer persona behavior (full technical detail,
  `file:line` references, code snippets, ASCII diagrams, Sources section,
  confidence rating).
- Do NOT read `persona-profiles.json`. Skip to Phase 1.
- This saves ~1-2k tokens on the most common invocation pattern.

**Persona path** — if the first word matches a prefix OR the text is
`questions`/`q`:
1. Read `.claude/persona-profiles.json` (slim index — aliases and file pointers only).
2. Match the prefix to a persona entry via its `aliases` array.
3. Read the matched persona's individual file (e.g., `.claude/personas/engineer.json`)
   to load the full prompt, questions, and templates.
4. Set the matching persona as active, strip the prefix from arguments.
5. If no prefix match but `questions`/`q` is present, check auto-memory
   for a stored role preference, then fall back to the `default` key.

**Apply throughout.** The active persona's `prompt` field overrides the
answer formatting rules. Every answer must conform to the active persona's
language, structure, and inclusion/exclusion rules.

If `$ARGUMENTS` (after stripping any persona prefix) is empty, ask: "What
would you like to know about the codebase?"

---

## Phase 0.5 — Question Bank (triggered by `questions` or `q` keyword)

If the remaining question (after persona stripping) is exactly `questions`
or `q`, show the question bank instead of answering a question. This
short-circuits the rest of the pipeline.

**Language rule**: all generated text in the question bank — questions,
descriptions, status labels, domain names, and forge prompts — MUST
follow the active persona's language rules. For founder persona: no
technical terms, no file paths, no domain labels like "backend" or
"frontend" (use "the core system" and "the user-facing interface"
instead). For PM persona: use product vocabulary, no engineering jargon.
This rule applies to every step below.

The question bank executes in two parts: FIRST generate and render
questions as plain numbered text (mandatory), THEN optionally append
build suggestions below (optional).

### Part A — Generate questions (mandatory, do this FIRST)

**A1. Load evergreen questions.**
Read the active persona's `questions.evergreen` array from the persona's
individual file (e.g., `.claude/personas/engineer.json`). Copy all of
them into a working list. These are your safety net — they guarantee
the question bank is never empty.

**A2. Generate contextual questions.**
Read three data sources and generate persona-appropriate questions. Each
source produces 1-2 questions using the `questions.contextual_templates`
from the active persona profile.

**Source A — Codebase structure** (`.forge/report.json`, reuse if exists):
- Pick the top 2 hub files by `in_degree`.
- Map each hub to a product area name:
  - `database.py` → "the database layer"
  - `rag_logistics.py` → "logistics / AI search"
  - `security.py` → "the login and permissions system"
  - `user.py` → "user management"
  - Other hubs → use the parent directory or file stem as the area name
- Generate 1-2 questions using the `hub_file` template, substituting the
  area name (not the file path — keep it persona-appropriate).

**Source B — Project state** (`project-state.json`):
- Read `open_issues`. If any exist, generate 1 question using the
  `open_issue` template.
  - For engineer persona, substitute the specific issue ID.
  - For founder/PM persona, keep it general.
- If `open_issues` is empty, skip.

**Source C — Recent changes** (`git log --oneline -5`):
- Parse the commit subjects to identify the most recently touched area.
- Generate 1 question using the `recent_change` template.

**A3. Assemble and deduplicate.**
Combine evergreen + contextual questions. Remove near-duplicates. Keep
contextual over evergreen when they overlap. Target: 6-8 total questions.

**Hard rule**: the final list MUST contain at least 5 questions. If
contextual generation produced too few, keep more evergreen questions.
Never present fewer than 5 questions.

**A4. Render questions as plain text — THIS IS THE PRIMARY OUTPUT.**

Self-check before outputting: count your questions. If you have fewer
than 5, add more from the evergreen list. If you have zero contextual
questions, use ALL evergreen questions as-is. The persona's evergreen
list always has 5 — that alone satisfies the minimum.

Split into two groups and render as plain numbered text:

```
QUESTIONS — {persona name}
───────────────────────────────────────────────────────

Start here:
  1. {overview question}
  2. {overview question}
  3. {overview question}

Go deeper:
  4. {specific contextual question}
  5. {specific contextual question}
  6. {contextual question}
  7. {contextual question}

───────────────────────────────────────────────────────
Type a number to explore that question, or ask your own.
```

This plain-text format is the guaranteed output. It works in all modes
(interactive, `claude -p`, Codex). If AskUserQuestion is available and
the session is interactive, you MAY additionally use it to present the
questions as selectable options — but the plain text above must always
be rendered regardless.

### Part B — Append build prompts (optional, do this AFTER Part A)

Only after the questions from Part A have been rendered, append build
prompts below them.

**B1. Generate forge prompts.**
Using the **same contextual data** already gathered in A2 (hub files,
project state, recent changes), generate 2-3 forge-ready prompts using
the active persona's `forge_templates` from the persona's individual file.

**How to generate each prompt:**

1. For each gap, issue, or opportunity identified in A2, pick the
   matching `forge_templates` key (`hub_file`, `open_issue`,
   `recent_change`, or `domain_gap`).
2. Fill the template placeholders with **concrete values** from the
   codebase data — not generic descriptions. Every placeholder must
   resolve to something real:
   - `{area}` → "shipment management", not "the system"
   - `{user_role}` → "warehouse manager", not "user"
   - `{missing_capability}` → "edit shipments after creation", not "missing features"
   - `{issue_id}` → "OI-24", not "the issue"
   - `{file}` → "backend/app/api/v1/shipments.py", not "the file"
3. Prepend `/forge` to each completed prompt so it's directly pasteable.
4. Keep each prompt to one sentence — forge handles decomposition.
5. **Stale issue check**: before suggesting a fix for an open issue,
   grep for existing test files or recent commits that may have already
   addressed it. If evidence of a fix exists, skip that issue.

**Rules:**
- If no `forge_templates` key exists for the persona (e.g., interviewer
  personas), skip Part B entirely.
- Never generate forge prompts for things that are already built.
- Prioritize gaps over improvements — missing features before polish.
- Each prompt must describe a **different** gap or opportunity.

**B2. Present build prompts.**
Render as a labeled text block AFTER the questions from Part A.
Build prompts are supplementary — they must never appear without
questions above them.

For non-technical personas (founder, PM), present as plain-language
action descriptions, not raw `/forge` commands:

```
WHAT TO BUILD NEXT:

  1. {plain-language description of the action and why it matters}
  2. {plain-language description}
  3. {plain-language description}

To start building any of these, tell me which one interests you.
```

For technical personas, use the standard forge-prompt format:

```
BUILD NEXT — paste any of these into the chat to start planning:

  /forge {prompt 1}
  /forge {prompt 2}
  /forge {prompt 3}
```

If B1 produced no forge prompts, omit the build prompt section entirely.

### Part C — Run the selected question

When the user types a number or selects a question, carry the active
persona forward and execute through the pipeline starting at Phase 1.

---

## Phase 0.7 — Overview Radar (triggered by `overview` or `ov` keyword)

If the remaining text (after persona stripping) starts with `overview` or
`ov`, produce a cross-domain attention radar instead of answering a
question. This short-circuits the rest of the pipeline.

**Purpose:** Tell the user which hat needs attention right now — surface
gaps, imbalances, and risks they wouldn't know to ask about.

**Budget**: ≤12 tool calls. No agents.

**Language rule**: all generated text in the overview radar MUST follow
the active persona's language rules. This includes domain labels, status
descriptions, commit counts, and suggested actions. Specific translations
for non-technical personas:
- "commits" → "internal development changes" (not "shipped" unless deployed)
- "backend" → "the core system"
- "frontend" → "the user-facing interface"
- "AI/ML" → "the smart features" or "the AI assistant"
- "DevOps" → "the hosting and automation setup"
- "test coverage" → "protection against things breaking"
- "open issues" → "known problems"
- "unactioned handoffs" → "pending items waiting for follow-up"
For technical personas, use standard domain terminology.

### Step 1 — Gather signals

Read these data sources in parallel (skip any that don't exist):

**Source A — Codebase structure** (`.forge/report.json`):
- Read `category_summary` for file counts per domain.
- Read hub files (top 3 by `in_degree`) to identify coupling hotspots.
- Note any domain with zero files or disproportionately few files.

**Source B — Project state** (`project-state.json`):
- Read `open_issues` — count by priority, note unresolved ones.
- Read `open_handoffs` — count unactioned handoffs.
- Read `blockers` — any active blockers.
- Read `tldr` and `next_commit` for current momentum.

**Source C — Recent activity** (`git log --oneline -15`):
- Parse commit subjects to count activity per domain (backend, frontend,
  ai, devops, docs, workflow).
- Identify domains with zero recent commits (cold domains).
- Identify domains with heavy recent activity (hot domains).

**Source D — Coverage gaps** (targeted greps, max 4):
- Backend tests: count test files vs. route/model files.
- Frontend pages: count page components vs. backend endpoints.
- AI evaluation: check for eval/test files in the AI service area.
- DevOps health: check for health check definitions in Docker/compose files.

**WARNING — do NOT read `.claude/stack/*.json` to determine what is
implemented.** Those are design specifications, not code inventory. The
AI stack spec describes BM25, RRF, cross-encoder reranking, and other
capabilities that may not be built yet. Read actual source files in
`backend/app/services/` to determine what the AI pipeline actually does.

### Step 2 — Analyze and score domains

For each domain, assign an attention level based on the signals:

- **Needs attention** — has open high-priority issues, is a cold domain
  with no recent commits, has significant coverage gaps, or has unactioned
  handoffs waiting.
- **Monitor** — has medium-priority issues, moderate activity, or minor
  gaps.
- **Healthy** — active recent work, no open issues, good coverage.

### Step 3 — Generate the radar

Present the overview using this format:

```
OVERVIEW — Attention Radar
───────────────────────────────────────────────────────

{One-sentence project status from project-state.json tldr}

NEEDS ATTENTION
  {domain icon} {Domain}  — {one-line reason}
    → /ask {persona} {suggested question}
    → /forge {suggested action}

  {domain icon} {Domain}  — {one-line reason}
    → /ask {persona} {suggested question}

MONITOR
  {domain icon} {Domain}  — {one-line reason}

HEALTHY
  {domain icon} {Domain}  — {one-line status}

───────────────────────────────────────────────────────
Activity (last 15 commits):
  Backend  ████████░░  {N commits}
  Frontend ██░░░░░░░░  {N commits}
  AI       ████░░░░░░  {N commits}
  DevOps   ░░░░░░░░░░  {N commits}
  Docs     ██████░░░░  {N commits}

Open issues: {N} ({H} high, {M} medium, {L} low)
Unactioned handoffs: {N}
Blockers: {N or "none"}
───────────────────────────────────────────────────────
```

Domain icons and persona mapping (plain text, no emoji):
- Backend: `[BE]` → suggest `/ask eng {question}`
- Frontend: `[FE]` → suggest `/ask frontend {question}`
- AI/ML: `[AI]` → suggest `/ask ai {question}`
- DevOps: `[OPS]` → suggest `/ask devops {question}`
- Security: `[SEC]` → suggest `/ask eng {question}` (security is cross-cutting)
- Product: `[PRD]` → suggest `/ask pm {question}`

Every suggested `/ask` command must use a valid persona alias so the
user can paste it directly. Never use raw domain names like `/ask backend`
— use the persona alias (`eng`, `frontend`, `ai`, `devops`, `pm`).

### Step 4 — Persona adaptation

If a persona was specified before `overview`:
- **Founder persona**: replace domain icons with plain names ("The core
  system" not "[BE] Backend"). Replace `/ask` and `/forge` commands with
  plain-language next steps ("I can look into what's missing in the
  customer-facing screens" not "/ask frontend ..."). Present recommended
  actions as a numbered decision card (see below). Never use "shipped" for
  commits — say "internal development changes completed." Translate all
  status language: "healthy" → "working well", "needs attention" →
  "has risks that could affect customers."
- **PM persona**: frame gaps as feature/capability gaps, use status
  indicators (Built/Partial/Missing/Not started), replace technical
  details with user-impact framing. Present recommended actions as
  prioritized options with user impact. Use "changes" not "commits."
- **Engineer/AI/Frontend/DevOps persona**: use the full technical format
  above with file references where relevant.

**Decision cards** (founder and PM personas only): when presenting
recommended actions, format as numbered options the user can choose
from, not raw commands:

```
What would you like to prioritize?

  1. Strengthen protection against things breaking — the login and
     inventory systems have no automated safety checks
  2. Complete the document management screens — users can upload
     documents but can't manage them in the interface
  3. Prepare for a customer pilot — run an end-to-end readiness check

Pick a number, or tell me what matters most to you.
```

### Step 5 — Suggest next action

End with one recommended action — the single most impactful thing to
do next. Frame it as a ready-to-paste command:

```
Recommended next action:
  /ask {persona} {specific question about the highest-priority gap}

  or start building:
  /forge {specific action to address the highest-priority gap}
```

Use the matching persona alias for the domain (see mapping above).
Example: if the frontend has the biggest gap, suggest
`/ask frontend what backend features have no UI yet?` not
`/ask what backend features have no UI?`.

**Done. Do not continue to Phase 1.**

---

## Phase 0.8 — Readiness Assessment (triggered by `readiness` or `ready`)

If the remaining text (after persona stripping) starts with `readiness`
or `ready`, produce a launch-readiness assessment instead of answering
a question. This short-circuits the rest of the pipeline.

**Purpose:** Tell the user how close the product is to being usable by
real customers, with evidence-based status per feature area.

**Budget**: ≤12 tool calls. No agents.

### Step 1 — Gather evidence

Read these data sources in parallel (skip any that don't exist):

**Source A — Feature inventory**: read route files, model files, and
frontend pages to identify what features exist at the code level.
Do NOT read `.claude/stack/*.json` for this — those are design specs,
not code inventory (see Verification Rules).

**Source B — Test coverage**: count test files per feature area. A
feature with no tests is "built but unverified."

**Source C — Frontend coverage**: check which backend features have
corresponding frontend pages or components. A feature with no UI is
"built but not user-accessible."

**Source D — Project state** (`project-state.json`): read `open_issues`
for known problems, `open_handoffs` for pending work.

**Source E — Recent stability** (`git log --oneline -15`): check if
recent changes were fixes (indicating instability) or features
(indicating forward progress).

### Step 2 — Classify each feature area

For each feature area, assign one of four readiness levels based on
actual evidence:

- **Ready** — code exists, tests exist, UI exists, no open issues.
  A customer could use this today.
- **Risky** — code exists and may work, but missing tests or has open
  issues. Could break without warning.
- **Incomplete** — partially built. Some code exists but key parts
  are missing (no UI, no core functionality, or blocked by dependencies).
- **Not started** — no code exists for this feature area.

**Evidence rule**: every readiness level MUST cite what evidence supports
it. "Ready" requires test files and UI components to exist. "Risky"
requires identifying what's missing. Never assign "Ready" based on code
existing alone — untested code is "Risky" at best.

### Step 3 — Present the assessment

**For founder/PM personas:**

```
READINESS ASSESSMENT
───────────────────────────────────────────────────────

{One-sentence overall verdict: e.g., "The core product works but
important safety gaps make it risky for real customers."}

READY — safe for customers
  {feature area} — {why it's ready}

RISKY — works but could break
  {feature area} — {what's missing: e.g., "no automated safety checks"}
  {feature area} — {what's missing}

INCOMPLETE — partially built
  {feature area} — {what exists vs. what's missing}

NOT STARTED
  {feature area} — {what doesn't exist yet}

───────────────────────────────────────────────────────
Overall: {N} of {total} feature areas are customer-ready.
Biggest risk: {the single most dangerous gap and why}
───────────────────────────────────────────────────────

What would you like to prioritize?

  1. {highest-impact action — plain language}
  2. {second action}
  3. {third action}

Pick a number, or tell me what matters most to you.
```

**For technical personas:**

```
READINESS ASSESSMENT
Route: Direct | Confidence: {HIGH/MEDIUM/LOW}
───────────────────────────────────────────────────────

{One-sentence summary}

| Feature Area | Status | Tests | UI | Issues | Evidence |
|-------------|--------|-------|----|--------|----------|
| {area}      | Ready  | ✓     | ✓  | 0      | {files}  |
| {area}      | Risky  | ✗     | ✓  | 2      | {files}  |
| {area}      | Incomplete | ✓ | ✗  | 1      | {files}  |

───────────────────────────────────────────────────────
Sources: {file:line references}
Recommended:
  /ask {persona} {question about highest-risk area}
  /forge {action to address highest-risk gap}
```

### Step 4 — Persona language

Apply the same persona language rules as the overview radar (Step 4 in
Phase 0.7). Founder gets plain English with decision cards. PM gets
product vocabulary with status indicators. Technical personas get full
detail with file references.

**Done. Do not continue to Phase 1.**

---

## Phase 1 — Tier Decision

Read the question and pick exactly one tier. **This is the single most
important decision in the pipeline** — it determines cost and process.

### Quick tier (~80% of questions)

**Signals**: yes/no question, single fact lookup, "where is X defined?",
"what is the name of X?", "does X exist?", "how many X?", any question
answerable by reading 1-2 files or running one grep/git command.

→ Go to **Quick Path**.

### Standard tier (~15% of questions)

**Signals**: "how does X work?", "what does X do?", "what's the state of
X?", single-concept explanation, feature status question, "what changed
recently?", process/workflow question, enumeration ("list all X").

→ Go to **Standard Path**.

### Deep tier (~5% of questions)

**Signals**: cross-domain architecture ("how does X flow from A to B?"),
multi-step diagnostic ("why is X failing?"), full system review,
comparison of approaches, anything spanning 2+ domains or requiring 5+
files. Also: explicit review requests ("is X safe?", "review X").

→ Go to **Deep Path**.

### Classification rules

1. Pick the cheapest tier that can fully answer the question.
2. When ambiguous, prefer Quick over Standard, Standard over Deep.
3. Follow-up questions always drop one tier from the original (Deep →
   Standard, Standard → Quick) unless the follow-up asks for more depth.
4. Follow-ups are always Claude-direct — never spawn a cold agent for a
   follow-up since the prior answer is already in context.

### Domain keywords (for identifying target files)

- **backend**: routes, models, services, migrations, seed, FastAPI, SQLAlchemy, endpoints, database
- **frontend**: components, pages, state, hooks, UI, React, TypeScript, Vite, Tailwind
- **ai**: LLM, RAG, embeddings, ingestion, retrieval, chunks, vectors, policy, logistics, context engineering, structured outputs, reranking, cross-encoder, guardrails, prompt, pipeline, evaluation
- **devops**: Docker, compose, scripts, hooks, CI, infrastructure, containers
- **security**: auth, JWT, secrets, tokens, passwords, CORS, permissions, roles

---

## Quick Path

**Budget**: ≤2 tool calls. ≤150 words output. No forge scan. No agents.

1. Identify what to look up from the question keywords.
2. Run one Grep or Read to find the answer.
3. Answer directly — short, factual, no ceremony.
4. Apply persona presentation frame. Suggest 1 follow-up.

**Done. Do not continue to Standard or Deep Path.**

---

## Standard Path

**Budget**: ≤6 tool calls. 200-500 words output. No agents.

### Data gathering

Pick the right data source based on the question:

- **Code question** (names a module, feature, or concept): identify target
  files from question keywords (use domain keywords above). Read 2-4 files.
  No forge scan needed — go directly to the files.
- **Process question** ("how does the workflow/protocol work?"): read the
  relevant doc (CLAUDE.md, ORCHESTRATION.md, AGENTS.md, commit-protocol.md).
- **Historical question** ("why did we do X?", references a decision/commit):
  read DECISIONS.md, project-state.json, or run `git log --oneline -10`.
- **Time-sensitive** ("what changed recently?"): run the appropriate
  `git log` or `git diff` command.
- **Enumeration** ("list all X", "what X do we have?"): grep for the pattern
  or read `.forge/report.json` if it exists and is recent.
- **Meta** ("what commands exist?", "how does /X work?"): read the relevant
  config files in `.claude/commands/` or `hooks/agent-config.json`.
- **Quantitative** ("how many X?"): count from scan data or targeted commands.

### Answer generation

1. Read the target files.
2. Start with a **one-sentence bold summary**.
3. Structure the rest with headers, bullets, and short blocks. Apply the
   active persona's language rules.
4. For technical personas (engineer, AI, frontend, devops): include
   `file:line` references, code snippets (3-10 lines), and ASCII diagrams
   when the answer describes a flow or architecture. Use definition-list
   format (bold label + description bullets) instead of Markdown tables.
   For non-technical personas (founder, PM): omit code, file paths, and
   diagrams — the persona's prompt rules take priority over these defaults.
5. Suggest 1-2 follow-up questions.
6. Apply persona presentation frame.

**Done. Do not continue to Deep Path.**

---

## Deep Path

**Budget**: ≤15 tool calls for Claude-direct, or one agent invocation.
500-1500 words output.

### Data gathering

1. Check if `.forge/report.json` exists and is less than 1 hour old. If
   not, run: `python hooks/forge_scan.py --path . --out .forge/`
2. Read `report.json` and cross-reference question keywords against the
   file graph to identify target files (max 8), owner agent, and domain.
3. For diagnostic questions, also check `project-state.json` open_issues.

### Agent decision

Invoke an agent only when the question spans enough complexity to justify
the ~50-70k token cost of a cold agent. Otherwise answer directly.

**Agent routing:**
- `backend/app/` (not AI services) → Rex
- `frontend/src/` → Aria
- AI services (`llm.py`, `rag_*.py`, `ingestion.py`) → Nova
- `hooks/`, `scripts/`, `docker-compose*` → Adam
- Correctness / quality review → Viktor
- Security / auth review → Sage
- Cross-domain flow (2+ domains) → parallel agents, one per domain

**Agent prompt** — invoke with this brief:

```
Read-only Q&A about the Manifesto codebase. Do not implement anything.

## Persona
{active persona name} — {persona prompt rules, joined by newlines}

## Question
{user's question}

## Target Files (read these first)
{list of target files, one per line}

## Instructions
1. Read every listed file before answering.
2. Start with a bold one-sentence summary.
3. Ground claims in actual code with file:line references.
4. Use bullets, headers, and code snippets (3-10 lines). No dense prose.
5. ASCII diagrams for flows/architecture (no Mermaid). Use box-drawing
   characters. Keep under 80 chars wide.
6. Suggest 1-2 follow-up questions.
7. Cap at 12 tool calls total.
```

**Cross-domain flow**: decompose into domain sub-questions, invoke agents
in parallel, then synthesize into one unified answer.

**Circuit breaker**: if an agent is blocked, read the target files
directly (up to 5) and answer with a note that the agent was unavailable.

### Verification (Deep Path only)

After generating the answer (especially agent-generated answers), verify
the top 2-3 claims:
- Glob cited file paths to confirm they exist.
- Grep for cited function/class names in the cited files.
- If a reference doesn't exist, correct it or flag it inline.
- Downgrade confidence one level per failed check.

### Apply persona presentation frame. Include confidence rating for
engineer persona.

---

## Presentation Frames

### Engineer persona (default)

```
ASK — {short question summary}
Route: {tier} | {Agent: name | or "Direct"} | Confidence: {HIGH/MEDIUM/LOW}
───────────────────────────────────────────────────────

{answer}

───────────────────────────────────────────────────────
Sources: {file:line references}
Follow-up questions:
  1. {question}
  2. {question}
```

### Founder persona

```
ASK — {short question summary}
───────────────────────────────────────────────────────

{answer — plain English, no technical metadata}

───────────────────────────────────────────────────────
You might also want to know:
  1. {plain-language follow-up}
  2. {plain-language follow-up}
```

### PM persona

```
ASK — {short question summary}
───────────────────────────────────────────────────────

{answer — feature-oriented, status indicators, gap analysis}

───────────────────────────────────────────────────────
Related questions:
  1. {product-oriented follow-up}
  2. {product-oriented follow-up}
```

### Interviewer personas

Interviewer personas flip the direction — the system challenges, the user
answers. The full session rules (structure, wildcards, difficulty scaling,
scorecard) are defined in each persona's `prompt` field. Follow those
rules exactly.

**Available interviewer personas:**
- `/ask if` or `/ask interviewer-founder` — Founder lens (strategy, prioritization, go-to-market)
- `/ask ip` or `/ask interviewer-pm` — Product Manager lens (user flows, scoping, metrics)
- `/ask ie` or `/ask interviewer-eng` — Senior Engineer lens (architecture, bugs, design tradeoffs)
- `/ask ia` or `/ask interviewer-ai` — AI/ML Engineer lens (pipelines, prompts, evaluation, retrieval)
- `/ask id` or `/ask interviewer-devops` — DevOps/SRE lens (containers, deployment, monitoring, failure modes)

**Argument handling**: after stripping the interviewer persona flag, the
remaining text is a TOPIC FOCUS, not a question. `/ask ie migration safety`
means "run an engineering interview focused on migration safety." If no
text remains, the interviewer picks topics freely.

**Session flow**:
1. **First invocation**: read the codebase (Standard Path data gathering),
   generate challenge (1/6). Do not answer anything — ask.
2. **User responds**: evaluate with the 4-part structure, then present
   the next challenge (2/6, 3/6, etc.). Each user response advances
   the counter by one.
3. **Wildcards**: 1-2 of the 6 challenges are general/conceptual questions
   on the same topic but not about this codebase. Insert at varied
   positions — not always the same slot.
4. **After challenge 6**: evaluate the final answer, then present the
   end-of-session scorecard with rating, strengths, gaps, topic heatmap,
   a copy-pasteable recommended next session command, and an optional
   **"Act on this"** section with 1-2 forge prompts derived from the
   weaknesses the session exposed (e.g., if the user struggled with
   auth security questions, suggest `/forge add rate limiting and
   brute-force protection to the login endpoint`).
5. **Difficulty scales dynamically**: strong answers → harder follow-ups.
   Weak answers → acknowledge what they got right, simplify the angle,
   offer hints. Stuck → offer two options to choose between.

### AI / Frontend / DevOps personas

These domain personas use the same technical frame as the engineer
persona — they request Sources, confidence ratings, and file:line
references in their prompt rules.

```
ASK — {short question summary}
Route: {tier} | {Agent: name | or "Direct"} | Confidence: {HIGH/MEDIUM/LOW}
───────────────────────────────────────────────────────

{answer — domain-specific vocabulary and concerns}

───────────────────────────────────────────────────────
Sources: {file:line references}
Follow-up questions:
  1. {domain-specific follow-up}
  2. {domain-specific follow-up}
```

### Other personas

Use the minimal frame (summary + answer + follow-ups). Only include
metadata if the persona's prompt explicitly asks for it.

---

## Session Behavior

After presenting an answer, if the user asks a follow-up (references the
prior answer, narrows scope, uses "what about X?"), treat it as an
implicit `/ask` with the same persona. Carry forward the domain context.
Drop one tier from the original. Do not re-scan or re-classify.

If the follow-up chain reaches 5+ questions in the same domain, generate
1-2 forge-ready prompts from the conversation context using the active
persona's `forge_templates` and suggest them directly:

```
You're going deep on {domain}. Ready to build?

  /forge {contextual prompt based on the gaps discovered in this session}
  /forge {second prompt if applicable}
```

---

## Verification Rules (apply to ALL phases)

These rules prevent false status claims. They apply whenever the answer
describes what works, what exists, or what users can do.

### Specification vs. implementation

`.claude/stack-profile.json` and `.claude/stack/*.json` describe the
**intended design** — what the system SHOULD use, not what IS implemented.
Never derive implementation status from these files. They describe BM25,
RRF, cross-encoder reranking, SSE streaming, and other capabilities that
may be planned but not yet built.

To determine what is actually implemented:
1. Read the actual source code files (e.g., `backend/app/services/*.py`).
2. Check for imports, function definitions, and call sites.
3. A capability is "implemented" only if executable code exists for it.
4. A capability described in the stack spec but absent from source code
   is "Planned" or "Not yet implemented" — never "Built" or "Ready."

This is the single most important verification rule. Violating it causes
the system to claim planned architecture is working code, which destroys
user trust.

### Placeholder detection

Before classifying a frontend page or component as "exists" or "built":
1. Read the component file (at least the return/render block).
2. Check if it renders real functionality (forms, data, interactions) or
   just placeholder content ("Coming soon", "Under construction", empty
   state with no actions, static text with no data binding).
3. A placeholder page is **not** a working UI. Classify the feature as
   "Incomplete" or "Partial" — never "Ready" or "Built."

Common placeholder patterns to detect:
- String literals like "Coming soon", "Under construction", "TODO"
- Components that render only a heading and no interactive elements
- Pages imported in the router but rendering static text only

### Behavior verification

Before claiming how a user flow works (navigation, redirects, landing
pages, upload capabilities):
1. Read the actual routing code (e.g., `App.tsx`, router config) to
   verify where users are sent after login.
2. Read the actual component to verify claimed capabilities (e.g., "users
   can upload documents through X" — check if X has an upload handler).
3. Never infer behavior from page names alone. `Dashboard.tsx` might be
   a placeholder. `/assistant` might be the actual landing page.
4. Distinguish between **intended** behavior (what the spec says) and
   **observed** behavior (what the code actually does). When they differ,
   report observed behavior and note the discrepancy.

### Cross-answer consistency

Within the same session, later answers must not contradict earlier ones
without explicit acknowledgment. This is especially critical between
deep Q&A answers (which read actual code) and overview/radar answers
(which scan more broadly and are more prone to error).

If an earlier answer in the session established that a capability is
missing (e.g., "BM25 is not implemented"), a later answer must not
claim it exists. When in doubt, defer to the answer that read the
actual source code.

### Self-correction

When a follow-up answer contradicts or corrects something stated in a
previous answer in the same session:
1. Explicitly acknowledge the correction: "Correction from my earlier
   answer: I said X, but after reading the code, Y is actually the case."
2. Never silently change a prior claim — the user may have already acted
   on the earlier answer.

### Architecture-aware suggestions

When generating forge prompts or build suggestions, verify that the
suggestion matches the actual architecture of the target system:
- If a system uses **relational/structured database queries** (SQL,
  ORM), do not suggest adding vector-retrieval components (reranking,
  cross-encoder) to it.
- If a system uses **vector retrieval**, do not suggest relational
  query optimizations.
- Read the actual service file to determine which retrieval paradigm
  it uses before suggesting improvements.
- Each domain (policy RAG, logistics lookup, assistant) may use a
  different retrieval strategy — do not assume they all work the same way.

---

## Constraints

- Read-only. No file modifications, no commits, no state updates.
- No repository-wide scans — use targeted reads and greps.
- Does not count toward any commit's tool budget.
