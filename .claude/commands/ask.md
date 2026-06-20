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

**Fast path** — if the first word does NOT match any prefix AND the
remaining text is not `questions`, `q`, `overview`, or `ov`:
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

### Step 1 — Load evergreen questions

Read the active persona's `questions.evergreen` array from the persona's
individual file (e.g., `.claude/personas/engineer.json`). These are the
base options.

### Step 2 — Generate contextual questions

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

### Step 3 — Generate forge prompts

Using the **same contextual data** already gathered in Step 2 (hub files,
project state, recent changes), generate 2-3 forge-ready prompts using
the active persona's `forge_templates` from the persona's individual file.

**How to generate each prompt:**

1. For each gap, issue, or opportunity identified in Step 2, pick the
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

**Rules:**
- If no `forge_templates` key exists for the persona (e.g., interviewer
  personas), skip this step entirely.
- Never generate forge prompts for things that are already built.
- Prioritize gaps over improvements — missing features before polish.
- Each prompt must describe a **different** gap or opportunity.

### Step 4 — Assemble and deduplicate

Combine evergreen + contextual questions. Remove near-duplicates. Keep
contextual over evergreen when they overlap. Target: 6-8 total questions.

### Step 5 — Present to the user

Split into three groups and present. Output the first two groups using
AskUserQuestion, then render the third group as a text section below.

**Group 1 — "Start here"**: 3-4 best overview questions.
**Group 2 — "Go deeper"**: 3-4 most specific contextual questions.
**Group 3 — "Build next"**: 2-3 forge-ready prompts (from Step 3).
Render as a labeled text block after the AskUserQuestion selection:

```
BUILD NEXT — paste any of these into the chat to start planning:

  /forge {prompt 1}
  /forge {prompt 2}
  /forge {prompt 3}
```

If Step 3 produced no forge prompts (interviewer personas, or no gaps
found), omit Group 3 entirely.

### Step 6 — Run the selected question

Take the user's selection, carry the active persona forward, and execute
through the pipeline starting at Phase 1.

---

## Phase 0.7 — Overview Radar (triggered by `overview` or `ov` keyword)

If the remaining text (after persona stripping) starts with `overview` or
`ov`, produce a cross-domain attention radar instead of answering a
question. This short-circuits the rest of the pipeline.

**Purpose:** Tell the user which hat needs attention right now — surface
gaps, imbalances, and risks they wouldn't know to ask about.

**Budget**: ≤12 tool calls. No agents.

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
    → /ask {domain} {suggested question}
    → /forge {suggested action}

  {domain icon} {Domain}  — {one-line reason}
    → /ask {domain} {suggested question}

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

Domain icons (plain text, no emoji):
- Backend: `[BE]`
- Frontend: `[FE]`
- AI/ML: `[AI]`
- DevOps: `[OPS]`
- Security: `[SEC]`
- Product: `[PRD]`

### Step 4 — Persona adaptation

If a persona was specified before `overview`:
- **Founder persona**: replace domain icons with plain names, replace
  `/ask` and `/forge` commands with plain-language descriptions of what
  needs attention and why it matters to the business.
- **PM persona**: frame gaps as feature/capability gaps, use status
  indicators (Built/Partial/Missing), replace technical details with
  user-impact framing.
- **Engineer/AI/Frontend/DevOps persona**: use the full technical format
  above with file references where relevant.

### Step 5 — Suggest next action

End with one recommended action — the single most impactful thing to
do next. Frame it as a ready-to-paste command:

```
Recommended next action:
  /ask {domain} {specific question about the highest-priority gap}

  or start building:
  /forge {specific action to address the highest-priority gap}
```

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

## Constraints

- Read-only. No file modifications, no commits, no state updates.
- No repository-wide scans — use targeted reads and greps.
- Does not count toward any commit's tool budget.
