Invoke Quinn for an ad-hoc coverage review outside the commit loop.

Usage: /qa-check [optional: specific service, route, or feature to review]

Steps:

1. **Identify scope** — if the Team Lead specified an area, read the source and test files for it.
   If not, ask: "Which part of the codebase should Quinn review for test coverage?"

2. **Build Quinn's context package:**
   - Quinn's identity file: `.claude/agents/qa.md`
   - Quinn's Current State Header (coverage debt log from prior sessions)
   - The source files being reviewed
   - The existing test files for those sources

3. **Invoke Quinn** with the context package. Quinn produces a coverage review
   in her standard format (Coverage Map / Suggested Tests / Verdict).

4. **Route the verdict:**
   - ADEQUATE → inform Team Lead, no action needed.
   - NEEDS ADDITIONS → route gaps to owning agent via Claude with Quinn's suggested tests.
   - INSUFFICIENT → present to Team Lead. Work on the affected code should not continue
     until coverage is brought up to adequate.

5. **Log in Quinn's worklog** and update coverage debt log.
