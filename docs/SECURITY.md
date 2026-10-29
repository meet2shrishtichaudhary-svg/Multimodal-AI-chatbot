# Aura AI — Security, Privacy & Compliance Architecture

**Document Version:** 2.0  
**Classification:** Engineering Specification & Threat Model  
**Updated:** October 2026  

---

## 1. Security Overview

Aura AI implements defense-in-depth principles across its full-stack architecture. The platform treats all incoming client payloads, uploaded documents, web search responses, and third-party AI provider outputs as potentially untrusted.

---

## 2. Authentication & Session Security

* **Password Hashing:** Passwords are never stored in plaintext. They are salted and hashed using `bcrypt` (work factor 12) with pre-hash Unicode normalization.
* **Session Management:** Stateless JSON Web Tokens (JWT) signed via HMAC-SHA256 (`HS256`) with a configurable secret (`JWT_SECRET`).
* **Session Expiration:** Default 7-day expiration (`ACCESS_TOKEN_EXPIRE_MINUTES`).
* **Password Reset Flow:** Cryptographically random 256-bit URL-safe tokens (`secrets.token_urlsafe(32)`) with a strict 2-hour expiration window.
* **Dual Auth & Guest Isolation:** Authenticated user sessions are strictly isolated by `user_id`. Unauthenticated users use ephemeral `X-Session-ID` headers with automated migration available upon account creation.
* **Account Deletion:** Full user data purge (`DELETE /api/auth/me`), recursively deleting database records, conversation histories, knowledge base chunks, document workspaces, and physical uploaded files.

---

## 3. Network & Transport Security

* **HTTPS Enforcement:** Production deployment is served over TLS 1.3 via reverse proxy (Nginx).
* **CORS Restrictions:** Cross-Origin Resource Sharing is configured via `CORS_ORIGINS` in `.env` to restrict cross-origin API calls to approved domain origins.
* **Security Headers Middleware:** Every response automatically injects:
  * `X-Content-Type-Options: nosniff` — Prevents browser MIME-type sniffing.
  * `X-Frame-Options: DENY` — Hardens against clickjacking attacks.
  * `X-XSS-Protection: 1; mode=block` — Activates browser cross-site scripting filters.
  * `Referrer-Policy: strict-origin-when-cross-origin` — Protects referer leakage.
  * `Permissions-Policy: microphone=(self), camera=()` — Restricts unauthorized device sensors.

---

## 4. API Rate Limiting & Denial of Service (DoS) Defense

An in-memory token-bucket rate limiter protects sensitive endpoints:
* **Authentication Routes (`/auth/login`, `/auth/register`, `/auth/forgot-password`):** Rate-limited to 15 requests per 60 seconds per IP address to eliminate brute-force and credential stuffing.
* **General API Routes (`/chat`, `/documents`, `/uploads`):** Rate-limited to 120 requests per 60 seconds per IP address.
* Exceeded requests return `429 Too Many Requests` with dynamic `Retry-After` headers.

---

## 5. File Upload & Document Parsing Security

* **Allowed Extensions:** Strictly whitelisted: `.txt`, `.md`, `.pdf`, `.docx`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.mp3`, `.wav`, `.m4a`, `.webm`, `.ogg`.
* **Path Traversal Protection:** All filenames are sanitized via `sanitize_filename()` (stripping null bytes `\0`, directory traversal markers `../`, `..\`, and non-alphanumeric characters). Physical disk operations use `safe_join_upload_path()` to ensure files never escape `settings.UPLOAD_DIR`.
* **Upload Size Limits:** Hard ceiling of 25MB (`MAX_UPLOAD_SIZE_MB`).

---

## 6. Prompt Injection & AI Safety Defense

* **RAG Context Guardrails:** Retrieved chunks from uploaded documents are wrapped in distinct boundary tags:
  ```text
  --- BEGIN RETRIEVED DOCUMENT CONTEXT ---
  [Doc 1: Project Plan]
  ...
  --- END RETRIEVED DOCUMENT CONTEXT ---
  ```
  The system prompt instructs the LLM that retrieved content represents external reference material and must never override core safety directives.
* **Crisis Safety Interventions:** Layered pattern detection scans prompts for self-harm and crisis ideation, injecting empathetic safety instructions and verified helpline resources.

---

## 7. Observability & Sensitive Data Redaction

* **Correlation IDs:** Every incoming request receives or generates an `X-Correlation-ID` header, propagated through logs and responses for end-to-end trace correlation.
* **Log Redaction:** All sensitive credentials (`AIzaSy...`, `sk-...`, `Bearer ey...`, passwords) are scrubbed via `redact_sensitive_text()` before emission to logs.

---

## 8. Remaining Assumptions & Operational Checklist

1. In production, change the default `JWT_SECRET` in `.env` to a high-entropy 64-character secret.
2. In multi-instance load-balanced production deployments, back the in-memory rate limiter with Redis.
3. Ensure PostgreSQL database user operates with least privilege (only `SELECT`, `INSERT`, `UPDATE`, `DELETE` permissions on `mm_chatbot` schema).

