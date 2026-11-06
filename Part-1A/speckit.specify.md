# Feature Specification: Tiered Rate Limiter

## Feature Summary
An API rate limiter using the Token Bucket algorithm with three configurable client tiers.

## Clarifications

### Session 2026-11-07

- Q: What makes a `Retry-After` value "appropriate" (AC3)? → A: It is the smallest whole number
  of seconds after which a retry from the same client will be accepted (time until one token is
  available, rounded up, minimum 1). A client that waits exactly that many seconds MUST be
  accepted; retrying one second earlier MUST still be rejected. (Recommended option, accepted by
  the repository owner on 2026-11-07. Prompted by the 2026-11-06 audit, which found that the
  value was rounded down, so a client obeying the header could be rejected again.)

## Client Tiers
- **Free**: 5 requests per minute.
- **Standard**: 20 requests per minute.
- **Premium**: 100 requests per minute.

## Acceptance Criteria
- [ ] **AC1**: Requests within the limit return successfully.
- [ ] **AC2**: Requests exceeding the limit are rejected with HTTP 429 (Too Many Requests).
- [ ] **AC3**: HTTP 429 responses must include a `Retry-After` header whose value is a positive
  integer number of seconds equal to the smallest wait after which a retry is accepted: retrying
  after exactly that many seconds succeeds, and retrying one second earlier is rejected
  (revised 2026-11-07, see Clarifications).
- [ ] **AC4**: The system must isolate limits correctly based on the provided client ID.
