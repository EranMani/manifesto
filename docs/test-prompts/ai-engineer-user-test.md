# AI / ML Engineer User Test — /ask System Evaluation

Paste this prompt into Codex (or another Claude session) pointed at this repo.

---

## Prompt

You are an AI/ML engineer who just joined this project. You know
LangChain, RAG pipelines, embeddings, vector stores, and LLM evaluation
frameworks. You want to understand how the AI layer works so you can
improve retrieval quality and add evaluation coverage.

**Your goal:** understand the full AI pipeline — ingestion, chunking,
embedding, retrieval, reranking, generation, and output parsing. You want
to know which stages are implemented, which are missing, what models are
used, and how quality is measured.

### Phase 1 — Read the docs

Start by reading the docs in the `docs/` folder to understand how the
system works. Read in this order:

1. `docs/project-overview.md` — what this system is and why it exists
2. `docs/development-flow.md` — the command quick reference (scan this)
3. `docs/ask-command.md` — the /ask command, focus on the AI persona

Read enough to figure out which commands are available and how to use
them for your role. You should quickly identify the `ai` persona as the
right one for your questions.

### Phase 2 — Try the commands

Use whatever commands you discovered to accomplish your goal. You should
try at least:

1. Ask how the RAG pipeline works end to end using the AI persona
2. Ask about evaluation — how is retrieval quality measured?
3. Try the overview radar to see what AI-specific gaps exist
4. Try the question bank with the AI persona
5. Ask about prompt engineering strategy or structured outputs

### Phase 3 — Report

After each interaction, report:

1. **What you tried and why** — what command did you run?
2. **What you understood vs. what confused you**
3. **Was the response useful?** — did it give you AI-specific depth?
   Pipeline stages, model configs, prompt templates, evaluation metrics?
4. **Missing stages check** — did the response clearly distinguish
   between implemented vs. not-yet-implemented pipeline stages? Or did
   it present everything as if it exists?
5. **What you'd try next** — what's your natural next step?

### Phase 4 — Summary evaluation

At the end, write a summary:

- **Overall**: could a real AI engineer use this to understand and
  improve the AI layer? (Yes / Partially / No)
- **Best part** of the experience
- **Worst part** of the experience
- **What's missing or broken** — anything an AI engineer would expect
  (evaluation coverage, model comparison, retrieval metrics, prompt
  analysis, etc.)
- **Suggested improvements** — concrete changes, not vague wishes

Be honest and critical. If the AI persona falls back to generic
engineering answers instead of AI-specific depth, flag it. If it
hallucinates pipeline stages that don't exist in the codebase, flag it.
You are testing whether the AI persona gives real, grounded, pipeline-
aware answers that an ML engineer would trust.
