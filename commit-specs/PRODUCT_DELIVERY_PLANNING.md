# Product Delivery Planning

> A reusable method for turning an early technical project into a testable product
> without losing engineering control.

## Start From The Demonstration

Define the shortest credible client story before decomposing implementation work:

1. Who is using the product?
2. What question or task do they bring?
3. What visible answer or action proves value?
4. What evidence makes the result trustworthy?
5. What must work in a clean demonstration environment?

Work backward from that experience. Infrastructure and hardening are supporting work,
not milestones unless a user can test a coherent capability when they finish.

## Use Two Planning Levels

**Product milestones** describe complete capabilities that a developer, client, or
investor can meaningfully test. They govern roadmap priority and require explicit
approval.

**Engineering commits** are small implementation units beneath those milestones. They
remain atomic, independently verified, and easy to review or revert.

Fewer commits do not automatically mean faster delivery. Compressing several behaviors
into one commit hides complexity and increases correction cost. Reduce scope by
deferring behavior, not by inflating commits.

## Commit Decomposition Rules

- One observable behavior and one owner.
- No more than two primary files or four changed files.
- Target 150-250 changed lines; 350 is the hard ceiling.
- One focused verification command.
- Do not combine schema, service, API, and UI work in one commit.
- Split work when exact contracts exceed the envelope.
- Every commit must reduce the distance to an observable product milestone.

## Milestone Rules

A milestone is ready only when all constituent acceptance criteria pass. Reaching a
commit number is not sufficient.

Every developer checkpoint publishes:

- exact startup command and URL or API request;
- a short manual test procedure;
- the expected visible result;
- known limitations and deferred behavior;
- what the next milestone adds.

## Hardening Strategy

Build infrastructure until it is dependable enough to support the demonstration.
Defer speculative sophistication until real demonstrations expose failures worth fixing.
Keep deferred work visible in a backlog so it is neither forgotten nor allowed to block
the primary product story.

Use the evidence source that matches the data:

- structured, allowlisted retrieval for authoritative operational records;
- document RAG for policies and explanatory material;
- focused evidence visualization for the facts supporting the current answer.

## Manifesto Worked Example

Manifesto's earlier Phase 2 roadmap put policy-chat ranking, streaming, persistence, and
frontend sophistication before its distinctive logistics demonstration. The engineering
sequence was controlled, but the first client-visible proof arrived too late.

The replan starts from one demonstration: a manager asks about a shipment, receives a
grounded verbal answer, and sees the supporting buyer, purchase order, vendor, shipment,
products, and event path. The same assistant still answers employee policy questions
from bundled mock documents.

The revised milestones are:

1. Demo data ready.
2. Logistics evidence ready.
3. Assistant backend ready.
4. Integrated prototype ready.
5. Client demo ready.

Advanced rank fusion, durable conversations, SSE streaming, cancellation, provider
selection, extensive metrics, and full-network exploration are deferred. They return
only when client testing or measured failures justify them.
