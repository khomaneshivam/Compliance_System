# ADR 0002: Regulatory Rule Representation and Temporal Versioning

## Status
**Accepted**

## Context
Statutory applicability in manufacturing depends on complex combinations of operational criteria (jurisdiction, industry category, equipment types, chemical thresholds, worker headcount). 
Furthermore, regulatory rules change over time when governments publish gazette amendments (e.g. altering the threshold for hazardous waste authorisations).

Overwriting rule logic in-place causes severe compliance flaws: historical audit reports lose their legal validity because past plant configurations would be re-evaluated against newly amended criteria.

## Decision
We decide to represent applicability rules using a **Declarative Abstract Syntax Tree (AST)** stored in PostgreSQL `JSONB` and enforce **Immutable Temporal Versioning**:

1. **AST Representation:**
   Rules are stored as JSON trees with standard logical and comparison operators (`==`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `and`, `or`).
   Example:
   ```json
   {
     "and": [
       { "==": ["plant.jurisdiction", "Maharashtra"] },
       { ">": ["plant.boiler_count", 0] }
     ]
   }
   ```
2. **Evaluation Engine:**
   A deterministic Python service evaluates the AST against a flattened dictionary of typed plant profile attributes. No generative LLMs are involved in determining formal statutory applicability.
3. **Temporal Versioning:**
   - Rules carry a monotonic `rule_version` integer and an `effective_from` date.
   - When a gazette amendment modifies an obligation, a new rule record is inserted with `rule_version = N + 1`.
   - Existing compliance records retain their historical evaluation snapshot, preserving audit integrity.

## Consequences
### Positive
- Zero risk of LLM hallucinations deciding statutory obligations.
- Complete explainability: the engine generates human-readable rationales explaining exactly which AST condition evaluated to true or false.
- Historical audit defensibility is guaranteed.

### Negative / Trade-offs
- Creating new rules requires authoring JSON AST structures rather than free-form text. (Mitigated by validation schemas and admin authoring tools).
