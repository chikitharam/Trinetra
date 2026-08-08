# Trinetra
Trinetra is an AI-powered cyber threat intelligence and awareness platform that uses Open Source Intelligence  to identify emerging cyber threats, explain them in simple language, provide community-specific alerts, AI assistance, victim experiences, trusted helplines, and actionable guidance to help users stay informed, protected, and cyber-aware.

trinetr/
├── frontend/                  # Next.js 14 (App Router) + TypeScript + Tailwind CSS
│   ├── src/
│   │   ├── app/               # Landing, Dashboards, Alerts, Threat Detail, AI Chat, Helpline, Admin
│   │   ├── components/        # Glass panel, RiskMeter, Heatmap, StatBadge, Navbar, Footer
│   │   ├── lib/               # Axios API client with offline mock fallback
│   │   └── types/             # TypeScript definitions
│   └── Dockerfile
├── backend/                   # Python FastAPI Backend
│   ├── app/
│   │   ├── api/v1/            # Auth, Threats, AI Chat, Helplines, Reviews, Search, Analytics, Admin
│   │   ├── ai/                # Classification, Plain-English Simplifier, FAISS Vector Index, RAG
│   │   ├── core/              # Config, Security (JWT/Bcrypt), Session
│   │   ├── models/            # SQLAlchemy 2.0 Async Models
│   │   ├── schemas/           # Pydantic v2 schemas
│   │   └── db/                # Seed script populating sample dataset
│   ├── tests/                 # Pytest test suite
│   └── Dockerfile
├── docker-compose.yml         # Full Stack Orchestrator (Frontend, Backend, Postgres, Redis)
├── nginx.conf                 # Reverse Proxy Configuration
└── README.md
```
