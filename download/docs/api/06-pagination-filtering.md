# 06 — Pagination & Filtering

> Cursor pagination, sorting, filtering, searching, field selection, expansion.

---

## 1. Cursor Pagination

All collection endpoints use **cursor-based pagination** (not offset). Cursors are opaque strings encoding the position; the client passes them back to get the next page.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page_size` | integer | 20 | Items per page (max 100). |
| `cursor` | string | null | Cursor from the previous response. |

### Response Envelope

```json
{
  "data": [...],
  "pagination": {
    "cursor": "current-cursor",
    "next_cursor": "next-cursor-or-null",
    "has_more": true,
    "total_count": 1234
  }
}
```

### Why Cursor, Not Offset

- **Performance**: offset pagination scans and discards rows (`OFFSET 10000 LIMIT 20`); cursor pagination uses an index seek (`WHERE created_at > cursor_value`).
- **Stability**: new inserts don't shift pages (offset pagination can skip or duplicate items).
- **No count requirement**: cursor pagination doesn't need `COUNT(*)` (expensive on large tables).

### Cursor Format

Cursors are base64-encoded strings containing the sort key and the row ID. Example decoded: `created_at:2026-07-02T14:30:00Z:id:550e8400-...`. Clients treat them as opaque.

---

## 2. Sorting

### Parameter

`sort_by=<field>` (ascending by default; `-` prefix for descending).

### Examples

```
GET /attempts?sort_by=-created_at
GET /concepts?sort_by=difficulty,name
```

### Multi-field Sort

Comma-separated: `sort_by=-created_at,id` (sort by created_at descending, then id ascending for ties).

### Default Sort

Each endpoint has a default sort (e.g., attempts default to `-created_at`; concepts default to `name`).

---

## 3. Filtering

### Equality Filters

```
GET /attempts?scoring_outcome=correct
GET /concepts?difficulty=hard
GET /enrollments?status=active
```

### Range Filters

```
GET /attempts?created_after=2026-07-01T00:00:00Z&created_before=2026-08-01T00:00:00Z
GET /mastery-scores?min_mastery=0.7
```

### Boolean Filters

```
GET /mastery-scores?weak_only=true
GET /concepts?include_archived=false
```

### IN Filters

Comma-separated values:

```
GET /attempts?scoring_outcome=correct,partial
GET /achievements?category=milestone,graduation
```

### Filter Combinations

Filters are ANDed by default. OR requires a different syntax (not supported in v1; use multiple requests or a future GraphQL endpoint).

---

## 4. Searching

### Full-Text Search

```
GET /search?q=list+mutability&type=concepts&subject_id=...
```

The `q` parameter triggers full-text search (PostgreSQL `tsvector` for v1; Elasticsearch for v2+ per ADR future suggestions).

### Search vs Filter

- **Filter** narrows a collection by exact or range match.
- **Search** matches text across multiple fields with relevance ranking.

Search results include a `score` field (relevance); filter results do not.

---

## 5. Field Selection

Clients can request specific fields to reduce payload size:

```
GET /concepts/{id}?fields=id,name,slug
```

Response:
```json
{ "id": "...", "name": "...", "slug": "..." }
```

### Rules

- `id` is always included (cannot be omitted).
- Unknown fields are ignored (not an error).
- Nested fields use dot notation: `fields=id,name,objectives.statement`.

---

## 6. Expansion

Related resources can be expanded inline to avoid extra requests:

```
GET /concepts/{id}?expand=objectives,misconceptions,dependencies
```

Response:
```json
{
  "id": "...",
  "name": "...",
  "objectives": [{ "id": "...", "statement": "..." }],
  "misconceptions": [{ "id": "...", "name": "..." }],
  "dependencies": [{ "target_concept_id": "...", "dependency_type": "prerequisite" }]
}
```

### Rules

- Without `expand`, related resources are not included (only IDs where applicable).
- Expansion is one level deep by default; deeper expansion uses dot notation: `expand=objectives.misconceptions`.
- Expansion is per-request; the server may limit the expansion depth (max 3 levels).

---

## 7. Combining Pagination, Filtering, Sorting

All collection endpoints support combining these:

```
GET /attempts?enrollment_id=...&scoring_outcome=incorrect&created_after=2026-07-01T00:00:00Z&sort_by=-created_at&page_size=50&cursor=...
```

---

*End of Pagination & Filtering.*
