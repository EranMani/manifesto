## /verify-commit — slash command

Verify the pending commit against current working-tree changes.

Do the following:

1. Read `project-state.json` and get `next_commit` and `next_commit_assignee`.

2. Run the verification script in worktree + no-persist mode:
   ```
   python hooks/verify_constraints.py --commit <next_commit> --agent <next_commit_assignee> --worktree --no-persist
   ```
   This checks uncommitted changes and returns PASS/FAIL without writing any records.

3. Parse and present the output as a clear summary to Eran with three lines:
   - [1] Context block:    PASS / FAIL
   - [2] Forbidden paths:  PASS / FAIL / WARNING
   - [3] Phase budget:     PASS / FAIL / WARNING

   ⚠️ WARNING on phase budget = agent didn't self-report. Not a hard failure, but flag it.

4. If any check FAILED:
   - Flag as a protocol violation.
   - Do NOT proceed to commit.
   - Surface the specific violation to Eran and ask how to address it.

5. If all checks PASSED (or warnings only):
   - Proceed to the commit proposal.
   - Permanent records (CONSTRAINT_LOG.md, CONTEXT_METRICS.json, constraint-dashboard.html)
     are written automatically when the git commit command runs via verify_constraints.py
     without --no-persist.

Note: This command checks the working tree (staged and unstaged changes vs HEAD). It does
NOT persist any records — persistence only happens after the git commit succeeds.
