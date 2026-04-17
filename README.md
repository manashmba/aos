# AOS — Agentic Operating System

> **The ERP Replacement for the AI Era**

A ground-up conversational, agentic operating system that replaces traditional ERP systems for mid-market enterprises. Business users interact through natural language, role-based copilots, autonomous agents, and event-driven workflows instead of rigid ERP screens.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│  CLIENTS: Web App │ WhatsApp Bot │ Mobile │ Voice │ API      │
├──────────────────────────────────────────────────────────────┤
│  API Gateway + Auth (JWT + RBAC + ABAC)                      │
├──────────────────────────────────────────────────────────────┤
│  Conversation Service → Intent Parser → Context Resolver     │
├──────────────────────────────────────────────────────────────┤
│  LLM Gateway (Claude / GPT-4o / Gemini — model router)      │
├──────────────────────────────────────────────────────────────┤
│  Agent Orchestration Engine                                   │
│  ├─ Interface Agents (role-based copilots)                   │
│  ├─ Reasoning Agents (planner, decomposer)                   │
│  ├─ Domain Agents (finance, procurement, inventory...)       │
│  ├─ Action Agents (transaction, notification, document)      │
│  ├─ Governance Agents (policy, audit, anomaly, compliance)   │
│  └─ Memory Agents (retrieval, ontology, precedent)           │
├──────────────────────────────────────────────────────────────┤
│  Policy Engine │ Workflow Engine │ Rules Engine               │
├──────────────────────────────────────────────────────────────┤
│  Event Bus (Redis Streams / Kafka)                           │
├──────────────────────────────────────────────────────────────┤
│  PostgreSQL │ pgvector │ Redis │ S3 │ Audit Log              │
├──────────────────────────────────────────────────────────────┤
│  Integrations: GSTN │ Banking │ WhatsApp │ Tally │ Email     │
└──────────────────────────────────────────────────────────────┘
```

## Core Principle

> **Generative AI interprets intent. Deterministic engines execute transactions.**
>
> The LLM never writes directly to the ledger. Every financial transaction passes through validation, policy checks, human approval, and deterministic posting.

## Project Structure

```
CRM/
├── aos-backend/          # Python FastAPI backend
│   ├── app/
│   │   ├── api/          # REST API endpoints
│   │   ├── core/         # Config, security, dependencies
│   │   ├── models/       # SQLAlchemy database models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # Business logic by domain
│   │   ├── agents/       # AI agent classes
│   │   ├── engine/       # Policy, ledger, workflow engines
│   │   ├── integrations/ # External system connectors
│   │   ├── memory/       # Memory management layer
│   │   ├── middleware/   # Auth, logging, rate limiting
│   │   └── utils/        # Shared utilities
│   ├── migrations/       # Alembic DB migrations
│   └── tests/            # Test suites
├── aos-frontend/         # React + TypeScript frontend
│   └── src/
│       ├── components/   # UI components by domain
│       ├── pages/        # Page-level views
│       ├── hooks/        # Custom React hooks
│       ├── services/     # API client services
│       ├── store/        # State management
│       └── types/        # TypeScript type definitions
├── whatsapp-bot/         # WhatsApp Business API bot
├── deploy/               # Docker, K8s, Terraform configs
├── docs/                 # Architecture and API docs
└── scripts/              # Setup and utility scripts
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 + FastAPI |
| Agent Framework | LangGraph + Custom Orchestrator |
| LLM | Claude Sonnet (primary) + GPT-4o (fallback) |
| Database | PostgreSQL 16 + pgvector |
| Cache | Redis 7 |
| Frontend | React 18 + TypeScript + Tailwind + shadcn/ui |
| WhatsApp | Meta Cloud API |
| Workflow | Temporal.io (later) / Custom async (MVP) |
| Auth | JWT + RBAC + ABAC |
| Hosting | AWS ap-south-1 (India data residency) |

## Modules

1. **Finance** — AP, AR, GL, tax, compliance, month-end close
2. **Procurement** — Vendor mgmt, RFQ, PO, GRN, invoice matching
3. **Inventory** — Stock, reorder, batch tracking, dispatch, cycle count
4. **Sales** — Quotations, orders, pricing, credit, collections
5. **Manufacturing** — BOM, MRP, scheduling, quality, wastage
6. **HR** — Workflows, reimbursements, attendance, payroll, policy Q&A

## Quick Start

```bash
# Backend
cd aos-backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env       # Configure your environment
alembic upgrade head       # Run migrations
uvicorn app.main:app --reload

# Frontend
cd aos-frontend
npm install
cp .env.example .env.local
npm run dev
```

## License

Proprietary — All rights reserved.
