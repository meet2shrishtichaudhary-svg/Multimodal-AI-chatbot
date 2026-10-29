# Aura AI — Production Implementation Roadmap

**Tracking Document:** Epics 1 through 15  
**Version:** 2.0 Production Upgrade  
**Status:** In Active Execution  

---

## Roadmap Matrix

| Epic / Phase | Priority | Scope & Key Deliverables | Status | Tests & Verification |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0: Audit & Baseline** | P0 | Codebase audit, baseline tests, dependency map | ✅ Completed | 18 passing tests recorded in `docs/IMPLEMENTATION_AUDIT.md` |
| **Epic 1: Auth & User Management** | P0 | JWT sessions, password reset, user-wise chat isolation, account deletion (`DELETE /api/auth/me`) | ⏳ In Progress (Account deletion & tests remaining) | Automated isolation tests, registration/login test |
| **Epic 2: Security & Privacy** | P0 | Rate limiting, HTTP security headers, request size limits, correlation ID middleware, safe path validator, log sanitization, `docs/SECURITY.md` | 🔲 Queued | Rate limit 429 tests, security header verification, path traversal checks |
| **Epic 3: Advanced Hybrid RAG** | P0 | Hybrid retrieval (BM25 lexical + vector cosine), threshold filtering, source citations, duplicate document detection, vector index sync | 🔲 Queued | Hybrid search test, citation verification test, duplicate doc rejection test |
| **Epic 4: Smart Memory Management** | P1 | User memory model (`user_memories`), semantic fact extraction, relevant memory retrieval into chat context, memory CRUD endpoints, privacy toggle | 🔲 Queued | Memory CRUD tests, memory isolation test, memory context injection test |
| **Epic 5: AI Agent & Tool Orchestration** | P1 | Modular agent orchestrator: intent classifier, multi-tool coordination (Web, RAG, DocGen, ImageGen), progress streaming, bounded retries | 🔲 Queued | Tool execution tests, intent classification tests, timeout handling test |
| **Epic 6: Observability & Cost Monitoring** | P1 | `X-Correlation-ID`, request latency metrics, token/cost estimation logging, `/api/health/live`, `/api/health/ready`, `/api/health/metrics` | 🔲 Queued | Liveness/readiness endpoint tests, correlation ID propagation test |
| **Epic 7: Document Workspace Upgrades** | P1 | Version diff comparison, version restore (`POST .../restore/{ver}`), workspace search, save state indicators | 🔲 Queued | Version restore test, diff generator test |
| **Epic 8: Natural Voice & Multilingual** | P1 | Multi-language audio support (English, Hindi, Hinglish), audio recording controls, TTS cancel | 🔲 Queued | Audio language parameter tests |
| **Epic 9: Feedback & AI Evaluation** | P1 | User feedback API (`/api/feedback`), hallucination evaluation harness, citation validation test | 🔲 Queued | Feedback submission test, evaluation runner test |
| **Epic 10: Background Jobs & Scalability** | P2 | In-memory / persistent job queue for bulk embedding and heavy document export (`/api/jobs`) | 🔲 Queued | Job lifecycle test (queued -> processing -> completed) |
| **Epic 11: Database, Storage & Recovery** | P0 | User data cascade deletion, database backup/restore utility, schema validation | 🔲 Queued | Backup and restore script test |
| **Epic 12: Testing & CI/CD** | P0 | Expand pytest suite to 30+ tests, GitHub Actions CI workflow (`.github/workflows/ci.yml`) | 🔲 Queued | Complete pytest run (all passing) |
| **Epic 13: Deployment & Operations** | P0 | `Dockerfile`, `docker-compose.yml`, `.env.example`, `README.md` | 🔲 Queued | Container configuration check, frontend build check |
| **Epic 14: Advanced User Experience** | P1 | Frontend search bar, memory management UI, feedback thumbs up/down, language picker | 🔲 Queued | UI build & module bundle verification |
| **Epic 15: Crisis Safety & Guardrails** | P0 | Multi-region helplines (India, US, UK, Canada, International), layered context scoring to prevent false positives | 🔲 Queued | Crisis safety regression tests (positive and negative cases) |
| **Final Acceptance & Report** | P0 | Produce `docs/IMPLEMENTATION_FINAL_REPORT.md` | 🔲 Queued | Acceptance criteria verification |

---

## Execution Principles
1. **Never mock real integrations**: Keep working Gemini, Whisper, pgvector, DuckDuckGo code intact.
2. **Backward Compatibility**: Preserve guest mode and existing API contracts.
3. **Verified Deliverables**: Every code change accompanied by tests and verification before marking complete.

