# Phase 3 Graph-Aware Logistics RAG Design

**Reviewed:** 2026-06-08
**Scope:** Vendors, shipments, products, categories, and future logistics relationships
**Decision:** Adopt graph-aware relational retrieval; defer a separate graph database.

## Short Answer

Graph reasoning is valuable here. The entities are connected:

```text
Vendor -> Shipment -> Product -> Category
                    -> User (added_by)
```

However, "use GraphRAG" can mean two different systems:

1. Extract a knowledge graph from unstructured text, build communities, and retrieve graph
   summaries, as in Microsoft GraphRAG.
2. Traverse an existing authoritative entity graph and use the resulting facts to ground
   an answer.

Manifesto needs the second pattern for logistics. The graph already exists in PostgreSQL,
so copying it into a second database would add synchronization, authorization, backup,
deployment, and consistency costs before evidence shows a benefit.

## Proposed Architecture

### 1. Curated Domain Graph

Define a machine-readable allowlisted graph:

- node types, primary keys, safe display fields, and role visibility
- allowed edges and join keys
- edge direction and cardinality
- approved aggregate operations, filters, and time semantics
- sensitive or forbidden columns

The LLM never receives the unrestricted database schema.

### 2. Structured Query Planner

Classify each question and produce a typed plan rather than free-form SQL:

```json
{
  "intent": "aggregate",
  "start": "vendor",
  "path": ["vendor.shipments", "shipment.products"],
  "filters": [{"field": "vendor.country", "op": "eq", "value": "Germany"}],
  "metrics": [{"op": "sum", "field": "product.quantity"}],
  "group_by": ["vendor.name"]
}
```

Validate node types, edges, fields, operators, limits, and user role against the curated
graph. Compile the accepted plan into parameterized SQL. The model does not author the
final executable statement.

### 3. Retrieval Router

- **Direct lookup:** deterministic indexed SQL.
- **Aggregate/analytical:** validated graph plan compiled to joins and aggregates.
- **Multi-hop relationship:** bounded graph traversal over approved foreign-key paths;
  use recursive CTEs only if future relationships become variable-depth.
- **Semantic text:** pgvector/full-text search over product descriptions or shipment
  notes, followed by graph expansion to authoritative related entities.
- **Mixed policy/logistics:** retrieve relational facts and policy excerpts separately,
  then synthesize with distinct provenance.

### 4. Provenance

Return structured evidence with entity type, ID, display label, relationship path, applied
filters, aggregation definition, data freshness timestamp, and the generated SQL for
manager transparency. Answers cite entities and calculations, not vector chunks alone.

### 5. Performance

GraphRAG does not automatically reduce latency. For this fixed, shallow schema,
PostgreSQL joins with indexes are likely faster than an extra network hop plus duplicated
graph storage. Add composite indexes based on measured query patterns and cache only
normalized, authorization-safe plans/results with explicit invalidation.

Benchmark p50/p95 latency, plan-validation failure rate, execution accuracy, and answer
accuracy against:

- unconstrained text-to-SQL baseline
- graph-plan-to-SQL
- optional Neo4j proof of concept

## When Neo4j or Full GraphRAG Becomes Justified

Run a proof of concept only if one or more become true:

- relationships become variable-depth or many-to-many across many entity types
- path finding, dependency chains, centrality, communities, or recommendations become
  first-class product requirements
- policy documents must be entity-linked to operational records at high scale
- PostgreSQL traversal misses measured latency/accuracy targets
- change-data-capture and authorization semantics for a second store are funded

Microsoft GraphRAG may later help with corpus-wide policy analysis, but its LLM-based
indexing and community summarization are not a latency optimization for transactional
vendor/shipment/product questions.

## Phase 3 Quality Gates

- Versioned logistics evaluation set with lookup, aggregation, multi-hop, temporal,
  ambiguous, unauthorized, and adversarial questions.
- Exact-result accuracy and relationship-path accuracy.
- Zero execution of non-allowlisted tables, columns, edges, or write statements.
- Parameterized SQL only, read-only role, statement timeout, row limit, and cancellation.
- p95 latency budget measured on representative data volume.
- Every answer reproducible from persisted plan, parameters, SQL, and result metadata.

## Primary References

- Microsoft GraphRAG overview:
  https://microsoft.github.io/graphrag/index/overview/
- Microsoft GraphRAG query modes:
  https://microsoft.github.io/graphrag/query/overview/
- Neo4j GraphRAG retrieval patterns:
  https://neo4j.com/docs/neo4j-graphrag-python/current/
- PostgreSQL recursive queries:
  https://www.postgresql.org/docs/current/queries-with.html
