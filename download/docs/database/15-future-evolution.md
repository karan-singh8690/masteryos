# 15 — Future Evolution

> How the schema evolves to support ML, vector search, recommendation models, knowledge graph, enterprise customers, multiple subjects, internationalization, offline learning, mobile sync, marketplace.

---

## Evolution Principles

1. **The schema is designed for a decade of evolution** — changes are expected; the schema accommodates them without rewrite.
2. **Versioning preserves history** — triple versioning (ADR-0011) ensures that evolution does not invalidate historical data.
3. **New features are additive** — new tables and columns are added; existing ones are rarely removed (deprecation, not deletion).
4. **Each evolution is a new ADR** — significant schema changes require an ADR documenting the rationale and the migration path.

---

## 1. Machine Learning (per ADR-0007)

The schema supports future ML integration via:

### Feature Extraction Layer

The `attempts` table already records all the features an ML model would need:
- `scoring_outcome`, `partial_credit` (the outcome).
- `time_to_answer_ms` (response time).
- `hint_used`, `hint_tiers_used` (hint behavior).
- `misconception_id` (diagnostic signal).
- `attempt_intent` (practice vs. review vs. diagnostic).
- `content_version_id`, `template_version_id`, `algorithm_version_id` (versioning context).

A future `ml_feature_vectors` table (added when ML is admitted) stores precomputed feature vectors per attempt, indexed by `learner_enrollment_id` and `concept_id` for offline training:

```sql
CREATE TABLE analytics.ml_feature_vectors (
    id uuid PRIMARY KEY,
    attempt_id uuid REFERENCES assessment.attempts(id),
    learner_enrollment_id uuid,
    concept_id uuid,
    feature_vector jsonb NOT NULL,  -- or vector type (see below)
    algorithm_version_id uuid,
    created_at timestamptz DEFAULT now()
);
```

### Model Registry

The `algorithm_versions` table already serves as the model registry. An ML model is an Algorithm Version with `parameters` containing the model's metadata (training data, hyperparameters, model artifact reference). The promotion gate (ADR-0007) governs ML model promotion.

### Shadow Evaluation

A future `ml_shadow_predictions` table records the predictions of a shadow ML model alongside the production deterministic algorithm:

```sql
CREATE TABLE analytics.ml_shadow_predictions (
    id uuid PRIMARY KEY,
    attempt_id uuid REFERENCES assessment.attempts(id),
    production_mastery_score numeric,
    shadow_mastery_score numeric,
    production_review_interval interval,
    shadow_review_interval interval,
    algorithm_version_id_production uuid,
    algorithm_version_id_shadow uuid,
    created_at timestamptz DEFAULT now()
);
```

This table enables offline comparison of the ML model against the production algorithm without affecting learners.

---

## 2. Vector Search (pgvector)

When ML embeddings are added (e.g., concept embeddings for similarity search, learner embeddings for cohort analysis), the `pgvector` extension is installed:

```sql
CREATE EXTENSION IF NOT EXISTS vector SCHEMA infrastructure;
```

### Concept Embeddings

A future `concept_embeddings` table stores vector embeddings per concept:

```sql
CREATE TABLE analytics.concept_embeddings (
    concept_id uuid PRIMARY KEY REFERENCES content.concepts(id),
    embedding vector(768),  -- dimension depends on the model
    model_version text NOT NULL,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX idx_concept_embeddings_vector ON analytics.concept_embeddings USING ivfflat (embedding vector_cosine_ops);
```

This enables queries like "find concepts similar to this one" (for cross-concept recommendation or curriculum gap analysis).

### Learner Embeddings

A future `learner_embeddings` table stores vector embeddings per learner (for cohort analysis):

```sql
CREATE TABLE analytics.learner_embeddings (
    learner_enrollment_id uuid PRIMARY KEY REFERENCES learning.learner_enrollments(id),
    embedding vector(256),
    model_version text NOT NULL,
    created_at timestamptz DEFAULT now()
);
```

This enables queries like "find learners with similar mastery profiles" (for cohort analytics or peer recommendation).

---

## 3. Recommendation Models

Future ML recommendation models (beyond the deterministic Scheduler) require:

### Recommendation Model Registry

The `algorithm_versions` table extends to cover recommendation models (a new `model_type` field, or a parallel `recommendation_model_versions` table).

### Recommendation Feedback

A future `recommendation_feedback` table records learner feedback on recommendations (accepted, deferred, dismissed, with optional reason):

```sql
CREATE TABLE learning.recommendation_feedback (
    id uuid PRIMARY KEY,
    recommendation_id uuid REFERENCES learning.recommendations(id),
    feedback_type text NOT NULL,  -- 'accepted', 'deferred', 'dismissed', 'rated'
    rating integer,  -- 1-5, for 'rated'
    reason text,
    created_at timestamptz DEFAULT now()
);
```

This table is the training data for future ML recommendation models.

---

## 4. Knowledge Graph

The `concepts` and `concept_dependencies` tables already form a knowledge graph. Future evolution adds:

### Graph Analytics

A future `concept_graph_analytics` table (nightly computed) stores graph metrics per concept:

```sql
CREATE TABLE analytics.concept_graph_analytics (
    concept_id uuid PRIMARY KEY REFERENCES content.concepts(id),
    content_version_id uuid REFERENCES content.content_versions(id),
    in_degree integer,
    out_degree integer,
    betweenness_centrality numeric,
    page_rank numeric,
    cluster_id uuid,  -- for community detection
    computed_at timestamptz DEFAULT now()
);
```

This enables queries like "which concepts are bridge concepts (high betweenness)?" or "which concepts form a cluster (community)?" for curriculum analysis.

### Graph Visualization

The knowledge graph is visualized in the Admin Portal and (optionally) to learners. The graph data is derived from `concepts` and `concept_dependencies` at query time (the graph is small enough to build in-memory).

### Cross-Subject Graph

A future `cross_subject_concept_links` table links concepts across subjects (e.g., a Python concept that depends on a SQL concept):

```sql
CREATE TABLE content.cross_subject_concept_links (
    id uuid PRIMARY KEY,
    source_concept_id uuid REFERENCES content.concepts(id),
    target_concept_id uuid REFERENCES content.concepts(id),
    link_type text NOT NULL,  -- 'related', 'reinforces'
    created_at timestamptz DEFAULT now(),
    CHECK (source_concept_id <> target_concept_id)
);
```

This enables cross-subject learning paths (e.g., "backend interview" spanning Python, SQL, System Design).

---

## 5. Enterprise Customers (B2B)

The `organizations` and `organization_members` tables (already modeled) support B2B. Future evolution adds:

### Organization-Specific Content

A future `organization_content_overrides` table allows organizations to customize content (e.g., private concepts, custom learning paths):

```sql
CREATE TABLE content.organization_content_overrides (
    id uuid PRIMARY KEY,
    organization_id uuid REFERENCES administration.organizations(id),
    content_type text NOT NULL,  -- 'concept', 'learning_path', 'template'
    content_id uuid NOT NULL,
    override_type text NOT NULL,  -- 'private', 'custom', 'hidden'
    override_data jsonb,
    created_at timestamptz DEFAULT now()
);
```

### SSO Integration

A future `organization_sso_configs` table stores SSO configuration per organization (SAML, OIDC):

```sql
CREATE TABLE administration.organization_sso_configs (
    id uuid PRIMARY KEY,
    organization_id uuid REFERENCES administration.organizations(id),
    sso_protocol text NOT NULL,  -- 'saml', 'oidc'
    config jsonb NOT NULL,  -- encrypted
    created_at timestamptz DEFAULT now()
);
```

### Organization Analytics

A future `organization_analytics` table (nightly computed) stores aggregate metrics per organization:

```sql
CREATE TABLE analytics.organization_analytics (
    id uuid PRIMARY KEY,
    organization_id uuid REFERENCES administration.organizations(id),
    snapshot_date date NOT NULL,
    active_learner_count integer,
    avg_mastery_score numeric,
    avg_session_duration_seconds integer,
    created_at timestamptz DEFAULT now()
);
```

---

## 6. Multiple Subjects

The schema is already Subject-agnostic (ADR-0010). Adding a new subject (e.g., SQL) requires:

1. Create a `tenants` row and a `subjects` row.
2. Author the content (concepts, objectives, misconceptions, templates) via the Content Pipeline.
3. Configure `scheduling_configs` for the subject.
4. Publish the first `content_versions` for the subject.
5. (Optional) Implement subject-specific pluggable components (e.g., `SQLQueryEvaluator` for SQL).

**No schema changes are required** to add a new subject. The `subject_id` foreign key on all content tables isolates subjects.

### Cross-Subject Features

Future features that span subjects (e.g., a unified dashboard across all of a learner's subjects) query by `user_id` across `learner_enrollments` (which links to different subjects). No schema changes needed.

---

## 7. Internationalization (i18n)

The schema supports i18n via:

### User Locale

The `user_profiles.locale` column (already present) stores the user's BCP-47 locale (e.g., 'en-US', 'hi-IN').

### Content Localization

Content is currently English-only. Future localization requires either:

**Option A: Translated content rows** (separate rows per locale):
```sql
ALTER TABLE content.concepts ADD COLUMN locale text DEFAULT 'en-US';
ALTER TABLE content.concepts ADD COLUMN master_concept_id uuid REFERENCES content.concepts(id);
-- A translated concept has master_concept_id pointing to the English original.
```

**Option B: JSONB translations** (translations in a single row):
```sql
ALTER TABLE content.concepts ADD COLUMN translations jsonb DEFAULT '{}';
-- {"en-US": {"name": "...", "description": "..."}, "hi-IN": {"name": "...", "description": "..."}}
```

Option A is preferred for queryability and versioning (each translation is a separate versioned artifact). Option B is simpler but harder to query and version.

### Notification Localization

Notification templates (currently application-defined constants) are localized via the user's `locale`. No schema changes needed (the application selects the template by locale).

---

## 8. Offline Learning

Offline learning (learners study without internet, sync later) requires:

### Offline Attempt Queue

A future `offline_attempt_queue` table (client-side, not in the database) stores attempts made offline. On sync, the client sends the attempts to the server, which inserts them into `attempts` with `created_at` set to the offline timestamp.

**Conflict resolution**: if the same question was answered offline and online (e.g., the learner started a session online, went offline, continued, then synced), the server reconciles by timestamp. The offline attempt is inserted; the mastery score is recomputed.

### Sync Metadata

A future `sync_metadata` table tracks sync state per device:

```sql
CREATE TABLE learning.sync_metadata (
    id uuid PRIMARY KEY,
    user_id uuid REFERENCES identity.users(id),
    device_id text NOT NULL,
    last_sync_at timestamptz,
    pending_attempt_count integer DEFAULT 0,
    created_at timestamptz DEFAULT now(),
    UNIQUE(user_id, device_id)
);
```

---

## 9. Mobile Sync

Mobile sync (for the PWA or a future native app) requires:

### Device Tracking

The `sessions` table already tracks `device_fingerprint`. A future `devices` table provides richer device management:

```sql
CREATE TABLE identity.devices (
    id uuid PRIMARY KEY,
    user_id uuid REFERENCES identity.users(id),
    device_fingerprint text NOT NULL,
    device_type text,  -- 'ios', 'android', 'web'
    push_token text,  -- for push notifications
    last_seen_at timestamptz,
    created_at timestamptz DEFAULT now(),
    UNIQUE(user_id, device_fingerprint)
);
```

### Push Notification Tokens

The `devices.push_token` column stores the push notification token (APNs for iOS, FCM for Android). The notification system uses this to send push notifications.

### Conflict Resolution

Same as offline learning: the server reconciles by timestamp. The `attempts` table's append-only nature and triple versioning ensure that conflicts are resolvable.

---

## 10. Marketplace (Future Phase 5+)

A marketplace (third-party content authors selling content) requires:

### Author Profiles

A future `author_profiles` table stores marketplace author metadata:

```sql
CREATE TABLE content.author_profiles (
    id uuid PRIMARY KEY,
    user_id uuid REFERENCES identity.users(id),
    display_name text NOT NULL,
    bio text,
    verification_status text DEFAULT 'unverified',
    created_at timestamptz DEFAULT now()
);
```

### Content Listings

A future `content_listings` table lists marketplace content (separate from the platform's own content):

```sql
CREATE TABLE content.content_listings (
    id uuid PRIMARY KEY,
    author_profile_id uuid REFERENCES content.author_profiles(id),
    subject_id uuid REFERENCES content.subjects(id),
    title text NOT NULL,
    description text,
    price_cents integer NOT NULL DEFAULT 0,
    status text DEFAULT 'draft',
    published_at timestamptz,
    created_at timestamptz DEFAULT now()
);
```

### Content Purchases

A future `content_purchases` table tracks which users have purchased which marketplace content:

```sql
CREATE TABLE content.content_purchases (
    id uuid PRIMARY KEY,
    user_id uuid REFERENCES identity.users(id),
    content_listing_id uuid REFERENCES content.content_listings(id),
    price_paid_cents integer NOT NULL,
    purchased_at timestamptz DEFAULT now(),
    UNIQUE(user_id, content_listing_id)
);
```

### Revenue Sharing

A future `revenue_shares` table tracks revenue sharing between the platform and marketplace authors:

```sql
CREATE TABLE billing.revenue_shares (
    id uuid PRIMARY KEY,
    content_purchase_id uuid REFERENCES content.content_purchases(id),
    author_share_cents integer NOT NULL,
    platform_share_cents integer NOT NULL,
    created_at timestamptz DEFAULT now()
);
```

---

## Evolution Summary

| Evolution | Schema Changes Required | New Tables | ADR Required |
|---|---|---|---|
| ML integration (shadow + promotion) | None (attempts already records features) | `ml_feature_vectors`, `ml_shadow_predictions` | Yes |
| Vector search | Install pgvector extension | `concept_embeddings`, `learner_embeddings` | Yes |
| Recommendation models | None (recommendations table exists) | `recommendation_feedback` | Yes |
| Knowledge graph analytics | None (graph exists) | `concept_graph_analytics`, `cross_subject_concept_links` | Yes |
| Enterprise (B2B) | None (organizations exist) | `organization_content_overrides`, `organization_sso_configs`, `organization_analytics` | Yes |
| Multiple subjects | **None** (schema is subject-agnostic) | None | No |
| Internationalization | Add `locale` / `master_concept_id` or `translations` | None (alter existing) | Yes |
| Offline learning | None (attempts append-only) | `sync_metadata` (client-side offline queue) | Yes |
| Mobile sync | None (sessions track devices) | `devices` | Yes |
| Marketplace | None (content structure reusable) | `author_profiles`, `content_listings`, `content_purchases`, `revenue_shares` | Yes |

---

## Closing Note

The schema is designed to evolve. Every evolution described here is additive (new tables, new columns); none requires a rewrite. The triple-versioning foundation (ADR-0011) ensures that evolution does not invalidate the historical data that is the company's competitive moat.

The role of this document is to anticipate the evolutions the team expects, so that when the time comes, the schema is ready. Each evolution will be a new ADR, a new migration, and a new chapter in the database's history.

---

*End of Future Evolution.*
