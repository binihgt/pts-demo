# PTS Demo - Security Architecture & Threat Defense

This document details the security model, architectural decisions, and threat mitigations implemented across **PTS Demo**.

---

## 1. Threat Matrix & Defense Implementation

| Threat Category | Potential Impact | PTS Demo Mitigation |
|---|---|---|
| **Brute-Force Credential Stuffing** | Unauthorized account takeover | `Flask-Limiter` limits `/auth/login` to **10 requests per minute** per IP. Account lockouts recorded in `AuditLog`. |
| **Credential Theft / Database Breach** | Stolen plain passwords reused on other services | Passwords hashed using `werkzeug.security` with modern PBKDF2/SHA256 and unique per-user random cryptographic salts. |
| **Session Hijacking & XSS Cookie Theft** | Session token theft via malicious scripts | Session cookies configured with **`HttpOnly=True`** (JavaScript cannot access cookies) and **`SameSite=Lax`**. In production, **`Secure=True`** restricts cookies to HTTPS only. |
| **Cross-Site Request Forgery (CSRF)** | Attacker forces CEO browser to create users or delete records | **`Flask-WTF`** enforces cryptographically signed hidden tokens on every HTML form. Requests without matching session tokens return HTTP 400. |
| **SQL Injection (SQLi)** | Arbitrary database read/write/drop | **100% SQLAlchemy ORM** parameterized queries. Raw unescaped SQL string concatenation is strictly prohibited. |
| **Clickjacking** | Dashboard rendered inside hidden iframe on malicious site | HTTP header **`X-Frame-Options: DENY`** prevents framing by any external origin. |
| **Unauthorized Telegram Bot Use** | Random Telegram users querying company finances or faking sales | **Closed-gate authorization**: Unregistered Telegram IDs are rejected immediately. Accounts can only be paired using a one-time 8-character token issued by the CEO. |
| **Privilege Escalation** | Employees viewing other staff's sales or company-wide profit | Explicit role checks (`@ceo_required`, `@manager_or_ceo_required`, `@telegram_auth_required`) and database query scoping (`Sale.employee_id == user.id`). |
| **Accidental Data Loss** | Hard drive failure, employee mistake, or database corruption | Atomic SQLite online backup API (`sqlite3.Connection.backup`) with rolling 14-day automated snapshots. |

---

## 2. Authentication & Credential Storage

### Password Storage
All user passwords are encrypted at rest using:
```python
generate_password_hash(password, method="scrypt" or "pbkdf2:sha256:600000")
```
- Passwords are never saved in plaintext, logs, or memory traces.
- Password hashes include individual, unique cryptographic salts.
- Verification uses constant-time string comparison (`check_password_hash`) to defend against timing attacks.

### Session Hardening
In `app/config.py`:
- `SESSION_COOKIE_HTTPONLY = True`: Blocks Client-side JavaScript (`document.cookie`) from accessing session identifiers.
- `SESSION_COOKIE_SAMESITE = 'Lax'`: Prevents cross-site cookie transmission on third-party links.
- `SESSION_COOKIE_SECURE = True` (Production): Browsers will never transmit cookies over plain HTTP.
- `PERMANENT_SESSION_LIFETIME = 28800`: Enforces an 8-hour maximum session lifetime.

---

## 3. Telegram Account Pairing Model

Unlike public consumer bots, PTS Demo operates as an **authenticated private enterprise bot**:

```text
[ CEO in Dashboard ] ──> Generates 8-character code: 'A1B2C3D4'
                                │
                         (Shared privately)
                                │
                                ▼
[ Employee on Telegram ] ──> Sends: /start A1B2C3D4
                                │
[ Bot Backend ] ─────────> Verifies code in DB -> Associates Telegram ID
                                │
[ Database ] ────────────> Code is CONSUMED and ERASED (One-time use)
```

1. **Pre-registration**: Only users created in the CEO dashboard exist in the database.
2. **One-Time Token**: The 8-character link code is generated via `secrets.token_hex(4).upper()`.
3. **Single Use & Destruction**: Once paired with a Telegram ID, the code is set to `NULL`, preventing replay attacks.
4. **Role Enforcement**: Every incoming Telegram update verifies that the sender's Telegram ID belongs to an active employee before executing commands.

---

## 4. HTTP Security Headers

Every response leaving Flask includes modern security headers configured in `app/__init__.py`:

```http
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; font-src 'self' https://cdn.jsdelivr.net; img-src 'self' data: https:; connect-src 'self';
```

- **Content Security Policy (CSP)**: Restricts script, style, and font loading to local origin and trusted CDNs (jsdelivr for Bootstrap).
- **X-Content-Type-Options**: Prevents browsers from MIME-sniffing away from declared content types.

---

## 5. Audit Trail & Incident Forensics

All security-sensitive and business operations generate an immutable record in `AuditLog`:

```python
AuditLog.log(action, user_id, details)
```

Tracked events include:
- `LOGIN_SUCCESS`, `LOGIN_FAILED`, `LOGIN_BLOCKED`, `LOGOUT`
- `USER_CREATED`, `USER_STATUS_CHANGED`, `PASSWORD_RESET`
- `LINK_CODE_GENERATED`, `TELEGRAM_LINKED`, `TELEGRAM_UNLINKED`
- `SALE_RECORDED`, `PAYMENT_RECORDED`
- `REPORT_DOWNLOADED_TELEGRAM`, `DATABASE_SEEDED`

The CEO can review this audit trail at any time via the web dashboard at `/audit/`.
