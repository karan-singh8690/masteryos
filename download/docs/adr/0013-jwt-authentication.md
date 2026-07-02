# ADR-0013 — JWT Authentication

---

## Title

Use JWT (JSON Web Tokens) with short-lived access tokens and long-lived refresh tokens for authentication, with refresh-token rotation and HttpOnly cookie storage.

---

## Status

Accepted

---

## Date

2026-07-02

---

## Context

The Mastery Engine is a SaaS product with a free tier and a paid tier. Users authenticate to access their learning data, mastery scores, and subscription features. The authentication system must be secure (resistant to credential stuffing, token theft, session hijacking), must be stateless (so any backend instance can serve any request, supporting the horizontal scaling in ASD Section 13.1), and must be user-friendly (no frequent logins, no lost sessions on mobile).

The architecture specification (Task 001, Section 12.1) commits to JWT-based authentication: short-lived access tokens (15 minutes), long-lived refresh tokens (30 days, sliding, in HttpOnly cookies), OAuth (Google, GitHub), and MFA (TOTP) for admin accounts. This ADR formalizes the choice and the security considerations.

The alternatives are session-based authentication (server-side sessions) and passwordless authentication (magic links, passkeys). Both are viable; the choice depends on the project's scale, the team's expertise, and the operational constraints. This ADR explains why JWT is the best fit for the Mastery Engine.

---

## Problem Statement

What authentication mechanism should the Mastery Engine use, given the requirements for stateless backend scaling, security against common attacks (credential stuffing, token theft, session hijacking), user-friendly session persistence, and support for OAuth and MFA?

---

## Decision

We will use **JWT-based authentication** with the following properties:

- **Access tokens** are short-lived (15 minutes), signed with an asymmetric algorithm (RS256 or EdDSA), and contain only the user id, tenant, and role claims. They are never stored in cookies or localStorage; they live in JavaScript memory only. The short lifetime limits the blast radius of token theft.
- **Refresh tokens** are long-lived (30 days, sliding), random opaque strings stored in an HttpOnly, Secure, SameSite=Lax cookie. They are stored as a salted hash in the database, so a database leak does not immediately compromise active sessions. They are rotated on every use; a stolen-and-replayed refresh token is detected (the rotation produces a "token family" anomaly) and revokes the entire session family.
- **OAuth** is supported for Google and GitHub, linked to the User via the UserCredential entity.
- **MFA** is supported via TOTP, required for admin accounts and optional for learner accounts.
- **Recovery** is via emailed magic link, single-use, short expiry (15 minutes), delivered to the verified email only.
- **Session revocation** is supported; the session list is visible to the user, who can revoke any session.

---

## Alternatives Considered

### Alternative A: Server-side sessions (session IDs in cookies, session state in the database or Redis)

- **Description:** The server stores session state; the client stores only a session ID in a cookie.
- **Arguments in favor:**
  - Simpler revocation (delete the session from the store).
  - No token signing/verification overhead.
  - Smaller client payload.
- **Arguments against:**
  - **Stateful backend**: every request requires a session-store lookup, which adds latency and a dependency (Redis or the database) on the critical path.
  - **Horizontal scaling complexity**: the session store must be shared across backend instances, adding infrastructure.
  - **Session-store failure**: if the session store fails, all users are logged out.
  - **Cookie-based session IDs** are vulnerable to CSRF (mitigated by SameSite cookies) and to session fixation (mitigated by session ID rotation).
- **Why rejected:** The stateful requirement conflicts with the stateless backend principle (ASD Section 13.1). The session-store dependency on the critical path adds latency and a failure mode. JWT's statelessness is a significant advantage for horizontal scaling.

### Alternative B: Passwordless authentication (magic links, passkeys)

- **Description:** Users authenticate by clicking a magic link sent to their email, or by using a passkey (WebAuthn).
- **Arguments in favor:**
  - No passwords to steal or reuse.
  - Excellent user experience (no password to remember).
  - Strong security (passkeys are phishing-resistant).
- **Arguments against:**
  - **Email dependency**: magic links require reliable email delivery, which is not guaranteed (spam filters, delivery delays).
  - **Passkey adoption**: passkeys are new; not all users have passkey-capable devices; supporting passkeys requires a fallback (password or magic link), which adds complexity.
  - **Recovery**: passwordless recovery is harder (if a user loses their passkey device and their email, they are locked out).
  - **The project's users (technical interview prep) expect password login**; passwordless is a nice-to-have, not a must-have at launch.
- **Why rejected:** Passwordless is a strong long-term direction (especially passkeys), but it is not the best choice at launch. The project will add passkey support in a future phase (the Identity context supports it via the UserCredential entity), but password + OAuth + MFA is the launch authentication model.

### Alternative C: OAuth-only (no password login)

- **Description:** Users authenticate only via OAuth (Google, GitHub); no password login.
- **Arguments in favor:**
  - No password storage; no password attacks.
  - Delegates security to the OAuth provider.
  - Simpler for the user (no new password).
- **Arguments against:**
  - **Excludes users without Google/GitHub**: some learners (especially in markets where Google/GitHub are less dominant) do not have these accounts.
  - **Provider dependency**: if a provider has an outage, users cannot log in.
  - **Privacy concerns**: some users do not want to link their learning account to their Google/GitHub identity.
  - **The project's users expect password login** as a baseline; OAuth is a convenience, not a requirement.
- **Why rejected:** OAuth-only is too restrictive. The project supports OAuth as a convenience alongside password login, giving users the choice.

### Alternative D: Symmetric JWT signing (HS256) with a shared secret

- **Description:** Use HS256 (HMAC with a shared secret) instead of RS256/EdDSA (asymmetric signing).
- **Arguments in favor:**
  - Simpler (one secret, no key management).
  - Faster signing and verification.
- **Arguments against:**
  - **Shared secret**: any service that verifies the token has the signing key, which means any compromised service can forge tokens. Asymmetric signing (RS256/EdDSA) separates signing (private key) from verification (public key), so verifying services cannot forge tokens.
  - **Key rotation**: with a shared secret, rotation requires coordinating all services; with asymmetric signing, rotation is just publishing a new public key.
- **Why rejected:** The security advantage of asymmetric signing is decisive. The performance difference is negligible at the project's scale.

---

## Pros

- **Stateless backend**: any backend instance can verify a JWT without a session-store lookup, supporting horizontal scaling (ASD Section 13.1).
- **Short-lived access tokens**: the 15-minute lifetime limits the blast radius of token theft.
- **Refresh-token rotation**: stolen-and-replayed refresh tokens are detected and revoke the session family, a strong defense against token theft.
- **HttpOnly cookie storage**: refresh tokens are not accessible to JavaScript, mitigating XSS-based token theft.
- **Asymmetric signing**: verifying services (including the frontend, if needed) cannot forge tokens.
- **OAuth integration**: users can log in with Google or GitHub, reducing password fatigue.
- **MFA support**: TOTP-based MFA for admin accounts and optional for learners.
- **Standards-based**: JWT is an industry standard with broad tooling support.

---

## Cons

- **Token revocation is harder**: unlike server-side sessions, a JWT cannot be "deleted" mid-lifetime. (Mitigated by the short access-token lifetime; for immediate revocation, a revocation list is checked on each request, but this reintroduces some statefulness. The project accepts the 15-minute window for learner accounts and uses the revocation list for admin accounts.)
- **Refresh-token rotation complexity**: the rotation and token-family anomaly detection add complexity to the Identity context.
- **JWT payload size**: JWTs are larger than session IDs, adding bytes to every request. (Negligible at the project's scale.)
- **Cookie-based CSRF risk**: refresh tokens in cookies are vulnerable to CSRF. (Mitigated by SameSite=Lax cookies and by requiring the access token in the request header for sensitive operations.)
- **Standards complexity**: JWT, OAuth, and OIDC have nuances that the team must understand (e.g., algorithm confusion attacks, token leakage in logs).

---

## Consequences

- The Identity context issues access tokens (15-minute JWTs, RS256/EdDSA signed) and refresh tokens (30-day opaque strings, HttpOnly cookies, hashed in the database).
- The frontend stores the access token in JavaScript memory; on 401, it attempts a single refresh using the HttpOnly cookie; on refresh failure, it redirects to login.
- Refresh tokens are rotated on every use; the rotation produces a token family; a replay (use of an old refresh token) revokes the family.
- OAuth (Google, GitHub) is supported; OAuth links to the User via the UserCredential entity.
- MFA (TOTP) is required for admin accounts and optional for learner accounts.
- A revocation list (checked on each request for admin accounts; accepted 15-minute window for learner accounts) supports immediate session revocation.
- The session list is visible to the user, who can revoke any session.
- Authentication events (login, logout, failed login, MFA enable/disable) are logged in the AuditLog.
- JWT signing keys are rotated quarterly; the rotation is a documented operational procedure.
- The glossary (Task 002) defines Authentication, Authorization, Session, UserCredential, and related terms.

---

## Risks

- **Access-token theft**: a stolen access token is valid for up to 15 minutes. *Mitigation:* short lifetime; HTTPS-only transport; no token storage in localStorage or cookies (JavaScript memory only); CSP headers to mitigate XSS.
- **Refresh-token theft**: a stolen refresh token can mint new access tokens. *Mitigation:* HttpOnly cookies (not accessible to JavaScript); rotation on every use; token-family anomaly detection revokes the family on replay; Secure and SameSite attributes.
- **Algorithm confusion attacks**: an attacker tricks the JWT library into accepting a token signed with a different algorithm (e.g., HS256 with the public key as the secret). *Mitigation:* the JWT library is configured to accept only the expected algorithm (RS256 or EdDSA); the library is kept up to date.
- **Token leakage in logs**: JWTs in log entries are a theft vector. *Mitigation:* logging middleware redacts Authorization headers; JWTs are never logged.
- **CSRF on refresh**: a CSRF attack triggers a refresh, minting a new access token. *Mitigation:* SameSite=Lax cookies; the refresh endpoint requires a custom header that cannot be set by a cross-origin form submission.
- **Key compromise**: the JWT signing private key is compromised. *Mitigation:* keys are stored in a secrets manager (ASD Section 12.6); keys are rotated quarterly; key compromise triggers an emergency rotation and a security incident response.
- **MFA bypass**: a bug allows login without MFA for an admin account. *Mitigation:* MFA enforcement is tested; the Identity context's MFA check is defense-in-depth (checked at login and at sensitive-operation time).

---

## Future Review Trigger

**Review trigger:** Any of the following measurable conditions:

1. **Passkey adoption**: passkey support becomes widely available on user devices and users request it, justifying adding passkey authentication alongside password and OAuth.
2. **Token revocation demand**: a security incident reveals that the 15-minute access-token window is too long for learner accounts, justifying a revocation list for all accounts (not just admin).
3. **JWT payload growth**: the JWT payload grows (e.g., with additional claims) to the point where it significantly impacts request size, justifying a switch to opaque tokens with server-side resolution.
4. **OAuth provider consolidation**: the project adds enough OAuth providers (Microsoft, Apple, etc.) that the UserCredential entity and the OAuth flow need refactoring.
5. **Regulatory change**: regulations require stronger authentication (e.g., mandatory MFA for all accounts, or FIDO2 compliance), justifying a policy revision.

**Expected review action:** When any trigger fires, the architecture review group evaluates the authentication change. Adding passkeys or MFA policy changes are relatively low-risk and require a new ADR. Switching from JWT to opaque tokens is a significant change requiring strong justification and a migration plan.

---

## Related ADRs

- **Depends on:** ADR-0003 (FastAPI) — FastAPI's `Depends` and security utilities support JWT authentication.
- **Depends on:** ADR-0002 (PostgreSQL) — refresh tokens and session metadata are stored in PostgreSQL.
- **Informs:** ADR-0014 (API-first development) — the API contract specifies authentication per endpoint.

---

## Related Architecture Sections

- ASD Section 12.1 — Authentication (JWT, refresh tokens, OAuth, MFA, recovery).
- ASD Section 12.2 — Authorization (role-based and resource-based).
- ASD Section 9.3 — Frontend Authentication Flow (token storage, refresh flow, logout).
- ASD Section 12.6 — Secrets Management (JWT signing keys).

---

## Related Glossary Terms

- Authentication
- Authorization
- User
- User Profile
- UserCredential (referenced in glossary)
- Session (referenced in glossary)
- Role
- Permission

---

*End of ADR-0013.*
