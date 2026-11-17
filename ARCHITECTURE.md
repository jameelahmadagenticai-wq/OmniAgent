# ARCHITECTURE.md

> Architecture overview for **OmniAgent** — a multi-tenant Autonomous Deep Agents platform.
> Format follows the [architecture.md](https://architecture.md/) template.

OmniAgent is a **single FastAPI process** that serves a **React 19 SPA** and a **`/v1` JSON/SSE API** on one port (`:8080`). Each user gets a private, isolated agent workspace, long-term memory, skills, and MCP tools. One compiled agent per `(run/chat, user, model, reasoning, genui)` is cached in-process; every request carries its own `user_id` + `thread_id` for tenant isolation.

---

## 1. Project Structure

```
OmniAgent/
├── Dockerfile                 # multi-stage: node:22 builds SPA → python:3.13-slim runs uvicorn + serves dist
├── docker-compose.yml         # baked stack: backend(:8080) + profile-gated infra (localdb/sandbox/observability)
├── docker-compose.dev.yml     # infra only (no backend) — run the backend on the host
├── sandbox.toml               # OpenSandbox server config (runtime/egress/network hardening)
├── ARCHITECTURE.md            # system design specification
├── README.md                  # project overview and quickstart
├── scripts/                   # start_all.sh, db-init scripts, serve.sh …
├── data/workspaces/           # dev agent workspace files (prod → /data volume)
│
├── backend/                   # FastAPI + deepagents + LangGraph (Python 3.11+)
│   ├── pyproject.toml         # deps: deepagents, langgraph, langchain-*, fastapi, sqlalchemy, psycopg, alembic …
│   ├── alembic/               # DB migrations
│   ├── static/                # brand assets / favicons served at /static
│   ├── mcp_servers/           # bundled MCP servers (youtube_server, whatsapp_server, omniagent_demo, workspace_fs)
│   └── app/
│       ├── main.py            # app assembly + lifespan (env load, DB init/seed, persistence, agent warm-up, SPA mount)
│       ├── core/              # config.py (Settings), auth.py, context.py, constants, enums, text/time utils
│       ├── db/                # models.py (SQLAlchemy schema), engine.py, crypto.py (Fernet), seed.py, seeds/*.sql
│       ├── agent/             # agent.py (build+cache), prompts.py, middleware.py, runs.py (SSE+HITL), agent_common.py
│       ├── routes/            # one APIRouter per concern: auth, models, mcp, skills, memory, workspace,
│       │                      #   settings_ui, chat, runs, sessions, health (+ deps.py)
│       ├── stores/            # sessions, users, usersettings, skills_store, mcp_runtime, memory_store,
│       │                      #   persistence (checkpointer/store), dbfs (DB→agent-FS bridge)
│       ├── workspace/         # workspace.py (per-thread files), media.py (/v1/media; office→PDF)
│       └── sandbox/           # OpenSandbox integration (opt-in code/shell execution)
│
└── frontend/                  # React 19 + Vite 8 SPA (assistant-ui external store)
    ├── package.json           # assistant-ui, tailwind v4, zustand, tanstack-query, react-router 7, biome
    └── src/
        ├── main.tsx  App.tsx  providers.tsx
        ├── runtime/           # OmniAgentRuntimeProvider.tsx (external-store runtime + custom SSE), workspaceAttachment.ts
        ├── routes/            # ChatPage, SettingsPage, McpPanel, SkillsPanel, MemoryPanel, ProvidersPanel, AuthPage
        ├── components/
        │   ├── assistant-ui/  # thread, tool-uis, generative-ui, html-canvas, reasoning, media-part, dot-matrix …
        │   ├── chat/          # ConversationSidebar, ModelPicker, WorkspaceDock, DownloadButton
        │   ├── layout/        # AppShell, PanelLayout, ConnectionStatus
        │   ├── memory/ skills/ settings/ auth/ ui/(shadcn)
        ├── store/             # zustand: chat.ts, settings.ts
        ├── api/               # client.ts, queries.ts (TanStack), sessions, auth, workspace, types …
        └── i18n/              # config + 16 locale files
```

---

## 2. High-Level System Diagram

```
                         ┌──────────────────────────────────────────────┐
  Browser (SPA)          │            OmniAgent backend (:8080)         │
  React 19 + assistant-ui│                                               │
  external-store runtime │  FastAPI app (single process, many users)     │
        │  HTTPS          │   ├─ /static, /favicon, SPA (app.frontend()) │
        │  cookie auth    │   ├─ /v1/* routers (auth, models, mcp,       │
        ├────────────────►│   │     skills, memory, workspace, settings, │
        │  POST /v1/runs  │   │     chat, runs, sessions, health)        │
        │◄──── SSE ───────│   └─ Agent engine (deepagents + LangGraph)   │
                          │        • per-(user,model,…) compiled-agent   │
                          │          cache  • HITL interrupt_on gating   │
                          └───────┬───────────────┬──────────────┬───────┘
                                  │               │              │
                       ┌──────────▼──┐   ┌────────▼───────┐  ┌───▼─────────────┐
                       │ Relational  │   │  LangGraph     │  │ Workspace files │
                       │ app DB      │   │  checkpointer  │  │ WORKSPACE_ROOT  │
                       │ (SQLite/PG) │   │  (chat history)│  │  /data volume   │
                       └─────────────┘   └────────────────┘  └─────────────────┘
                                  │
              ┌───────────────────┼─────────────────────┬───────────────────┐
        Model providers      MCP servers          SMTP (OTP)      OpenSandbox (opt-in)
      (Google Gemini /       (stdio/http;                         per-session containers
       Anthropic / OpenAI)    youtube, whatsapp,                  on isolated network
                              web-search, fs, …)
```

Request shapes:
- **Chat/runs**: `POST /v1/runs` → agent streams tokens, tool calls, and approval interrupts back over **SSE** (`sse-starlette`). The SPA's `OmniAgentRuntimeProvider` is an assistant-ui **external-store** runtime fed by this custom SSE stream.
- **Everything else** (settings, skills, MCP CRUD, memory, workspace files, sessions) is plain JSON over `/v1/*`.

---

## 3. Core Components

### Backend — FastAPI app (`backend/app/main.py`)
- Owns application lifespan (load `.env` → init DB schema/seeds → open checkpointer persistence → warm default Google Gemini agent).
- Mounts APIRouters per concern and serves the built SPA on port `8080`.

### Agent Engine (`backend/app/agent/`)
- `agent.py` builds and caches compiled deepagents graphs keyed by `("run"|"chat", user_id, model_id, effort, genui)`.
- Tools assembled per build:
  - Global & per-user MCP tools (loaded dynamically via `langchain-mcp-adapters`).
  - Bundled tools: `youtube-tools` (video search), `whatsapp-tools` (messaging dispatch), `web-search`, and `workspace-fs`.
  - Generative UI tools (`render_ui`, `render_html`).
- `runs.py` drives the SSE run loop and **Human-in-the-Loop (HITL) approvals** (`interrupt_on` gates external tool actions).

### Frontend — React 19 SPA (`frontend/`)
- Built on **React 19**, **Vite 8**, **Tailwind CSS v4**, and **`@assistant-ui/react`**.
- Native dark mode with rich Markdown rendering, inline Mermaid diagrams, audio/video previews, and Generative UI widgets.
- Draggable navigation rail, conversation history sidebar, and thread workspace file dock.
