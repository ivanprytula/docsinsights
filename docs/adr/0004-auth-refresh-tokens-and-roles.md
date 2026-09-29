# ADR-0004: Refresh Tokens (Stateless JWT) and Role Field (Schema-Only)

**Date:** 2026-09-29
**Status:** Accepted
**Scope:** Phase 1 (Auth & User Identity completion)

## Context

Phase 1 was marked "shipped" in `docs/roadmap.md`, but the actual implementation missed two auth primitives that the roadmap claims to have delivered:

1. **Refresh tokens** — The roadmap explicitly lists `POST /auth/refresh` as shipped, but no refresh-token mechanism exists.
2. **Role field on User** — The roadmap frames a `role` field as "foundation for Phase 2 authz," but only a binary `is_superuser` bool exists today.

Without these, Phase 2 (authorization) has no foundation to build on. This ADR documents the decision to add both primitives to complete Phase 1.

## Decision

### Refresh Tokens: Stateless JWT

Issue a second, longer-lived JWT alongside the access token at login. The refresh token:
- Has a distinct `type: "refresh"` claim (access tokens carry `type: "access"`), preventing replay as an access token.
- Uses a longer default expiry (30 days vs. 8 days for access tokens).
- Is verified by decode only — **no server-side storage or revocation**.

**Endpoint:** `POST /login/refresh-token`
**Request:** `{"refresh_token": "<jwt>"}`
**Response:** `{"access_token": "<new_jwt>", "refresh_token": "<new_jwt>", "token_type": "bearer"}`
**Behavior:** Decode the refresh token, check its `type` claim, verify the user exists and is active, and issue new tokens.

### Role Field: Schema-Only

Add a `role` column to the `User` table with an enum type (`"user"` | `"admin"`), defaulting to `"user"`.

- **No enforcement in Phase 1.** The field exists so Phase 2 can build role-based authorization on top of it.
- **`is_superuser` remains unchanged.** It continues to gate admin routes (`POST /users`, `DELETE /users/{id}`, etc.). This keeps Phase 1 focused on identity, not authorization.
- **Migration:** Single `ALTER TABLE` adds the column with a PostgreSQL enum type.

## Rationale

### Stateless Refresh JWT over DB-Backed

| Aspect | Stateless JWT | DB-backed token |
| --- | --- | --- |
| **Revocation** | Not possible (no server state) | Possible (lookup DB on use) |
| **Logout** | Not possible (token always valid until expiry) | Possible (mark token revoked) |
| **Scaling** | No DB reads for refresh (stateless verification) | Each refresh hits DB |
| **Complexity** | Lower (no token table, no cleanup) | Higher (migration, CRUD, expiry handling) |

**Stateless JWT chosen because:**
1. The project currently has no logout flow or revocation requirement.
2. Stateless verification scales linearly with request volume (no DB bottleneck).
3. Simpler to ship in Phase 1 without adding a new table.
4. Can be upgraded to DB-backed in Phase 3+ if logout/revocation becomes a real feature.

### Schema-Only Role Field

Deferring enforcement to Phase 2 keeps Phase 1 tightly scoped to **identity and session management**, not authorization. The field provides the schema contract Phase 2 needs without adding authorization logic (permission checks, middleware, policy evaluation) to Phase 1.

## Implementation

- **Backend:** `backend/app/models.py` — Add `UserRole` enum and `role: UserRole` field to `UserBase`.
- **Security:** `backend/app/core/security.py` — Add `create_refresh_token()` function.
- **Config:** `backend/app/core/config.py` — Add `REFRESH_TOKEN_EXPIRE_MINUTES` (default 30 days).
- **Routes:** `backend/app/api/routes/login.py` — Update login endpoint to issue refresh token, add refresh endpoint.
- **Token model:** `backend/app/models.py` — Extend `Token` response model to include `refresh_token` field.
- **Migration:** `backend/app/alembic/versions/` — Add role column via `ALTER TABLE user ADD COLUMN role ...`.
- **Tests:** `backend/tests/api/routes/test_login.py` — Verify refresh token is issued, accepted, and rejects wrong token type/invalid token/inactive user.

## When I Would Change This

- **If logout becomes a requirement** — A logout endpoint needs server-side revocation. At that point, migrate to DB-backed refresh tokens (store hash + expiry + revocation flag, check on use).
- **If token rotation is needed for security** — Stateless tokens cannot be rotated server-side. Add a token refresh counter or migration token.
- **If role-based enforcement is added in Phase 2** — The role field is already in the schema; Phase 2 adds the middleware/checks that respect it.

## Alternatives Considered

### 1. Include logout / revocation in Phase 1
- **Rejected:** Logout is not part of the current feature set. Shipping it "just in case" violates YAGNI; storage + cleanup are real costs.

### 2. Immediate role-based authorization in Phase 1
- **Rejected:** Phase 1 is identity (who are you), not authorization (what can you do). Adding permission checks, role enum matchers, and protected routes would bloat Phase 1 and conflate concerns.

### 3. No role field yet
- **Rejected:** The roadmap frames roles as Phase 1's deliverable ("foundation for Phase 2 authz"). Omitting it leaves Phase 2 with no schema to build on. A simple schema-only field costs almost nothing and unblocks Phase 2.

## Sign-Off

- **Author:** Claude (Sonnet 5)
- **Reviewed by:** (pending)
- **Date accepted:** 2026-09-29
