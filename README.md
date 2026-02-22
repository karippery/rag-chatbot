# SecureRole-RAG: Offline, Role-Based Retrieval-Augmented Generation System

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org)
[![Django](https://img.shields.io/badge/django-5.2-green)](https://www.djangoproject.com)
[![License](https://img.shields.io/badge/license-proprietary-red)](LICENSE)

---

## Overview

SecureRole-RAG is a **high-assurance, offline-first** Retrieval-Augmented Generation system designed for organizations handling confidential internal data. Unlike conventional RAG pipelines that filter results *after* retrieval, this system **enforces access control at the database query level**, ensuring users can only retrieve and reason over documents they are explicitly authorized to access.

✅ Zero third-party API calls — fully offline  
✅ Security classification: `LOW` | `MID` | `HIGH` | `VERY HIGH`  
✅ Role-based access enforced in pgvector queries  
✅ Audit trail for every query  
✅ Async document processing with Celery  

---

## Security Model: Database-Level Access Control

```
┌─────────────────────────────────────────┐
│  USER QUERY: "What is the CEO salary?"  │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│  1. Authenticate via JWT                │
│  2. Resolve user → allowed security levels │
│     e.g., employee → [LOW, MID]         │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│  3. Generate query embedding            │
│  4. pgvector search WITH filter:        │
│     WHERE security_level IN [LOW, MID]  │
│     AND is_active = TRUE                │
│                                         │
│  🔒 HIGH/VERY HIGH chunks NEVER retrieved │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│  5. If no authorized chunks →           │
│     Return: "You don't have access      │
│             to this data"               │
│                                         │
│  6. Else → LLM generates answer from    │
│     authorized context only             │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│  7. Log query to QueryHistory:          │
│     • user_id, timestamp, query hash    │
│     • effective_max_level accessed      │
│     • model used, token count           │
└─────────────────────────────────────────┘
```

### Why This Matters
- ❌ No "filter-after-retrieval" race conditions
- ❌ No accidental leakage via prompt injection or context overflow
- ✅ Compliance-ready: GDPR, HIPAA, internal data policies
- ✅ Defense-in-depth: authz enforced at storage, retrieval, and generation layers

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Dependency Mgmt** | [`uv`](https://github.com/astral-sh/uv) |
| **Backend** | Django 5.2, Django REST Framework |
| **Auth** | JWT (djangorestframework-simplejwt) |
| **Storage** | MinIO (S3-compatible) |
| **Database** | PostgreSQL + [`pgvector`](https://github.com/pgvector/pgvector) |
| **Task Queue** | Celery + Redis |
| **Embedding Model** | `sentence-transformers/all-MiniLM-L6-v2` (ONNX via `optimum[onnxruntime]`) |
| **LLM Options** | • `quick`: `Qwen/Qwen2-0.5B-Instruct`<br>• `detailed`: `Qwen/Qwen2.5-1.5B-Instruct` |
| **Serving** | Uvicorn (ASGI) |
| **Code Quality** | `flake8`, `black`, `isort` |
| **Environment** | Fully offline — no external API calls |

---

##  API Endpoints

###  Document Upload
```http
POST /api/documents/upload/
Authorization: Bearer <JWT>
Content-Type: multipart/form-data

Form Fields:
- file*        : PDF, DOCX, TXT, MD
- title*       : string
- description  : string (optional)
- security_level* : LOW | MID | HIGH | VERY HIGH
```

**Response**:
```json
{
  "id": "doc_abc123",
  "status": "processing",
  "message": "File uploaded. Embedding generation queued."
}
```

>  Background Celery task:  
> `download_from_minio → text_extract → chunk → embed → upsert to pgvector`

---

###  RAG Query
```http
POST /api/rag/query/
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "query": "What is our Q3 marketing budget?",
  "mode": "quick"  // or "detailed"
}
```

**Response (Authorized)**:
```json
{
  "answer": "The Q3 marketing budget is $1.2M, allocated across...",
  "sources": [
    {
      "document_id": "doc_xyz789",
      "title": "Q3 Budget Plan",
      "security_level": "MID",
      "chunk_id": "chunk_456"
    }
  ],
  "model_used": "Qwen/Qwen2-0.5B-Instruct",
  "query_id": "qry_log_001"
}
```

**Response (Unauthorized)**:
```json
{
  "answer": "You don't have access to this data.",
  "sources": [],
  "reason": "no_authorized_chunks_found"
}
```


## 🚀 Quick Start (Docker Compose)

### Prerequisites
- Docker Engine 24.0+
- Docker Compose v2.20+
- 16GB+ RAM recommended (for local LLM inference)
- Optional: NVIDIA GPU + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html ) for accelerated inference

---

### 1. Clone Repository
```bash
git clone https://your-org/secure-role-rag.git
cd secure-role-rag
```

---

### 2. Configure Environment (`.env`)
Copy the example environment file and adjust for your deployment:

```bash
cp .env.example .env

---

### 3. Download Models (One-Time Setup)
Models are not included in the repo. Use the helper script to pull them to a local volume:

```bash
# Create models directory
mkdir -p ./models

# Run model downloader (requires internet once)
docker compose run --rm model-downloader
```

> 📦 Models are cached in `./models` and mounted into containers. Subsequent runs work fully offline.

---

### 4. Start All Services
```bash
# Build and start in detached mode
docker compose up --build -d

# View logs
docker compose logs -f api celery-worker
```

**Services launched**:
| Service | Port | Purpose |
|---------|------|---------|
| `api` | `localhost:8000` | Django + Uvicorn (main API) |
| `celery-worker` | — | Async embedding & processing |
| `celery-beat` | — | Scheduled tasks (optional) |
| `postgres` | `localhost:5432` | PostgreSQL + pgvector |
| `redis` | `localhost:6379` | Celery broker/cache |
| `minio` | `localhost:9000` | S3-compatible object storage |
| `minio-console` | `localhost:9001` | MinIO web UI |

---

### 5.Add DB extention on documents\migrations\0001_initial.py

```python
    operations = [

            migrations.RunSQL(
                sql="CREATE EXTENSION IF NOT EXISTS vector;",
                reverse_sql="DROP EXTENSION IF EXISTS vector;",
            ),
```