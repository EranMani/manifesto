# Product Concept: Assistant Action Badges

## Summary

When a user asks the assistant about a shipment, the assistant understands the
current state and suggests 2-3 clickable action badges — guiding the user
through what to do next instead of leaving them to figure it out alone.

The user clicks a badge to confirm the action. The assistant handles the rest
or continues the conversation with a short confirmation step.

**Interaction model:** Suggest and confirm. The assistant paves the path; the
user decides.

---

## Why This Matters

Today the assistant answers questions. Tomorrow it guides decisions.

- Users don't need to know what's possible — the system shows them.
- No context-switching to other screens or tools.
- The guidance is contextual — it comes from the actual shipment data, not a
  generic menu. A delayed shipment shows different badges than a delivered one.
- Over time, this becomes impossible to replicate without the same procurement
  graph connecting vendors, orders, shipments, products, and events.

---

## How It Works

1. User asks about a shipment (e.g., "where is TRK-4521?")
2. Assistant retrieves the shipment, its status, latest events, and related data
   (vendor, purchase order, client, timeline)
3. Assistant answers the question in natural language
4. Below the answer, 2-3 contextual action badges appear based on the current
   shipment status and latest event
5. User clicks a badge
6. Assistant confirms the action with a short prompt ("Notify vendor ABC about
   the customs delay on TRK-4521. Add a message?")
7. User confirms or adjusts
8. Action executes; conversation continues naturally

---

## Status-to-Badge Mapping

### Pending (ordered but not moving yet)

| Badge | Why |
|-------|-----|
| Ask vendor for dispatch date | Shipment exists but nothing's happened |
| Change expected arrival | It's clear it won't ship on time |
| Cancel order | Vendor is unresponsive |

### In Transit (moving normally)

| Badge | Why |
|-------|-----|
| Track next update | Remind me when the next event arrives |
| Notify client | Let the buyer know it's on its way |
| Flag concern | Something feels off but no event yet |

### Delayed (delay reported)

| Badge | Why |
|-------|-----|
| Ask vendor for explanation | Get a reason if none exists |
| Extend delivery estimate | Update the expected arrival for the buyer |
| Escalate to manager | Delay is serious or repeated |
| Check vendor history | Has this vendor been late before? |

### Customs Hold (event: customs_hold)

| Badge | Why |
|-------|-----|
| Contact vendor about docs | Vendor usually handles clearance paperwork |
| Extend delivery estimate | Customs delays are unpredictable |
| Watch for release | Notify me when customs is cleared |

### Damaged

| Badge | Why |
|-------|-----|
| File claim with vendor | Start the damage process |
| Request replacement | Initiate a new order |
| Document damage | Attach photos or notes |
| Check policy | What does our policy say about damaged goods? |

### Partial Delivery

| Badge | Why |
|-------|-----|
| Confirm what arrived | Reconcile received vs. expected items |
| Request remaining items | Ask vendor to ship the rest |
| Adjust purchase order | Update quantities if accepting partial |

### Cancelled

| Badge | Why |
|-------|-----|
| Request refund | Money back |
| Reorder from same vendor | Try again |
| Find alternate vendor | Switch suppliers |

### Returned

| Badge | Why |
|-------|-----|
| Confirm vendor received return | Close the loop |
| Request credit/refund | Get the money back |
| Reorder | If the goods are still needed |

### Lost

| Badge | Why |
|-------|-----|
| File claim | Insurance or vendor liability |
| Reorder urgently | The goods are needed |
| Notify client | Manage expectations |

---

## Role-Based Badge Logic

### Managers (admin, manager roles)

See the full operational badges above. They can act on shipment data,
contact vendors, adjust orders, and escalate.

### Employees (employee role)

Employees only access policy answers. Their badges are:

| Badge | Why |
|-------|-----|
| Read full policy | Link to the relevant policy document |
| Ask a follow-up | Pre-filled clarification questions |
| Talk to my manager | Escalation path when policy doesn't cover their case |
| Report an issue | Something happened that policy should address |

---

## Design Principles

1. **Maximum 3 badges per answer.** More than 3 creates decision fatigue —
   the opposite of guiding. Pick the most relevant based on status + latest event.

2. **Badges are contextual, not generic.** "Notify vendor" isn't always shown.
   It appears because the system knows who the vendor is and that contacting
   them is the logical next step for this specific situation.

3. **Clicking a badge continues the conversation.** It doesn't open a new screen
   or a form. The assistant responds with a confirmation step, and the user
   stays in the same flow.

4. **Suggest and confirm.** No badge auto-executes. The user always sees what
   will happen and says yes. Trust is built by being right consistently, not
   by acting without permission.

5. **The assistant explains why.** Each badge can have a one-line reason shown
   on hover or inline: "This vendor usually handles customs clearance paperwork."

---

## What This Unlocks Later

Once users trust the badge suggestions (they're consistently right):

- **Auto-execute low-risk actions** — status notifications that are always
  appropriate can skip the confirmation step
- **Proactive alerts** — "Shipment TRK-4521 just hit customs. Last time this
  vendor had a 4-day customs delay. Want me to extend the estimate now?"
- **Workflow chains** — one badge leads to another. "File claim" → "Attach
  evidence" → "Notify client about delay" → "Reorder from alternate vendor"
- **Learning from choices** — which badges do users click most? Which do they
  ignore? Refine suggestions over time.

---

## Open Questions for Product

- Should badges persist after the answer, or disappear once the user scrolls?
- Should there be a "More actions" overflow for the less common options?
- Should clicked badges leave a visible trail in the conversation (so the user
  can see what they did)?
- How do we handle badges for actions that require data we don't have yet
  (e.g., "Document damage" when no photo upload exists)?
- Should the assistant proactively surface badges even when the user didn't
  ask a question (e.g., on shipment status change events)?
