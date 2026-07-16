# Security Documentation

## Standards

- OWASP Top 10
- OWASP API Security Top 10
- CWE / CVE hygiene
- Zero Trust / Least Privilege / Defense in Depth

## Controls implemented

### Authentication & sessions
- Argon2id password hashing
- Short-lived JWT access tokens (15m default)
- Refresh token rotation with family reuse detection
- Account lockout after failed logins
- Secure logout (token revoke)
- Password reset single-use tokens (hashed at rest)
- MFA-ready user fields

### Authorization
- RBAC permission matrix (`app/core/permissions.py`)
- Object-level checks (customers only see own claims/vehicles)
- Function-level permission dependencies on admin routes
- Mass-assignment protection via Pydantic schemas

### Injection & XSS
- SQLAlchemy ORM only (no raw string SQL for user input)
- JSON error responses without stack traces in production handlers
- CSP, X-Content-Type-Options, X-Frame-Options
- React auto-escaping for UI

### File upload
- Extension allow-list
- Magic-byte sniffing
- Size / resolution limits
- Path traversal rejection
- Thumbnail generation from verified images
- Virus scan status hook

### Transport & storage
- HTTPS-ready NGINX config surface
- Secrets via environment variables
- AES-256-GCM helpers for field/file encryption at rest
- Secure cookies guidance for SPA deployments

### Abuse resistance
- Login and API rate limiting (app + NGINX zones)
- Request IDs for correlation
- Audit trail for security-relevant events

## Vulnerability checklist (pre-release)

Stored/Reflected/DOM XSS · SQLi · CSRF · IDOR · Broken authZ · SSRF · RCE · Path traversal · Upload abuse · Open redirect · Clickjacking · Sensitive data exposure · Security headers · Cookie flags · JWT validation · Rate limiting · BOLA/BFLA · Business logic · Race conditions · Privilege escalation · Secret leakage · Weak crypto · Dependency CVEs · Container hardening
