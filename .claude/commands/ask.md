# /ask — Domain-Routed Codebase Q&A

Parse `$ARGUMENTS` as the user's question. If empty, ask: "What would you like
to know about the codebase?"

This command answers questions about the Manifesto codebase by classifying what
kind of answer is needed, then routing to the right source: a domain expert
agent, project documents, git history, the codebase graph, or direct
computation. Read-only — no code changes, no commit protocol updates.

---

## Phase 1 — Question Classification & Route Selection

Read the question and classify it into exactly one **answer route**. The route
determines what data source answers the question and how it is presented.

### Session continuity check

Before classifying, check if this is a **follow-up question** in an ongoing
`/ask` session. A question is a follow-up if:

- It references something from a previous `/ask` answer in this conversation
  ("what about the chunking part?", "and how does that connect to X?",
  "go deeper on the second point")
- It uses pronouns that only make sense given a prior answer ("how does it
  handle errors?", "what calls that function?")
- It's in the same domain as the previous `/ask` and narrows scope

If it is a follow-up:
1. **Carry forward** the previous route, domain, target files, and agent type
   — do not re-scan or re-classify from scratch.
2. **Narrow** the target files to only those relevant to the follow-up.
3. **Extend context**: include a one-paragraph summary of the previous answer
   in the agent prompt so the agent builds on it rather than repeating.
4. **Re-classify only if** the follow-up shifts to a genuinely different route
   (e.g., previous was `domain-expert`, follow-up is "is that secure?" →
   switch to `review`).

### Route table

| Route | Trigger signals | Data source | Agent? |
|-------|----------------|-------------|--------|
| `domain-expert` | Names a specific module, service, file, or technical concept that maps to application code | Graph-RAG scan → agent reads target files | Yes — domain owner |
| `review` | "Is X safe?", "Is X correct?", "Does X handle Y?", "Review X" | Agent reads target files with a review lens | Yes — Viktor or Sage |
| `process` | "How does the commit protocol work?", "How does delegation work?", "What is the workflow for X?" | CLAUDE.md, ORCHESTRATION.md, AGENTS.md, commit-protocol.md | No — Claude reads docs directly |
| `historical` | "Why did we do X?", "What was decided about X?", "When was X changed?", references a commit number, decision ID, or past event | DECISIONS.md, project-state.json replan_history, git log | No — Claude reads docs + git |
| `inventory` | "What X do we have?", "List all X", "How many X?", "Show me the X" — asking for an enumeration | Graph-RAG scan `report.json` + targeted grep | No — Claude computes from scan data |
| `flow` | "How does X flow from A to B?", "What happens when a user does X end-to-end?", traces a path across 2+ domains | Graph-RAG scan → parallel agent invocations across domains | Yes — parallel: primary + secondary |
| `diagnostic` | "Why is X failing?", "I get error Y when Z", "This test fails with X" — runtime behavior questions | Target files + command execution (read-only commands only: git log, git diff, pytest --collect-only) | Yes — domain owner |
| `time-sensitive` | "What changed since X?", "What's different on this branch?", "Recent changes to X", any temporal framing | git log, git diff | No — Claude runs git commands |
| `meta` | "What commands are available?", "What agents do we have?", "How does /ask work?" — questions about the tooling | .claude/commands/, AGENTS.md, agent-config.json | No — Claude reads config files |
| `quantitative` | "How many lines/files/tests?", "How big is X?", "What's the coverage?" — numeric answers | Graph-RAG scan data + targeted commands (wc, pytest --collect-only) | No — Claude computes |

### Classification rules

1. Check trigger signals in order. First match wins.
2. If the question contains both a domain keyword AND a temporal word ("recently",
   "since", "last week"), prefer `time-sensitive` over `domain-expert`.
3. If the question contains "why" + a decision/commit reference, prefer
   `historical` over `domain-expert`.
4. If the question asks for a list/enumeration of things, prefer `inventory`
   over `domain-expert` even if domain keywords are present.
5. If genuinely ambiguous between two routes, pick the one with the cheaper
   data source (docs before agents, scan data before git).

### Depth estimation & execution tier

Estimate the answer depth based on question complexity. Depth determines both
the word budget AND whether an agent is invoked or Claude answers directly.
This is the primary token-cost control.

| Depth | Signals | Word budget | Inline snippets | Execution tier |
|-------|---------|-------------|-----------------|----------------|
| `brief` | Yes/no question, single fact lookup, one-word concept, "what is the name of X?", "where is X defined?" | 50–150 words | 0–1 snippet | **Claude-direct** — always. Read ≤2 target files, answer inline. ~3-5k tokens. |
| `standard` | "How does X work?", "What does X do?", single-concept explanation, single-function scope | 200–500 words | 1–2 snippets | **Claude-direct** — Claude reads the target files (≤4) and answers with snippets + diagram. ~8-15k tokens. |
| `deep` | Architecture questions, multi-step flows, "explain the full X", comparison of approaches, diagnostic with multiple possible causes | 500–1000 words | 2–4 snippets | **Agent** — invoke the domain expert. The question is complex enough that domain-specialist grounding justifies the cost. ~50-70k tokens. |
| `comprehensive` | Cross-domain flows involving 2+ agents, full system architecture, "walk me through everything about X" | 800–1500 words | 3–6 snippets | **Parallel agents** — invoke 2+ agents in parallel. ~90-130k tokens. |

**The rule: `brief` and `standard` never invoke an agent. `deep` and
`comprehensive` do.** This means roughly 60-70% of questions (fact lookups,
single-concept explanations, "where is X?") are answered at ~5-15k tokens
instead of ~50-75k.

The depth also scales with the number of domains involved:
- 1 domain → cap at `deep`
- 2+ domains → allow `comprehensive`

Follow-up questions default to one depth level lower than the original unless
the follow-up itself asks for more depth ("go deeper", "explain in detail").

**Follow-ups are always Claude-direct** regardless of depth. Claude already
has the previous answer in conversation context — spawning a cold agent that
doesn't remember the prior answer is wasteful. Instead, Claude reads the
specific files the follow-up targets (narrowed from the original target list)
and builds on the prior answer directly. Exception: if a follow-up explicitly
shifts route (e.g., from `domain-expert` to `review`), and the new route is
`deep` or `comprehensive`, invoke the review agent since it brings a different
analytical lens.

### Token budget summary

| Scenario | Estimated tokens |
|----------|-----------------|
| `brief` question | ~3-5k |
| `standard` question | ~8-15k |
| `deep` question (agent) | ~50-70k |
| `comprehensive` question (parallel agents) | ~90-130k |
| Follow-up (any depth) | ~5-15k |
| 4-question session: standard → 3 follow-ups | ~25-55k total |
| 4-question session: deep → 3 follow-ups | ~65-110k total |

### Keywords for domain mapping (used by `domain-expert`, `review`, `flow`, `diagnostic`)

- **backend**: routes, models, services, migrations, seed, alembic, FastAPI,
  SQLAlchemy, CRUD, endpoints, database, schema
- **frontend**: components, pages, state, hooks, UI, React, TypeScript, Vite,
  Tailwind, layout, sidebar, form
- **ai**: LLM, RAG, embeddings, ingestion, retrieval, chunks, vectors, policy,
  logistics, prompts, citations
- **devops**: Docker, Dockerfile, compose, scripts, hooks, CI, infrastructure,
  deployment, containers, volumes
- **security**: auth, JWT, secrets, tokens, passwords, input validation,
  uploads, CORS, permissions, roles

---

## Phase 2 — Data Gathering

Each route has its own data-gathering step. Execute only the step matching
the selected route. If this is a follow-up with a carried-forward route, skip
the scan and reuse the previous target files (narrowed to the follow-up scope).

### Route: `domain-expert` / `flow` / `diagnostic`

Check if `.forge/report.json` exists and is less than 1 hour old. If so, reuse
it. Otherwise, run:

```powershell
python hooks/forge_scan.py --path . --out .forge/
```

Read `.forge/report.json` and cross-reference the question keywords against the
file graph to identify:

1. **Target files** — files whose names, categories, or import connections match
   the question keywords. Prioritize:
   - Direct keyword match (question mentions "ingestion" → `ingestion.py`)
   - Hub proximity (target imports a hub → include the hub for context)
   - Call-tree tracing (follow imports upstream/downstream)
2. **Owner agent** — from `domain_ownership`, who owns the target files
3. **Domain concentration** — which domain has the most target files

Limit target files to the top 8 most relevant.

For `flow` route, identify all domains in the path and collect target files
from each domain. Do not limit to one domain — the whole point of `flow` is
cross-domain tracing.

For `diagnostic` route, also check `project-state.json` open_issues for any
issue matching the reported symptom.

### Route: `process`

Read the following files (only the sections relevant to the question):
- `CLAUDE.md`
- `ORCHESTRATION.md`
- `AGENTS.md`
- `commit-protocol.md`

No graph scan needed.

### Route: `historical`

Read:
- `DECISIONS.md` — search for the referenced decision ID or topic
- `project-state.json` — check `replan_history`, `open_issues`, `notes`,
  `historical_notes`
- Run `git log --oneline -20` if the question references a recent change

No graph scan needed.

### Route: `inventory`

Check if `.forge/report.json` exists and is recent. If so, reuse it. Otherwise
run the scan.

Read `.forge/report.json` and extract the relevant category. Supplement with
targeted grep if the scan data is too coarse (e.g., "list all API endpoints"
→ grep for `@router` in `backend/app/api/`).

### Route: `time-sensitive`

Run the appropriate git command:
- "What changed since X?" → `git log --oneline --since="X"`
- "What's different on this branch?" → `git log --oneline main..HEAD`
- "Recent changes to X" → `git log --oneline -10 -- path/to/X`
- "What changed in file X?" → `git log --oneline -10 -- X` + `git diff HEAD~5 -- X`

No graph scan needed.

### Route: `meta`

Read the relevant config files:
- "What commands?" → list `.claude/commands/*.md` filenames
- "What agents?" → read `hooks/agent-config.json` or `AGENTS.md`
- "How does /X work?" → read `.claude/commands/X.md`

No graph scan needed.

### Route: `quantitative`

Use `.forge/report.json` if available. Supplement with targeted commands:
- "How many tests?" → `pytest --collect-only -q` (via docker compose if needed)
- "How many files?" → count from scan data
- "How big is X?" → line counts from scan data or `wc -l`

### Route: `review`

Same as `domain-expert` data gathering, but the agent selection differs
(Phase 3).

---

## Phase 3 — Answer Generation

### Execution tier: Claude-direct (`brief` / `standard` depth, or any follow-up)

Claude answers the question directly without invoking an agent. Steps:

1. Read the target files identified in Phase 2 (≤2 files for `brief`, ≤4 for
   `standard`). For follow-ups, read only the files relevant to the narrowed
   scope.
2. Apply the same answer format rules as the agent prompt (inline snippets,
   Mermaid diagrams, source citations, confidence rating).
3. For follow-ups, build on the previous answer — reference it, don't repeat
   it. If the previous answer was agent-generated (`deep`), Claude has that
   full answer in context and can drill into specific parts without re-reading
   everything.

This tier handles the majority of questions at ~5-15k tokens each.

### Execution tier: Agent (`deep` / `comprehensive` depth, first question only)

Invoke the domain expert agent. This tier is for questions complex enough that
a cold agent reading 5-8 files and producing a grounded analysis is worth the
~50-70k token cost.

#### Agent routing table

| Route | Signal | Agent | Subagent type |
|-------|--------|-------|---------------|
| `domain-expert` | Target files in `backend/app/` (not AI services) | Rex | rex |
| `domain-expert` | Target files in `frontend/src/` | Aria | aria |
| `domain-expert` | Target files in AI services (`llm.py`, `rag_*.py`, `ingestion.py`) | Nova | nova |
| `domain-expert` | Target files in `hooks/`, `scripts/`, `docker-compose*` | Adam | adam |
| `review` | Correctness / quality focus | Viktor | viktor |
| `review` | Security / auth / secrets focus | Sage | sage |
| `flow` | All domains in the flow path | Multiple owners | Parallel |
| `diagnostic` | Domain of the failing component | Domain owner | (varies) |

#### Agent prompt

Invoke the selected agent with this structured brief:

```
You are answering a user question about the Manifesto codebase. This is a
read-only Q&A — do not implement anything, do not suggest code changes unless
the question is specifically asking for implementation guidance.

## Question
{user's question}

## Route
{domain-expert / review / flow / diagnostic}

## Answer Depth
{brief / standard / deep / comprehensive} — target {N–M} words.

## Relevant Files (read these first)
{list of target files from the graph scan, one per line}

## Previous Answer Context (follow-up only)
{one-paragraph summary of the previous /ask answer, if this is a follow-up
question — omit entirely for first questions}

## Project Context
{relevant entries from project-state.json: open issues, handoffs, decisions
that relate to the question — omit if none are relevant}

## Answer Instructions

1. Read every file listed above before answering.
2. Ground your answer in actual code — reference specific functions, classes,
   constants, and patterns you find. Use file_path:line_number format.
3. Structure the answer so both a senior engineer and someone new to the
   codebase can follow it. Start with a one-paragraph summary, then go deeper.
4. Adapt the answer format to the question:
   - Conceptual → explanation with architecture overview first
   - Procedural → numbered steps, end with a "Prompt You Can Use" section
   - Diagnostic → symptom analysis, root cause, evidence from code
   - Review → findings list with severity, cite the specific code
   - Flow → step-by-step trace through the code path with file:line at each hop

5. **Inline code snippets**: for the most critical code referenced in your
   answer, embed the actual snippet (3-10 lines) directly in the answer.
   Select snippets that are essential to understanding — function signatures,
   key logic blocks, configuration values. Do not dump entire files. Use
   fenced code blocks with the language identifier.

6. **Visual diagrams**: when the answer describes a flow, architecture,
   data path, request lifecycle, or component relationship, include a
   Mermaid diagram or ASCII flow chart. Rules:
   - Use Mermaid `graph TD` for top-down flows (request lifecycle, data
     pipelines, inheritance)
   - Use Mermaid `graph LR` for left-right flows (processing pipelines,
     horizontal architectures)
   - Use Mermaid `sequenceDiagram` for request/response interactions between
     components
   - Use ASCII art only when Mermaid cannot express it (e.g., table layouts,
     directory trees)
   - Every diagram must have a one-line caption above it
   - Label every node and edge — unlabeled diagrams are worthless

   Examples of when to include a diagram:
   - "How does JWT auth work?" → sequenceDiagram showing client → route →
     JWT decode → DB lookup → response
   - "What does the ingestion endpoint do?" → graph TD showing upload →
     validate → extract text → chunk → embed → store
   - "How does data flow from frontend to AI?" → graph LR showing
     React form → API route → service → LLM → response → UI

7. Include a "Sources" section listing every file:line you referenced.
8. Rate your confidence: HIGH (code clearly answers this), MEDIUM (some
   inference needed), or LOW (significant gaps in what you could find).
9. Suggest 1-2 natural follow-up questions the user might want to ask next.

Stay within the word budget from the Answer Depth field.
Cap your work at 12 tool calls (reads + searches). Do not scan the full repo.
```

#### Parallel invocation for `flow` route

When the `flow` route identifies 2+ domains, invoke agents **in parallel**
rather than sequentially:

1. Decompose the flow question into domain-scoped sub-questions. Example:
   - "How does document upload work end-to-end?"
   - → Aria: "How does the frontend upload form submit the file and handle
     the response?"
   - → Rex: "How does the backend /documents endpoint receive, validate,
     and persist the upload?"
   - → Nova: "How does the ingestion service process the uploaded document
     into chunks and embeddings?"

2. Invoke all domain agents **in the same message** (parallel tool calls).
   Each agent gets its domain's target files plus the sub-question.

3. After all agents return, **synthesize** the answers into one unified
   step-by-step flow with a single Mermaid diagram tracing the full path
   across all domains. Number each step and annotate with the domain
   and agent who provided that leg.

4. The synthesized answer must read as one coherent narrative, not three
   separate answers stitched together.

#### Circuit breaker fallback

If the agent invocation is blocked by `tool_cap_start.py` or any circuit
breaker:

1. Read the target files directly (up to 5 files).
2. Synthesize the answer from the code and graph scan data.
3. Prefix the answer with: "Note: {Agent} was unavailable; answer synthesized
   from code analysis."

### Routes that Claude answers directly: `process`, `historical`, `inventory`, `time-sensitive`, `meta`, `quantitative`

Claude answers the question directly from the data gathered in Phase 2. No
agent invocation. Apply these format rules:

| Route | Answer format | Visual |
|-------|--------------|--------|
| `process` | Step-by-step explanation with doc references (file:section) | Mermaid flowchart of the process steps |
| `historical` | Timeline or narrative with decision IDs and commit numbers | ASCII timeline if 3+ events |
| `inventory` | Table or bullet list, sorted logically (alpha, by domain, etc.) | Table always; add tree diagram for hierarchical items |
| `time-sensitive` | Chronological list of changes with commit hashes | None usually; Mermaid gantt if many changes |
| `meta` | Direct factual answer, list or table if multiple items | Table for agent/command listings |
| `quantitative` | Number first, then breakdown if useful | Table for breakdowns |

For Claude-direct routes, apply the same inline code snippet and diagram rules
from the agent prompt. Visuals are not optional — if the answer describes a
flow, architecture, or relationship, include a diagram.

---

## Phase 4 — Answer Grounding Verification

Before presenting the answer to the user, verify the key claims. This step
catches hallucinations and stale references.

### Verification tier (scales with depth)

| Depth | Verification level | Budget | What to check |
|-------|--------------------|--------|---------------|
| `brief` | **None** — Claude read the files directly, no secondhand claims | 0 tool calls | Skip entirely |
| `standard` | **Spot-check** — verify the single most critical claim | 1 tool call | One Grep for the key function/class cited |
| `deep` | **Standard** — verify file existence + top claims | 3 tool calls | Glob cited paths + Grep top 2 functions |
| `comprehensive` | **Full** — verify files, functions, and snippets | 4 tool calls | Glob paths + Grep functions + Read-verify 1 snippet |

The rationale: `brief` and `standard` are Claude-direct — Claude already read
the actual files, so its claims are grounded by construction. Verification
matters most for agent-generated answers where the agent may have paraphrased
or inferred across files.

### Verification rules (for `deep` and `comprehensive`)

1. **File existence**: for every file path cited in the answer, confirm it
   exists using Glob. Remove or correct any dead references.

2. **Function/class existence**: for the top 2-3 most critical function or
   class names cited, grep for them in the cited file. If a cited function
   does not exist in that file, either correct the reference or flag it:
   "Note: {function} was not found at the cited location; the code may have
   changed since the scan."

3. **Inline snippet accuracy** (comprehensive only): for the most critical
   embedded code snippet, verify it matches the actual file content. Read the
   cited file:line range and compare. If the snippet diverges from the actual
   code, replace it with the real code.

4. **Confidence downgrade**: if any verification check fails, downgrade the
   confidence by one level (HIGH → MEDIUM, MEDIUM → LOW). If 2+ checks fail,
   set confidence to LOW and add a warning to the answer header.

### What NOT to verify

- Opinion or architectural commentary (the agent's analysis is the value)
- Follow-up suggestions
- Diagram accuracy (diagrams are derived from the code the agent read)
- Word count compliance

---

## Phase 5 — Present the Answer

Display the answer with this frame:

```
ASK — {short question summary}
Route: {route} | {Agent: name | or "Direct"} | Confidence: {HIGH/MEDIUM/LOW}
Depth: {brief/standard/deep/comprehensive} | Follow-up: {#N or "—"}
───────────────────────────────────────────────────────

{answer — preserve all formatting, headers, code blocks, diagrams, and tables}

───────────────────────────────────────────────────────
Sources: {file:line or doc:section references}
Follow-up questions:
  1. {suggested question}
  2. {suggested question}
```

If the answer includes a "Prompt You Can Use" section, keep it clearly
separated so the user can copy it.

If any grounding verification failed, add a verification note after the
confidence rating:

```
⚠ Verification: {N} of {M} references could not be confirmed — marked inline.
```

---

## Session Behavior

`/ask` is designed for multi-turn sessions. After presenting an answer:

1. The user may ask a follow-up question with or without `/ask` prefix.
   If the next user message is clearly a follow-up to the `/ask` answer
   (references it, narrows it, asks "what about X?"), treat it as an
   implicit `/ask` follow-up and apply the session continuity rules from
   Phase 1.

2. Track the follow-up count (Follow-up: #1, #2, #3...) in the header so
   the user can see the conversation depth.

3. Each follow-up reuses the cached scan data and carries forward the
   domain context. Only re-scan if the follow-up shifts to a completely
   different area of the codebase.

4. If the follow-up chain reaches 5+ questions in the same domain, suggest:
   "You're going deep on {domain}. Want me to run `/forge` to turn these
   insights into a commit spec?"

---

## Error Handling

- **Empty question**: prompt the user to provide one
- **Too vague** (no route signals match): ask the user to narrow down
  — "Which layer? Which feature? Can you name a file, function, or concept?"
- **Agent blocked**: Claude answers directly using the graph scan and file
  reads, noting the fallback
- **Agent returns a thin answer**: Claude supplements with its own file reads
  and notes which parts came from the agent vs. orchestrator analysis
- **Question spans routes**: prefer the route that gives a more complete answer
  (e.g., "How many endpoints do we have and how does auth work on them?" is
  `inventory` first, with a `domain-expert` follow-up suggestion)
- **Grounding verification failure**: downgrade confidence, flag inline, but
  still present the answer — a partially verified answer is better than no
  answer

---

## What This Command Does NOT Do

- Does not write or modify any files
- Does not create commits or update commit-protocol.md
- Does not update project-state.json
- Does not run destructive commands
- Does not count toward any commit's tool budget
- Does not trigger quality gates or preflight checks
