# Role-Based Secure RAG System

**A self-hosted Retrieval-Augmented Generation system with access control**


---

## Overview

This is an **enterprise-grade RAG (Retrieval-Augmented Generation) system** that allows organizations to:

- 📚 Upload internal documents (PDFs, Word, text files)
- 🔐 Classify them by security level (LOW, MID, HIGH, VERY HIGH)
- 🔍 Let employees query the knowledge base using natural language
- ✅ **Guarantee** users only see answers from documents they're authorized to access

### Key Differentiator: Security-First Design

Unlike typical RAG systems that filter results *after* retrieval, this system **enforces access control at the database level**. Unauthorized content is never retrieved — not even to be discarded. This eliminates entire classes of security vulnerabilities.

---

## Features

### 🔒 **Three-Layer Security Architecture**

```
┌──────────────────┬────────────────────────────┬──────────────────────┐
│  Authentication  │     Authorization          │   Data Protection    │
├──────────────────┼────────────────────────────┼──────────────────────┤
│ JWT tokens       │ Role → Clearance mapping   │ Pre-filtered search  │
│ 15-min expiry    │ Document-level permissions │ Encrypted storage    │
│ Token rotation   │ Endpoint-level RBAC        │ Audit logging        │
│ Rate limiting    │ Query-level filtering      │ No external APIs     │
└──────────────────┴────────────────────────────┴──────────────────────┘
```

### 📊 **Role-Based Access Control**

| Role            | Clearance Levels      | Use Case                    |
|-----------------|-----------------------|-----------------------------|
| Guest           | LOW                   | External contractors        |
| Employee        | LOW, MID              | General staff               |
| Manager         | LOW, MID, HIGH        | Department heads            |
| CEO             | ALL                   | Executive leadership        |
| Vice President  | ALL                   | C-suite                     |

### 🚀 **Technical Capabilities**

- **Document Processing**: Automatic chunking, embedding, and indexing
- **Vector Search**: PostgreSQL + pgvector for lightning-fast similarity search
- **Local LLM**: Optional TinyLlama for on-premise answer generation
- **Audit Trail**: Immutable logs of all queries and access attempts
- **Zero External Dependencies**: All AI runs locally — no OpenAI/Anthropic API calls
- **Resource Efficient**: Runs on 4GB RAM, i3 CPU



## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│  (Web UI, Mobile App, API Consumers)                            │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS + JWT
┌────────────────────────────▼────────────────────────────────────┐
│                     Django REST API                              │
│  ┌──────────────┬───────────────────┬─────────────────────┐    │
│  │   Auth       │   Documents       │   RAG Engine        │    │
│  │   (users/)   │   (documents/)    │   (rag/)            │    │
│  └──────────────┴───────────────────┴─────────────────────┘    │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
┌────────▼────────┐  ┌───────▼───────┐  ┌───────▼──────────┐
│  PostgreSQL     │  │    MinIO      │  │  Embedding Model │
│  + pgvector     │  │  (S3 storage) │  │  (all-MiniLM)    │
│                 │  │               │  │                  │
│ • User data     │  │ • Raw files   │  │ • 80MB           │
│ • Documents     │  │ • Encrypted   │  │ • CPU-friendly   │
│ • Embeddings    │  │ • Versioned   │  │ • 384-dim        │
└─────────────────┘  └───────────────┘  └──────────────────┘
```
