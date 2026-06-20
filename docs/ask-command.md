# /ask — Codebase Q&A and Interview System

The `/ask` command is Manifesto's read-only codebase Q&A system. It answers
questions about the project, adapts its language to the audience, and can
run structured interview sessions to challenge your thinking.

## Table of Contents

- [Quick Start](#quick-start)
- [Personas](#personas)
  - [Answer Personas](#answer-personas)
  - [Interviewer Personas](#interviewer-personas)
- [Question Bank](#question-bank)
- [How the Pipeline Works](#how-the-pipeline-works)
- [Usage Reference](#usage-reference)
  - [Basic Q&A](#basic-qa)
  - [Guided Discovery](#guided-discovery)
  - [Interview Mode](#interview-mode)
  - [Topic-Focused Interviews](#topic-focused-interviews)
- [Examples](#examples)
- [Persona Aliases](#persona-aliases)
- [Architecture](#architecture)
  - [Files](#files)
  - [Tiered Pipeline](#tiered-pipeline)
  - [Token Budgets](#token-budgets)
- [Adding New Personas](#adding-new-personas)
- [Design Decisions](#design-decisions)
- [Testing](#testing)

---

## Quick Start

```bash
# Ask a question (defaults to engineer persona)
/ask how does auth work?

# Ask as a specific persona
/ask founder what can this product do?
/ask pm what's the state of shipments?
/ask eng how does the ingestion pipeline work?

# Get suggested questions
/ask founder questions
/ask pm q

# Start an interview session
/ask ie                              # engineering interview, random topics
/ask ip                              # product manager interview
/ask if                              # founder interview

# Focused interview on specific topics
/ask ie migration safety and test isolation
/ask ip user onboarding and retention
/ask if competitive moats and go-to-market
```

---

## Personas

Every `/ask` invocation uses a persona that controls the language, structure,
and presentation of the output. There are two categories: **answer personas**
(the system answers your question) and **interviewer personas** (the system
challenges you with questions).

### Answer Personas

| Persona | Aliases | What it does |
|---------|---------|--------------|
| **Founder** | `founder`, `nontechnical`, `plain`, `simple` | Plain English, no jargon, business outcomes. 3-5 bullet answers. No code, no file paths, no acronyms. |
| **Product Manager** | `pm`, `product`, `product-manager` | Feature-oriented language, status indicators (Built/Partial/Missing/Planned), gap analysis. No engineering jargon. |
| **Senior Engineer** | `engineer`, `eng`, `dev`, `senior`, `technical` | Full technical detail — file paths, line numbers, code snippets, ASCII diagrams, import chains. The default persona. |

**How persona is selected** (in priority order):

1. **Explicit flag** — first word of arguments matches a persona alias
2. **Auto-memory** — stored user role preference from previous sessions
3. **Default** — `engineer` (configurable in `persona-profiles.json`)

**Lazy loading optimization**: when no persona flag is present and the
keyword isn't `questions`/`q`, the persona profiles file is NOT read.
The default engineer behavior is applied directly, saving ~1-2k tokens
on the most common invocation pattern (`/ask how does X work?`).

### Interviewer Personas

Interviewer personas flip the dynamic — the system asks, you answer.

| Persona | Aliases | What it challenges |
|---------|---------|-------------------|
| **Interviewer — Founder** | `interviewer-founder`, `interview-founder`, `if` | Strategic thinking, product vision, prioritization, go-to-market, competitive analysis |
| **Interviewer — PM** | `interviewer-pm`, `interview-pm`, `ip` | User empathy, feature scoping, gap analysis, metrics, stakeholder communication |
| **Interviewer — Engineer** | `interviewer-eng`, `interview-eng`, `ie` | Architecture, code reading, bug spotting, design tradeoffs, performance, migration planning |

Every interview challenge is **grounded in the actual codebase** — real code,
real gaps, real issues. No generic textbook questions.

---

## Question Bank

Don't know what to ask? The question bank generates persona-appropriate
questions based on the current state of the codebase.

```bash
/ask founder questions    # plain-English questions about the product
/ask pm q                 # product-oriented questions about features and gaps
/ask eng questions        # technical questions about architecture and code
```

The question bank combines three outputs:

- **Evergreen questions** — always-relevant questions defined per persona
- **Contextual questions** — dynamically generated from:
  - `.forge/report.json` — hub files and domain structure
  - `project-state.json` — open issues and blockers
  - `git log` — recent changes
- **Forge prompts** — actionable `/forge` commands generated from the same
  contextual data, ready to paste and start building

Questions are presented as an interactive selection with two groups:
"Start here" (overview questions) and "Go deeper" (specific questions).
Below the selection, a **"Build next"** section shows 2-3 forge-ready
prompts that can be pasted directly to start planning commits.

```
BUILD NEXT — paste any of these into the chat to start planning:

  /forge add shipment editing — PATCH endpoint with role-based access and frontend form
  /forge build vendor dashboard UI — frontend for existing vendor CRUD so managers can browse and filter
  /forge fix OI-24 — auth token refresh race condition with regression tests
```

Each forge prompt is grounded in actual codebase gaps — not generic
suggestions. The persona controls the language: founder prompts describe
user value, PM prompts describe capabilities and user flows, engineer
prompts describe technical scope and test coverage.

---

## How the Pipeline Works

The `/ask` command uses a **3-tier pipeline** that matches question
complexity to processing cost:

```
Question arrives
      │
      ▼
┌─────────────┐
│ Persona     │ ← Select from flag, memory, or default
│ Selection   │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐
│ "questions" │────►│ Question     │ ← Show guided questions, short-circuit
│  keyword?   │     │ Bank         │
└──────┬──────┘     └──────────────┘
       │ no
       ▼
┌─────────────┐
│ Tier        │ ← Quick / Standard / Deep
│ Decision    │
└──────┬──────┘
       │
       ├── Quick ──────► Grep/Read 1-2 files → answer (≤150 words)
       │
       ├── Standard ──► Read 2-4 files → structured answer (200-500 words)
       │
       └── Deep ──────► Forge scan → agent invocation → verification
                         → full answer (500-1500 words)
```

---

## Usage Reference

### Basic Q&A

```bash
# Minimal — uses default persona (engineer)
/ask where is the shipment model defined?

# With persona
/ask founder what can this product do?
/ask pm what features are built vs missing?
/ask eng how does the auth dependency chain work?
```

**Follow-ups**: after an answer, ask a follow-up naturally. The system
carries forward the persona and domain context:

```
/ask pm what's the state of shipments?
> [answer about shipments]

what about vendor management?
> [follow-up answer, still in PM persona]
```

### Guided Discovery

```bash
/ask questions          # question bank with default persona
/ask founder questions  # founder-appropriate questions
/ask pm q              # shorthand
/ask eng q             # engineer questions
```

### Interview Mode

Start a session with no topic (free-form) or a specific topic:

```bash
# Free-form — interviewer picks topics
/ask ie
/ask ip
/ask if

# Topic-focused — all 6 challenges constrained to these areas
/ask ie migration safety and test isolation
/ask ip user onboarding
/ask if competitive moats and go-to-market
```

**Session structure:**
1. System presents challenge (1/6)
2. You answer
3. System evaluates (What you nailed / What to consider / Senior take)
4. System presents next challenge (2/6)
5. Repeat through (6/6)
6. System presents end-of-session scorecard

**During the session:**
- **Strong answers** → harder follow-ups, added constraints
- **Weak answers** → hints, simpler angles, encouragement
- **Stuck** → two concrete options to choose between (lifeline)
- **1-2 wildcard questions** — general/conceptual questions on the same
  topic but not about this codebase, inserted at random positions

**End-of-session scorecard includes:**
- Overall rating: Foundation / Developing / Proficient / Senior
- Strongest areas with examples from your answers
- Areas to develop with what you missed and why it matters
- Senior comparison — how your thinking compares
- Topic heatmap — visual bars per category
- Copy-pasteable recommended next session command

### Topic-Focused Interviews

The scorecard's recommendation is directly runnable:

```
SESSION COMPLETE — Engineering Interview (6/6)
...
Recommended next session:
  Focus on migration safety and test isolation.
  Run: /ask ie migration safety and test isolation
```

Copy the command, paste it, and the next session focuses on your weak areas.
This creates a continuous improvement loop.

---

## Examples

### Founder asking about the product

```
/ask founder what can this product do?
```

Output (plain English, no jargon):

```
ASK — What can this product do?
───────────────────────────────────────────────────────

Manifesto is a supply chain management tool that helps teams manage
vendors, track shipments, and get instant AI-powered answers from
company documents.

- Users can manage their full vendor list and product catalog.
- The system tracks shipments through their entire journey.
- Users can upload company documents and the AI reads and stores them.
- There's a built-in AI assistant that answers questions in plain English.
- Access is controlled by role: admins, managers, and employees.

───────────────────────────────────────────────────────
You might also want to know:
  1. How far along is the product?
  2. What does it look like when someone opens it right now?
```

### PM asking about feature status

```
/ask pm what's the state of shipments?
```

Output (feature-oriented, gap analysis):

```
ASK — State of shipments
───────────────────────────────────────────────────────

Shipments has a solid data foundation but is missing key capabilities.

- Built — Create, view, list, and delete shipments
- Built — Full lifecycle tracking with exception states
- Built — AI-powered Q&A over shipment data
- Missing — Users can't edit a shipment after creating it
- Missing — No frontend management UI (placeholder page)
- Missing — No filtering, search, or pagination

───────────────────────────────────────────────────────
Related questions:
  1. What's the gap analysis for the frontend?
  2. What user flows exist today for managing vendors?
```

### Engineer asking about architecture

```
/ask eng how does auth work?
```

Output (full technical detail, code snippets, diagrams):

```
ASK — How does auth work?
Route: Standard | Direct | Confidence: HIGH
───────────────────────────────────────────────────────

Auth is JWT-based with bcrypt password hashing and a FastAPI dependency
chain for per-route access control.

[ASCII sequence diagram]
[Code snippets with file:line references]
[Dependency chain walkthrough]
[Notable gaps section]

───────────────────────────────────────────────────────
Sources: backend/app/api/v1/auth.py:13-25, ...
Follow-up questions:
  1. What roles exist and which endpoints are gated?
  2. Is the JWT secret configuration production-safe?
```

### Engineering interview session

```
/ask ie
```

Output:

```
INTERVIEW — Engineering Challenge (1/6)
───────────────────────────────────────────────────────

[Code snippet from the actual codebase]

Challenge: What are the tradeoffs of this pattern? Think about
testability, configuration changes, and error recovery.

───────────────────────────────────────────────────────
Think out loud. I care more about your reasoning than the "right" answer.
```

---

## Persona Aliases

Quick reference for all available aliases:

| Full name | Short aliases |
|-----------|---------------|
| `founder` | `nontechnical`, `plain`, `simple` |
| `pm` | `product`, `product-manager` |
| `engineer` | `eng`, `dev`, `senior`, `technical` |
| `interviewer-founder` | `interview-founder`, `if` |
| `interviewer-pm` | `interview-pm`, `ip` |
| `interviewer-eng` | `interview-eng`, `ie` |

---

## Architecture

### Files

| File | Purpose |
|------|---------|
| `.claude/commands/ask.md` | Command definition — pipeline logic, tier system, presentation frames |
| `.claude/persona-profiles.json` | Persona definitions — prompts, aliases, question banks, forge templates, interviewer rules |
| `.claude/stack-profile.json` | Technology stack anchors — answers reference project's actual stack, not generic advice |
| `.forge/report.json` | Codebase scan data — file categories, import graph, hub files (generated by `forge_scan.py`) |
| `hooks/forge_scan.py` | Deterministic codebase scanner — no LLM calls |

### Tiered Pipeline

| Tier | Tool calls | Output | Forge scan | Agents | When |
|------|-----------|--------|------------|--------|------|
| **Quick** | ≤2 | ≤150 words | No | No | Fact lookups, yes/no, "where is X?" |
| **Standard** | ≤6 | 200-500 words | No | No | "How does X work?", status, enumerations |
| **Deep** | ≤15 | 500-1500 words | Yes | Possible | Cross-domain, diagnostics, reviews |

### Token Budgets

| Scenario | Estimated cost | Notes |
|----------|---------------|-------|
| Quick question (no persona flag) | ~3-6k tokens | Fast path: no persona file read |
| Quick question (with persona) | ~5-8k tokens | Reads persona-profiles.json |
| Standard question | ~15-20k tokens | |
| Deep question (with agent) | ~50-70k tokens | |
| Follow-up question | ~5-15k tokens | |
| Interview challenge (per question) | ~10-20k tokens | |
| Full interview session (6 challenges) | ~80-150k tokens | Opt-in only |

---

## Adding New Personas

Add a new key to `.claude/persona-profiles.json`:

```json
{
  "your-persona": {
    "name": "Display Name",
    "aliases": ["your-persona", "yp", "short-alias"],
    "prompt": [
      "Line 1 of the persona instructions.",
      "Line 2 — rules, tone, formatting constraints.",
      "These control how answers are generated."
    ],
    "questions": {
      "evergreen": [
        "Always-relevant question 1",
        "Always-relevant question 2"
      ],
      "contextual_templates": {
        "hub_file": "Question template about {area}",
        "open_issue": "Question template about issues",
        "recent_change": "Question template about changes",
        "domain_gap": "Question template about gaps"
      }
    },
    "forge_templates": {
      "hub_file": "Improve {area} — {action} to {outcome}",
      "open_issue": "Fix {issue_summary} — {root_cause} with {test_approach}",
      "recent_change": "Extend {area} — add {next_capability} building on {recent_work}",
      "domain_gap": "Add {missing_component} — {scope_description} so {user_role} can {user_action}"
    }
  }
}
```

The `forge_templates` field is optional. If omitted, the "Build next"
section is skipped for that persona (appropriate for interviewer personas).
Template placeholders are filled with concrete values from the codebase
scan — never generic descriptions.

No changes to `ask.md` needed — the command reads personas dynamically
from the config file.

For **interviewer personas**, the `prompt` array must additionally include:
- Topic focus handling
- Session structure (6 challenges)
- Wildcard question rules
- Difficulty scaling rules
- Evaluation structure (4-part)
- End-of-session scorecard template with topic heatmap

See the existing `interviewer-eng` persona for a complete example.

---

## Design Decisions

The `/ask` system evolved through several design iterations. Key decisions
are recorded in `DECISIONS.md` under **D55**.

**Why personas instead of flags?**
Personas bundle language rules, formatting, presentation frames, and
question banks into a single selectable identity. A flag system (`--no-code`,
`--plain-english`, `--gap-analysis`) would require users to compose the
right combination every time.

**Why 3 tiers instead of 10 routes?**
The original system had 10 classification routes (domain-expert, review,
process, historical, inventory, flow, diagnostic, time-sensitive, meta,
quantitative). Each question went through a multi-step classification
ceremony regardless of complexity. The 3-tier system (Quick/Standard/Deep)
cuts instruction overhead by 55% and makes the majority of questions
(Quick + Standard = ~95%) significantly cheaper.

**Why interviewer personas are in the same system?**
Interview mode reuses the same persona selection, question bank, and
pipeline infrastructure. The only difference is behavioral — interviewer
personas ask instead of answer. Keeping them in the same system means
topic focus, session management, and the improvement loop all work without
new infrastructure.

**Why "Build next" forge prompts in the question bank?**
The question bank's purpose is guided discovery — helping the user find
what matters. But discovery without action creates a gap: the user learns
"shipments can't be edited" and then has to manually translate that into
a forge-able task. "Build next" closes that gap by generating forge-ready
prompts from the same contextual data the question bank already gathered.
The persona controls the language: a founder sees user value, a PM sees
capabilities, an engineer sees technical scope. No extra tool calls —
the data is already in context from Step 2.

**Why wildcard questions?**
Pure codebase-grounded challenges test applied knowledge but miss broader
pattern recognition. Wildcards ("When is eventual consistency acceptable?",
"How did Slack's onboarding inform their retention?") test whether the user
can connect specific codebase knowledge to general principles — which is
what separates senior-level thinking from mid-level execution.

---

## Testing

### Test each persona produces the right voice

```bash
/ask founder what can this product do?    # Should: plain English, no jargon
/ask pm what's the state of shipments?    # Should: feature status, gap analysis
/ask eng how does auth work?              # Should: code snippets, file:line refs
```

**Check for persona leaks:**
- Founder: no file names, no function names, no acronyms
- PM: no HTTP methods, no database terms, no raw enums
- Engineer: full technical detail present

### Test the question bank

```bash
/ask founder questions    # Should: plain-English questions
/ask pm q                 # Should: product-oriented questions
/ask eng q                # Should: technical questions
```

**Check:** questions should be contextual (reference real codebase state),
not just generic templates.

**Check forge prompts:**
- A "Build next" section appears below the question selection
- Each prompt starts with `/forge`
- Prompts reference real gaps (not "add feature X" generically)
- Founder prompts use plain language about user value
- PM prompts describe capabilities and user flows
- Engineer prompts include technical scope and test coverage
- No prompts suggest building something that already exists

### Test the tier system

```bash
/ask where is the shipment model?           # Should: Quick tier (1-2 tool calls)
/ask how does the auth dependency chain work? # Should: Standard tier (3-6 tool calls)
/ask how does data flow from upload to AI?   # Should: Deep tier (agent or 10+ tool calls)
```

### Test interview mode

```bash
/ask ie    # Should: engineering challenge grounded in real code
```

**Check:**
- Challenge references actual code from this repo
- Progress shows (1/6)
- After answering, evaluation uses 4-part structure
- After 6 challenges, scorecard appears with heatmap

### Test topic-focused interviews

```bash
/ask ie auth and security    # Should: all challenges about auth/security code
```

**Check:** challenges are constrained to the specified topic area.

### Test the improvement loop

After a session completes, the scorecard should include a recommended
next session command that is directly copy-pasteable and runnable.
