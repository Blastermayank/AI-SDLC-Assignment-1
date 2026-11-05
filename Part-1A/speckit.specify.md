# Feature Specification: Tiered Rate Limiter

## Feature Summary
An API rate limiter using the Token Bucket algorithm with three configurable client tiers.

## Client Tiers
- **Free**: 5 requests per minute.
- **Standard**: 20 requests per minute.
- **Premium**: 100 requests per minute.

## Acceptance Criteria
- [ ] **AC1**: Requests within the limit return successfully.
- [ ] **AC2**: Requests exceeding the limit are rejected with HTTP 429 (Too Many Requests).
- [ ] **AC3**: HTTP 429 responses must include an appropriate rate-limit retry header.
- [ ] **AC4**: The system must isolate limits correctly based on the provided client ID.
