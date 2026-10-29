# Aura AI — Secure, Intelligent, Multimodal AI Platform

Aura AI is an enterprise-grade full-stack multimodal AI platform featuring grounded generative chat, multi-document Retrieval-Augmented Generation (RAG) with hybrid lexical & semantic search, document workspace with versioning and diff comparisons, speech-to-text / text-to-speech, AI image synthesis, live web research, long-term conversational memory, and multi-region crisis safety guardrails.

---

## 🌟 Key Architecture & Capabilities

* **Dual Mode Authentication (JWT & Guest Mode):**
  * Salting & password hashing via `bcrypt` (cost factor 12).
  * Stateless signed JWT sessions (`HS256`) with automatic guest chat history claiming upon registration.
  * Account self-service: password resets, profile management, custom AI instructions, and irreversible account deletion.
* **Hybrid Retrieval-Augmented Generation (RAG):**
  * Combines dense semantic vector search (Google Gemini `gemini-embedding-001` with 3072 dimensions / `pgvector` cosine distance) and sparse lexical BM25 token matching.
  * Duplicate document detection (SHA & size checks) and automatic retrieval result caching.
* **Smart Long-Term Conversational Memory:**
  * Auto-extracts personal facts, roles, and preferences across conversation turns.
  * Transparent user memory inspector: view, add, or permanently forget memory facts.
* **Agent Tool Orchestration:**
  * Intent classifier automatically coordinates Web Search, Document RAG, Document Generation, and Image Generation.
  * Sandboxed execution with strict timeouts and bounded retries.
* **Empathetic AI & Multi-Region Crisis Safety Guardrails:**
  * Context-aware crisis ideation detection with false-positive filtering for technical terms (e.g. `kill -9 process`, `cut video`).
  * Instant helpline routing for **India** (KIRAN 1800-599-0019, Vandrevala, AASRA), **United States & Canada** (988), **United Kingdom** (NHS 111, Samaritans 116 123), and International resources.
* **Document Workspace:**
  * Collaborative document drafting with live version history, unified diff comparison, one-click version restoration, and export to `.docx`, `.md`, and `.txt`.
* **Production Observability:**
  * Request correlation ID (`X-Correlation-ID`) propagation.
  * Token estimation and provider cost monitoring.
  * Kubernetes/Docker `/api/health/live` and `/api/health/ready` probes.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
* **Python:** 3.13+
* **Node.js:** 20+ (with npm)
* **PostgreSQL:** 16 with `pgvector` (optional; falls back automatically to SQLite `dev_fallback.db` if PostgreSQL is not active)
* **Google Gemini API Key:** (or OpenAI API Key)

### 2. Local Development Setup

#### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate Python virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and supply GEMINI_API_KEY (or OPENAI_API_KEY)

# Start backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install npm packages
npm install

# Start Vite development server
npm run dev
```

Visit the application at [http://localhost:5173](http://localhost:5173).  
Swagger API interactive documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## 🐳 Docker Deployment

The application is fully containerized using Docker Compose:

```bash
# Configure root environment
cp .env.example .env

# Build and start all services (PostgreSQL 16 pgvector, FastAPI backend, Nginx frontend)
docker-compose up -d --build

# View container logs
docker-compose logs -f
```

---

## 🧪 Automated Testing

Run the comprehensive 29-test automated test suite:

```bash
cd backend
.\venv\Scripts\python.exe -m pytest tests -v
```

All 29 tests validate:
* Authentication, password reset, cross-user isolation, account deletion.
* Hybrid RAG, BM25 scoring, duplicate document prevention.
* Smart memory CRUD and prompt injection defenses.
* Agent intent routing and tool timeouts.
* Observability health probes (`/health/live`, `/health/ready`, `/health/metrics`).
* Multi-region crisis safety guardrails and false-positive filtering.
* Document workspace version restoration and diff comparisons.

---

## 🛡️ Security & Privacy
See [`docs/SECURITY.md`](docs/SECURITY.md) for full threat modeling, rate limiting thresholds, and security headers specifications.

