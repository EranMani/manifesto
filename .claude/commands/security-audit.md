Invoke Sage for an ad-hoc security review outside the commit loop.

Usage: /security-audit [optional: specific files, features, or threat scenarios]

Steps:

1. **Identify scope** — if the Team Lead specified files, read those.
   If not, ask: "Which part of the codebase should Sage review? (e.g., all API routes, the auth layer, the external API integrations)"

2. **Build Sage's context package:**
   - Sage's identity file: `.claude/agents/security.md`
   - Sage's Current State Header (attack surface map from prior sessions)
   - The files to review
   - Any relevant architecture context (what's external vs internal, what's trusted vs untrusted)

3. **Invoke Sage** with the context package. Sage produces findings in her standard format.

4. **Route findings by severity:**
   - CRITICAL/HIGH → present to Team Lead immediately. Do not wait.
   - MEDIUM → present to Team Lead in the next approval prompt.
   - LOW/INFO → bundle into a summary for the Team Lead.

5. **Update Sage's attack surface map** in her worklog Current State Header.

6. **Log in Sage's worklog** under "Ad-hoc audit — [date]"
