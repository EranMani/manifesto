Invoke Viktor for an ad-hoc code review outside the commit loop.

Usage: /review-request [optional: specific files or areas to focus on]

Steps:

1. **Identify what to review** — if the Team Lead specified files, read those.
   If not, read the last commit's diff (`git diff HEAD~1 HEAD`).

2. **Build Viktor's context package:**
   - Viktor's identity file: `.claude/agents/reviewer.md`
   - Viktor's Current State Header
   - The files to review (full content, not just diff, for accurate context)
   - The commit spec for context on what was intended

3. **Invoke Viktor** with the context package. Viktor produces a review
   in his standard format (💬 / ⚠️ / 🚨 / What's Good / Verdict).

4. **Route the findings:**
   - 💬 Comments → present to Team Lead, ask if they want the owning agent notified
   - ⚠️ Concerns → route to owning agent via Claude, track resolution
   - 🚨 Hard Block → present to Team Lead immediately with full context

5. **Log in Viktor's worklog** under "Ad-hoc review — [date]"

This command does not require a commit to be in progress. It can be used at any time.
