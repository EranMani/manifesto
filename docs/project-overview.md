# Manifesto — Project Overview

One person. Every hat. AI handles the rest.

---

## What This Is

Manifesto is a development system that lets a single person build a
complete, production-grade application by wearing every role — backend
engineer, frontend engineer, DevOps, product manager, security reviewer,
and founder — with AI agents filling the expertise gaps.

The bottleneck for a solo builder is not writing code. It's knowing
**what to think about** across domains you can't all be expert in
simultaneously. A backend engineer forgets to check CORS. A founder
skips input validation. A PM doesn't know the database can't handle the
query pattern they're requesting.

Manifesto solves this by surfacing the questions each domain expert would
ask, translating identified gaps into buildable tasks, and executing them
with verification at every step — so one person can ship fast without
shipping blind.

---

## The Core Loop

Everything flows through three commands:

```
   Understand           Plan              Execute
  ┌──────────┐      ┌──────────┐      ┌──────────┐
  │  /ask    │ ──►  │  /forge  │ ──►  │/next-step│
  │          │      │          │      │          │
  │ What's   │      │ Turn gap │      │ Build it,│
  │ missing? │      │ into a   │      │ verify,  │
  │ What's   │      │ validated│      │ commit   │
  │ risky?   │      │ plan     │      │          │
  │ Build ►  │      │          │      │          │
  └──────────┘      └──────────┘      └──────────┘
       │                                    │
       └────────────────────────────────────┘
                  (cycle back)
```

### /ask — Understand

Ask questions in the language you're thinking in right now.

- **As a founder**: `/ask founder what can this product do?` — plain
  English, no jargon, business outcomes
- **As a PM**: `/ask pm what features are built vs. missing?` — feature
  status, gap analysis, user flows
- **As an engineer**: `/ask eng how does auth work?` — file paths, code
  snippets, architecture diagrams

The question bank (`/ask pm q`) generates guided questions **and**
forge-ready prompts from the actual codebase state. You don't need to
know what to ask or how to phrase the build task — the system does both.

### /forge — Plan

Give it a task in plain English. It scans the codebase, consults domain
agents for design input, challenges the design for flaws, decomposes into
atomic commits, and generates validated specs.

```bash
/forge add shipment editing — PATCH endpoint with role-based access
```

Output: commit specs with 14 required sections, updated protocol, ready
for execution. No code changes — just a validated plan.

### /next-step — Execute

Execute the plan one commit at a time, or let auto mode run the full
sequence unattended.

```bash
/next-step --auto    # auto-approve clean preflights, loop all commits
```

Each commit goes through: preflight check, implementation, verification,
constraint check, finalization, commit, state advancement. If anything
fails, it stops safely.

---

## Why It Works for One Person

### The Problem

A solo builder faces an impossible tradeoff: move fast and miss things,
or be thorough and move slowly. The domains compound:

- **Backend**: API design, data models, migrations, error handling
- **Frontend**: components, state management, responsiveness, accessibility
- **DevOps**: containers, CI/CD, infrastructure, monitoring
- **AI/ML**: retrieval quality, hallucination risk, prompt robustness
- **Security**: auth flows, input validation, secrets, attack surfaces
- **Product**: user flows, gap analysis, prioritization, scope decisions
- **Strategy**: moat, go-to-market, competitive positioning, resource allocation

No single person thinks in all these frames simultaneously. You default
to the hat you're most comfortable wearing and miss everything else.

### The Solution

Manifesto doesn't replace domain expertise — it surfaces the domain
questions so you can't skip them.

**Personas** adapt the system's language to whichever hat you're wearing.
When you're thinking about product, the PM persona shows you feature
status and gap analysis. When you switch to engineering, the engineer
persona shows you file paths and architecture. Same codebase, different
lens.

**Guided discovery** means you don't need to know what to ask. The
question bank reads the codebase state and generates the questions each
persona would care about — plus actionable forge prompts to start
building immediately.

**Interview mode** challenges your thinking. The system asks *you*
questions grounded in your actual codebase — pushing you to think about
edge cases, tradeoffs, and risks you'd otherwise skip. After a session,
the scorecard identifies weak areas and suggests both focused practice
sessions and concrete forge prompts to strengthen the codebase.

**Atomic commits with verification** mean every change is independently
tested, constraint-checked, and reversible. You move fast because the
system catches mistakes before they compound.

**Stack anchors** mean every agent knows the project's chosen
technologies, patterns, and principles before making any recommendation.
Rex knows the backend is FastAPI + SQLAlchemy + Celery. Nova knows AI
orchestration is LangChain + LangGraph with pgvector. Adam knows
deployment is Docker Compose on a VPS with Nginx. No agent wastes time
rediscovering the stack or recommending technologies that don't fit — the
`.claude/stack-profile.json` is their shared source of truth — and each
agent loads only their domain detail file, not the entire 50KB playbook.

---

## The Stack Profile

The stack profile uses **tiered context loading** — the same pattern it
recommends for AI systems:

- **Level 0** (`.claude/stack-profile.json`, ~8KB): philosophy, engineering
  methodology, testing mandates, and one-line summaries per domain. Every
  agent reads this.
- **Level 2** (`.claude/stack/{domain}.json`): full detail for one domain.
  Each agent loads only their file when working.

```
.claude/
├── stack-profile.json              ← Level 0: philosophy + abstracts
├── stack/
│   ├── backend.json                ← Rex: backend + database
│   ├── frontend.json               ← Aria: frontend
│   ├── ai.json                     ← Nova: AI, RAG, retrieval, context
│   ├── infrastructure.json         ← Adam: infra, observability, tiers
│   ├── security.json               ← Sage: auth, webhooks, AI security
│   └── product.json                ← Mira: product strategy, delivery
```

| Domain | Owner | Core Technologies |
|--------|-------|------------------|
| **Backend** | Rex | Python 3.12+, FastAPI, Pydantic, SQLAlchemy, Alembic, Celery, Redis, PostgreSQL |
| **Frontend** | Aria | TypeScript, React 18+, Vite, Tailwind CSS, shadcn/ui, Zustand |
| **AI/ML** | Nova | LangChain, LangGraph, Langfuse, hybrid RAG (BM25 + vectors + RRF + cross-encoder), pgvector/numpy |
| **Infrastructure** | Adam | Docker, Docker Compose, Nginx, GitHub Actions, VPS, Grafana, Celery Beat |
| **Security** | Sage | JWT + refresh tokens, bcrypt, rate limiting, CORS whitelist, webhook signature verification |
| **Product** | Mira | Discovery protocol, sprint model, scoping, accuracy paradigm, delivery methodology |

Each domain file includes **technologies** (what to use), **patterns**
(how to use them), and **principles** (when and why). The AI domain
includes a complete hybrid RAG pipeline specification with BM25 sparse
retrieval, dense embeddings, RRF fusion, cross-encoder reranking, and
NDCG@10 evaluation. The infrastructure domain includes a three-tiered
operational architecture (triggers → schedules → agents).

The stack profile shapes every decision in the pipeline:
- **`/ask`** answers reference the project's actual stack, not generic advice
- **`/forge`** Phase 3 agents load their domain file and recommend within the chosen technologies
- **`/forge`** Phase 3.5 challenges validate against stack constraints
- **`/next-step`** implementations use the patterns defined in the profile

---

## The Agent Team

You're not alone — you have a team of specialist agents:

| Agent | Role | What They Do |
|-------|------|-------------|
| **Claude** | Orchestrator | Default implementor, routes work, reviews everything |
| **Rex** | Backend Engineer | Python, FastAPI, SQLAlchemy, API design, data models |
| **Aria** | Frontend Engineer | React, TypeScript, components, state, UI |
| **Nova** | AI/ML Engineer | LLM services, RAG pipelines, ingestion, embeddings |
| **Adam** | DevOps Engineer | Docker, hooks, scripts, infrastructure, automation |
| **Viktor** | Code Reviewer | Cross-domain quality review, reads everything, touches nothing |
| **Sage** | Security Reviewer | Auth, secrets, input validation, attack surface analysis |
| **Mira** | Product Reviewer | User-facing behavior, UX decisions, advisory |

All agent communication routes through Claude. No direct agent-to-agent
contact. Claude delegates only when specialist expertise genuinely
justifies the cost — not just because a file is "owned" by an agent.

---

## The Safety Net

Building fast means nothing if you ship broken code. Every commit passes
through:

1. **Preflight check** — validates the spec, dependencies, and ownership
   before any code is written
2. **Implementation** — edits only the files listed in the approved spec
3. **Focused verification** — runs the spec's test command
4. **Constraint verification** — automated checks for budget, scope, and
   protocol compliance
5. **Finalization** — pre-commit artifacts and marker validation
6. **Pre-commit hook** — enforces domain boundaries at the git level
7. **State advancement** — project state, protocol, and token records
   are all updated atomically

If any step fails, the system stops and explains why. In auto mode, it
stops safely and waits for you. No silent failures, no half-applied
changes.

---

## Breaking the Flow

The system is designed to be interrupted at any point:

### When to break

- **Preflight blocked**: a dependency isn't met, or a decision is needed.
  The system shows you what's wrong and waits.
- **Verification fails**: the implementation doesn't pass tests. After 2
  repair cycles, it stops and asks for guidance.
- **Scope exceeded**: the task can't fit the approved budget. The system
  returns `SPLIT_REQUIRED` with completed work and a proposed split.
- **User interrupts auto mode**: send any message and the loop stops
  after the current step completes.
- **Quality gate finding**: Viktor, Sage, or Mira raises a blocking
  issue. It becomes the next commit — there are no gate-fix passes.

### When to go back

- After any `/next-step` completes, run `/ask` to verify what was built
  and identify new gaps
- After an interview session exposes a weakness, paste the "Act on this"
  forge prompt to fix it
- After a `/forge` plan, run `/ask eng` to sanity-check the approach
  before executing
- After 5+ follow-up questions, `/ask` suggests specific forge prompts
  from the conversation context

### What you never lose

- **Every commit is atomic** — independently testable and reversible
- **State is always consistent** — project-state.json, commit-protocol.md,
  and TOKEN_RECORDS.md are advanced together
- **Token records have no gaps** — every commit gets a row, providing
  full observability
- **Git history is never rewritten** — no amends, no force pushes, no
  silent overrides

---

## The Full Pipeline

From zero knowledge to committed code:

```
/ask pm q
  │
  │  "What features are built vs. missing?"
  │  "What user flows are incomplete?"
  │
  │  BUILD NEXT:
  │    /forge add shipment editing — PATCH endpoint with role-based access
  │    /forge build vendor dashboard — frontend for existing CRUD
  │
  ├── (paste a forge prompt)
  │
  ▼
/forge add shipment editing — PATCH endpoint with role-based access
  │
  │  Phase 1: Intent → feature, backend, keywords: shipment, editing
  │  Phase 2: Scan → identifies target files, hubs, ownership
  │  Phase 3: Agent design input → Rex recommends approach
  │  Phase 3.5: Design challenge → checks for architecture/security flaws
  │  Phase 4: Decompose → C80 (backend) → C81 (frontend)
  │  Phase 5: Generate specs → 14 sections each, validated
  │  Phase 6: Present → approval card
  │
  ├── (user approves or adjusts)
  │
  ▼
/next-step --auto
  │
  │  C80: preflight → implement → verify → commit → advance state
  │  C81: preflight → implement → verify → commit → advance state
  │  No more pending commits → stop
  │
  ▼
/ask pm what's the state of shipments now?
  │
  │  "Built — full CRUD including editing"
  │  (cycle complete, identify next gap)
```

---

## The Training Dimension

Beyond building, the system trains your thinking:

```bash
/ask ie auth and security    # engineering interview, 6 challenges
/ask ip user onboarding      # product interview, 6 challenges
/ask if competitive moats    # founder interview, 6 challenges
```

Every challenge is grounded in your actual codebase — real code, real
gaps, real issues. The scorecard at the end shows where you're strong,
where you need work, and gives you two paths forward:

- **Learn more**: `/ask ie migration safety` — next focused session
- **Build it**: `/forge add migration safety checks` — fix the weakness

This creates two reinforcing loops: one that builds your skills and one
that builds your product. The same session that sharpens your thinking
also surfaces concrete work to strengthen the codebase.

---

## File Map

```
.claude/
├── commands/
│   ├── ask.md                    ← /ask command (personas, tiers, Q&A)
│   ├── forge.md                  ← /forge command (6-phase pipeline)
│   └── next-step.md              ← /next-step command (execution engine)
├── persona-profiles.json         ← 6 personas with prompts, questions, forge templates
├── stack-profile.json            ← Level 0 abstract — philosophy, methodology, domain summaries
├── stack/                        ← Level 2 domain details (loaded per agent)
│   ├── backend.json              ← Rex: Python, FastAPI, Pydantic, SQLAlchemy, Celery, PostgreSQL
│   ├── frontend.json             ← Aria: TypeScript, React, Vite, Tailwind, shadcn/ui
│   ├── ai.json                   ← Nova: LangChain, LangGraph, hybrid RAG, context architecture
│   ├── infrastructure.json       ← Adam: Docker, Nginx, CI/CD, operational tiers, observability
│   ├── security.json             ← Sage: JWT, auth, webhook security, AI security
│   └── product.json              ← Mira: discovery, sprint model, delivery, scaling
└── settings.json                 ← Claude Code configuration

hooks/                            ← Verification and automation pipeline
├── forge_scan.py                 ← Deterministic codebase scanner
├── forge_planner.py              ← Commit decomposition engine
├── preflight_commit.py           ← Pre-execution readiness check
├── verify_constraints.py         ← Post-implementation constraints
├── finalize_commit.py            ← Pre-commit finalization
├── pre_commit_check.py           ← Git hook: domain enforcement
├── validate_commit_spec.py       ← Spec validation (14 sections)
├── agent-config.json             ← Agent definitions and domains
└── ...                           ← Telemetry, budget, delegation, notifications

commit-specs/                     ← Validated commit specifications
docs/                             ← Command and flow documentation
.forge/                           ← Scan and planning output

project-state.json                ← Current position and state
commit-protocol.md                ← Commit index and status
AGENTS.md                         ← Agent roster and domain boundaries
CLAUDE.md                         ← Operating contract
DECISIONS.md                      ← Architectural decision log
TOKEN_RECORDS.md                  ← Per-commit token records
```

---

## Documentation Map

| Doc | What it covers |
|-----|---------------|
| [docs/development-flow.md](development-flow.md) | The complete ask → forge → next-step pipeline, command quick reference, architecture, installation guide |
| [docs/ask-command.md](ask-command.md) | /ask in depth: personas, question bank, interview mode, tiers, token budgets |
| [docs/forge-command.md](forge-command.md) | /forge in depth: 6 phases, decomposition rules, error recovery |
| [docs/next-step-command.md](next-step-command.md) | /next-step in depth: execution modes, commit lifecycle, auto mode, hooks |
| [docs/project-overview.md](project-overview.md) | This file — the why, the what, the how |
| .claude/stack-profile.json | Level 0 stack abstract — philosophy, methodology, domain summaries |
| .claude/stack/*.json | Level 2 domain details — one file per agent, loaded only when active |
| CLAUDE.md | Operating contract — boot sequence, approval rules, execution protocol |
| AGENTS.md | Agent roster, domain boundaries, cross-agent communication |
| DECISIONS.md | Architectural decision log with rationale |

---

## The End Goal

One person builds a full-stack, AI-powered, production-grade application
— backend, frontend, infrastructure, AI services — with the confidence
that nothing critical was missed.

Not by working harder. Not by knowing everything. By having a system
that asks the right questions at the right time, translates answers into
build tasks, executes with verification, and trains your thinking in the
gaps between builds.

The measure of success is not how much code the agents write. It's how
many domain blind spots the system catches before they become bugs,
security holes, or product failures — and how fast one person can go
from "I have an idea" to "it's live and it works."
