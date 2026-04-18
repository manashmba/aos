# AOS — Agentic Operating System

> **The ERP Replacement for the AI Era**

A ground-up conversational, agentic operating system that replaces
traditional ERP for Indian mid-market enterprises. Business users
interact through natural language, role-based copilots, and
event-driven workflows instead of rigid ERP screens.

```
┌──────────────┐      ┌──────────────┐      ┌─────────────────┐
│  Web (React) │─────▶│   Backend    │◀────▶│   PostgreSQL    │
└──────────────┘      │  (FastAPI)   │      │  + pgvector     │
┌──────────────┐      │              │      └─────────────────┘
│  WhatsApp    │─────▶│  Orchestrator│      ┌─────────────────┐
│   Bot (TS)   │      │  + Policy    │◀────▶│     Redis       │
└──────────────┘      │  + Ledger    │      │  (streams+cache)│
                      │  + Audit     │      └─────────────────┘
                      └──────┬───────┘
                             │
                   ┌─────────┴────────────┐
                   ▼                      ▼
              Claude Sonnet           Integrations
              (w/ GPT-4o fallback)    (GST/Bank/Tally/
                                       Email/OCR/WA)
```

## Core Principle

> Generative AI interprets intent. Deterministic engines execute
> transactions.
>
> The LLM never writes directly to the ledger. Every financial action
> passes through policy evaluation, optional human approval, and
> deterministic posting with idempotency keys.

## Repositories in this monorepo

| Path | Purpose |
|------|---------|
| `aos-backend/`  | FastAPI + async SQLAlchemy + Alembic. Agents, policy engine, ledger, audit, domain services (finance, procurement, inventory, sales, HR, manufacturing), integrations layer. |
| `aos-frontend/` | Vite + React + TypeScript + Tailwind. Chat UI, dashboard, trial balance, audit viewer. |
| `whatsapp-bot/` | Express + TypeScript bridge between WhatsApp Business Cloud API and the backend's conversation service. |
| `deploy/`       | Kubernetes manifests, Prometheus config, Docker assets. |
| `docs/`         | Blueprint, runbooks, diagrams. |

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 + FastAPI + async SQLAlchemy 2.0 |
| Agent framework | Custom Orchestrator (LangGraph-ready) |
| LLM | Claude Sonnet (primary) + GPT-4o-mini (fallback) |
| Database | PostgreSQL 16 + pgvector |
| Cache / streams | Redis 7 |
| Frontend | React 18 + TypeScript + Tailwind + shadcn-style primitives |
| WhatsApp | Meta Cloud API |
| Auth | JWT + RBAC |
| Observability | Prometheus + Grafana + structlog |
| Hosting | AWS ap-south-1 (India data residency) |

## Quick start — full stack in Docker

```bash
cp .env.example .env       # fill in ANTHROPIC_API_KEY, JWT_SECRET_KEY, …
make up                    # builds + starts everything
make migrate               # run DB migrations
open http://localhost:5173 # web app
```

URLs:
- Backend: http://localhost:8000 (Swagger at `/docs`)
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- Bot webhook: http://localhost:3001/webhook

## Development — run services directly

```bash
make backend-dev     # uvicorn with reload on :8000
make frontend-dev    # vite on :5173 (proxies /api -> :8000)
make bot-dev         # tsx watch on :3001
make backend-test    # pytest
```

## Architecture highlights

- **Conversation → Agent → Tool pipeline**: router classifies intent,
  domain agent plans tool calls via Claude (OpenAI fallback),
  orchestrator evaluates each call against the policy engine, then
  executes deterministic tools.
- **Policy engine**: per-domain YAML rule packs (finance, procurement,
  sales, inventory, HR, agent) with `require_approval`, `block`,
  `warn` effects. Tunable INR-calibrated thresholds.
- **Ledger engine** (`app/engine/ledger`): declarative posting rules
  map business events (e.g. `sales.invoice_posted`, `hr.payroll_run`)
  to balanced double-entry JEs with Indian CoA codes. Idempotent
  postings and fiscal period locks.
- **Audit**: append-only `audit_logs` with SHA-256 hash chain —
  `GET /api/v1/audit/verify` walks the chain and reports the first
  broken link.
- **Integrations**: pluggable protocol + mock for WhatsApp, GSTN/IRP,
  banking, email, Tally, OCR.
- **Observability**: Prometheus metrics at `/metrics`; structlog JSON
  logs with `correlation_id` bound per request.

## Modules

1. **Finance** — AP, AR, GL, tax, compliance, month-end close
2. **Procurement** — Vendor mgmt, RFQ, PO, GRN, three-way match
3. **Inventory** — Stock, reorder, batch tracking, dispatch, cycle count
4. **Sales** — Quotations, orders, pricing, credit, collections
5. **Manufacturing** — BOM, material availability, production orders
6. **HR** — Onboarding, leave, reimbursement, attendance, payroll

## Deployment

- `docker-compose.yml` brings up a single-host stack (Postgres, Redis,
  backend, frontend, whatsapp-bot, Prometheus, Grafana).
- `deploy/k8s/` has namespace, postgres StatefulSet, redis Deployment,
  backend/frontend/bot Deployments with HPA, Ingress with TLS.
- CI workflow is available at `deploy/ci.yml.sample` — copy it to
  `.github/workflows/ci.yml` when pushing with a PAT that has the
  `workflow` scope.

## License

Proprietary — All rights reserved.
