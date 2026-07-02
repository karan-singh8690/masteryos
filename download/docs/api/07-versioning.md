# 07 — API Versioning

> URI versioning, deprecation, sunset, backward compatibility, breaking changes.

---

## 1. Versioning Strategy

The API is **URI-versioned**: `/api/v1/...`, `/api/v2/...`.

### Why URI Versioning (not header)

- **Simplicity**: the version is visible in the URL; easy to test, debug, and route.
- **Caching**: CDNs and proxies can cache per-version (header-based versioning breaks caching).
- **Discoverability**: the version is self-documenting in the URL.
- **Industry standard**: most public APIs (GitHub, Stripe, Twilio) use URI versioning.

### Version Number

- **Major version** (`v1`, `v2`): bumped on breaking changes.
- **No minor version in URI**: minor (additive) changes don't bump the URI; they're backward-compatible.
- **Patch version**: never in URI; bug fixes are always backward-compatible.

---

## 2. Backward Compatibility

### What's Backward-Compatible (no version bump)

- Adding a new endpoint.
- Adding an optional request field.
- Adding a new response field (clients ignore unknown fields).
- Adding an enum value (clients handle unknown values gracefully).
- Relaxing a constraint (making a required field optional).
- Changing the order of fields in a response (JSON objects are unordered).

### What's a Breaking Change (requires version bump)

- Removing an endpoint.
- Removing or renaming a request or response field.
- Changing a field's type.
- Changing a field's semantic meaning.
- Adding a required request field.
- Restricting a constraint (making an optional field required).
- Removing an enum value.
- Changing the default behavior of an endpoint.
- Changing authentication requirements.
- Changing error codes or status codes.

---

## 3. Deprecation

When an endpoint or field is deprecated (but still functional):

1. **Announce**: the deprecation is announced in the changelog and via the `Deprecation` header on the deprecated endpoint.
2. **Sunset header**: the `Sunset` header indicates the removal date.
3. **Documentation**: the deprecated endpoint is marked in the OpenAPI spec.
4. **Migration guide**: a guide helps clients migrate to the replacement.

### Example Deprecation Response

```
HTTP/1.1 200 OK
Deprecation: true
Sunset: Sat, 31 Dec 2026 23:59:59 GMT
Link: <https://docs.masteryengine.com/api/migration/v1-to-v2>; rel="deprecation"
```

---

## 4. Sunset Policy

- **Minimum support**: a deprecated endpoint is supported for at least 6 months after its successor ships.
- **Sunset date**: communicated via the `Sunset` header at least 6 months in advance.
- **Notification**: clients are notified via email (for registered apps) and the changelog.
- **Removal**: after sunset, the endpoint returns `410 Gone` with a migration link.

---

## 5. Version Coexistence

During a major version migration (e.g., v1 → v2):

- Both versions run in parallel.
- v1 is deprecated but functional (with `Deprecation` and `Sunset` headers).
- v2 is the default for new clients.
- v1 is removed after the sunset date.

---

## 6. Versioning of Schemas (Events)

Event payloads are versioned via `payload_schema_version` (per `08-event-versioning.md` in Task 005). Event versioning is independent of API versioning.

---

## 7. Changelog

The API changelog is maintained in the repository and published at `https://docs.masteryengine.com/api/changelog`. It documents:

- New endpoints and fields (additive; no version bump).
- Deprecations (with sunset dates).
- Breaking changes (with new version).
- Bug fixes.

---

*End of Versioning.*
