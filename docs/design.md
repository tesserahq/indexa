

# Indexa — Design Document

## 1. Purpose

**Indexa** is a platform service responsible for synchronizing Linden domain data into external search providers using an event-driven architecture.

Indexa:
- Consumes domain events from NATS (CloudEvents)
- Builds provider-agnostic search documents
- Syncs documents to one or more search providers
- Treats search engines as derived read models, never sources of truth

A core design goal is **provider portability**: Algolia is an initial implementation, not an architectural commitment.

---

## 2. Non-Goals

Indexa explicitly does not:
- Own domain data
- Expose end-user search APIs
- Mirror relational schemas
- Perform domain business logic
- Guarantee strict real-time indexing

---

## 3. High-Level Architecture

```
Domain Services
  ├─ write to Postgres
  ├─ emit CloudEvents
  ▼
NATS / JetStream
  ▼
Indexa
  ├─ Event routing
  ├─ Document building
  ├─ Provider adapters
  ▼
Search Providers
  (Algolia, Typesense, ...)
```

Indexa operates fully outside request paths.  
Failure or downtime in Indexa must never impact core APIs.

---

## 4. Core Design Principles

### 4.1 Provider Agnosticism
- No provider-specific logic in core modules
- Providers are isolated adapters
- Switching providers requires configuration, not rewrites

### 4.2 Event-Driven and Replayable
- Live indexing is driven by events
- Consumers are durable and replayable
- Reindexing uses the same pipeline

### 4.3 Idempotency First
- All operations are safe to retry
- Document IDs are deterministic
- Version-aware updates are preferred

### 4.4 Configuration over Code
- Providers and services are registered, not hardcoded
- Secrets are externalized
- Behavior is driven by configuration

---

## 5. Responsibilities

### Indexa
- Consume and route CloudEvents
- Resolve domain ownership
- Build canonical search documents
- Sync documents to search providers
- Perform reindexing operations

### Domain Services
- Own domain data
- Emit semantic domain events
- Expose read-only indexing APIs

### Search Providers
- Store and query denormalized documents
- Remain passive targets

---

## 6. Event Consumption Model

### 6.1 CloudEvents

Events follow the CloudEvents specification and expose an `event_type`.

Examples:
```
com.identies.user.updated
com.custos.role.assigned
com.linden.document.created
```

Events are semantic, small, and stable.

---

## 7. Service Registration and Event Routing

Indexa operates in a microservice-oriented platform where domain ownership is explicit.

Indexa must know which service is authoritative for a given event domain in order to:
- Handle live events
- Perform reindexing

### 7.1 Domain Ownership Model

Each domain service owns one or more event namespaces.

Examples:
- `com.identies.*` → Identies service
- `com.custos.*` → Custos service
- `com.linden.*` → Linden core services

Ownership is declared, never inferred.

---

### 7.2 Service Registration

Each domain service registers with Indexa.

Registration defines:
- Owned domain prefixes
- Base URL for indexing APIs
- Supported entity types
- Authentication requirements

Example:
```
{
  "service": "identies",
  "domains": ["com.identies"],
  "indexing_base_url": "https://identies.internal",
  "entities": ["user", "organization", "membership"],
  "auth": {
    "type": "service_token"
  }
}
```

Registration mechanisms:
- Static configuration
- Admin API or bootstrap job

Registrations are treated as configuration, not mutable runtime state.

---

### 7.3 Event-to-Service Resolution

On event receipt:
1. Extract domain prefix from `event_type`
2. Match against registered domains
3. Resolve owning service
4. Derive entity type and action
5. Dispatch indexing logic

Unregistered domains:
- Are ignored or dead-lettered
- Emit warnings and metrics

---

### 7.4 Reindexing Interaction

The same registry is used during reindexing:
- Indexa resolves target services
- Calls their indexing APIs
- Never hardcodes service assumptions

Indexa routes by declaration, not convention.

---

## 8. Document Model

Indexa builds provider-neutral documents.

Example:
```
{
  "id": "person_123",
  "type": "person",
  "title": "Jane Doe",
  "summary": "Guardian, Barcelona",
  "tags": ["family", "guardian"],
  "metadata": {
    "workspace_id": "ws_456"
  },
  "schema_version": 1,
  "updated_at": "2026-01-14T09:09:00Z"
}
```

This is the canonical indexing contract.

---

## 9. Provider Abstraction Layer

Providers implement a common interface:

```
SearchProvider
- upsert(documents[])
- delete(ids[])
- ensure_index(schema)
- healthcheck()
```

Rules:
- Core never imports provider SDKs
- Providers handle batching, retries, rate limits
- Providers are replaceable at runtime

---

## 10. Configuration and Secrets

### 10.1 Provider Configuration

```
providers:
  algolia:
    enabled: true
    app_id: ${ALGOLIA_APP_ID}
    api_key: ${ALGOLIA_API_KEY}
    index_prefix: linden_
  typesense:
    enabled: false
    host: ${TYPESENSE_HOST}
    api_key: ${TYPESENSE_API_KEY}
```

Rules:
- Secrets are externalized
- Configuration is read at startup
- Providers can be enabled/disabled without code changes

---

## 11. Reindexing Strategy

Reindexing guarantees correctness over time.  
Events provide liveness; reindexing restores trust.

Reindexing always uses the same pipeline as live indexing.

### 11.1 Core Principles

- Reindexing does not consume historical events
- Reindexing reads from authoritative, read-only indexing APIs
- Providers are passive targets
- Operations are restartable and retry-safe

---

### 11.2 Reindexing Scopes

- Full reindex
- Partial reindex:
  - By entity type
  - By workspace / tenant
  - By time range
  - By explicit IDs

---

### 11.3 Reindex Job Definition

```
{
  "scope": "workspace",
  "workspace_id": "ws_456",
  "entity_types": ["person", "document"],
  "providers": ["algolia"],
  "mode": "upsert"
}
```

---

### 11.4 Execution Flow

1. Trigger (admin, schedule, migration)
2. Planning (resolve services, providers, indices)
3. Execution:
   - Fetch entities via service-owned indexing APIs
   - Page deterministically
   - Build documents
   - Upsert in batches
4. Completion (metrics, summaries)

---

### 11.5 Deletion and Staleness

- Upsert-only (default)
- Scoped cleanup
- Full index rebuild with atomic switch

---

### 11.6 Schema Versioning

Each document includes `schema_version`.

- Compatible changes reuse index
- Breaking changes create new indices

---

### 11.7 Concurrency with Live Events

- Live consumers continue running
- Reindexing does not block events
- Idempotent writes guarantee convergence

---

### 11.8 Failure and Recovery

- Batch-level retries
- Job resumability
- No global locks
- Worst case: duplicate upserts

---

### 11.9 Operational Expectations

Reindexing must be:
- Boring
- Observable
- Safe to repeat

If reindexing feels risky, the design is wrong.

---

## 12. Observability

- Provider latency and error metrics
- Event routing metrics
- Reindex progress and outcomes
- Dead-letter monitoring

---

## 13. Future Extensions

This design supports:
- Additional search providers
- Vector and hybrid search
- AI-generated summaries and embeddings
- Search analytics consumers
- Per-tenant index isolation

---

## 14. Summary

Indexa is:
- Event-driven
- Domain-aware
- Provider-agnostic
- Replayable
- Operationally safe

Search providers are implementation details.  
Domain services remain authoritative.