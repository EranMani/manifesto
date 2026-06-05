## /verify-commit — slash command
## Move this file to: .claude/commands/verify-commit.md

Run constraint verification for the most recently completed commit.

Do the following:

1. Read `project-state.json` and get `last_completed_commit` (e.g. "08") and
   `next_commit_assignee` to know which agent just ran.

2. Run the verification script:
   ```
   python hooks/verify_constraints.py --commit <last_completed_commit> --agent <assignee>
   ```

3. Parse and present the output as a clear summary to Eran with three lines:
   - [1] Context block:    PASS / FAIL
   - [2] Forbidden paths:  PASS / FAIL / WARNING
   - [3] Phase budget:     PASS / FAIL / WARNING

   ⚠️ WARNING on phase budget = agent didn't self-report. Not a hard failure, but flag it.

4. If any check FAILED:
   - Flag as a protocol violation.
   - Do NOT proceed to the next commit.
   - Surface the specific violation to Eran and ask how to address it.

5. If all checks PASSED (or warnings only):
   - Log one line in TOKEN_RECORDS.md under the commit row:
     `Constraints: context ✅ · forbidden ✅ · budget ✅`  (or ⚠️ where unverified)
   - Proceed to the next Commit Preview.

Note: If phase budget warnings recur across multiple commits for the same agent,
add "Tool usage: reads=N, writes=N, total=N" as a hard requirement in their identity file.
