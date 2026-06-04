Compress the oldest sessions of a specified agent's worklog to reduce context window consumption.

Usage: /archive-worklog [agent-name]
Example: /archive-worklog backend

Steps:

1. **Read the full worklog** for the specified agent.

2. **Identify sessions to archive:** the oldest 5 completed sessions
   (sessions with ✅ Done status in the session index).

3. **Write the Archive Entry** (max 20 lines) to the active worklog:
   ```
   ## Archive Entry — Sessions [N]–[M] (Commits [X]–[Y])
   Built: [comma-separated component list]
   Key decisions:
   1. [decision] — [one sentence why]
   2. [decision] — [one sentence why]
   Handoffs given: [list or none]
   Interfaces established: [key function signatures or route shapes]
   Known issues resolved: [list or none]
   [Full detail: [agent]-worklog-archive-[batch].md]
   ```

4. **Move the 5 sessions** to `[agent]-worklog-archive-[N].md`

5. **Update the Current State Header** to reflect the archive reference.

6. **Confirm:** "Archived sessions [N]–[M] for [agent]. Worklog is now [line count] lines."

This operation never loses information — the archive file contains the full original sessions.
It only removes them from the active worklog so they don't consume context on every invocation.
