# OmniAgent

> **A Multi-Tenant Autonomous Deep Agents Platform** powered by **FastAPI**, **LangGraph**, and **React 19** (`assistant-ui`).

OmniAgent provides every user with a private, isolated AI agent workspace, durable long-term memory, customizable skills, and **MCP (Model Context Protocol)** tools—complete with Human-in-the-Loop (HITL) approval controls, Generative UI widgets, and native Google Gemini integration.

---

## Key Features

- **Google Gemini & Multi-Provider Architecture:** Built with native Google Gemini (`gemini-2.0-flash`) support by default. Easily plug in Anthropic Claude, OpenAI, AWS Bedrock, or any local/custom LLM endpoint via the Providers tab.
- **Model Context Protocol (MCP) Integration:** Extensible tool execution via industry-standard MCP servers (stdio and HTTP transports), allowing agents to interact with external databases, APIs, and file systems.
  - 🎬 **YouTube Search MCP Server:** Automatically search videos, extract direct links, and preview content.
  - 💬 **WhatsApp Dispatch MCP Server:** Verify phone numbers and dispatch WhatsApp messages with safe/Twilio gateways.
  - 🌐 **Web Search MCP Server:** Live web searches via DuckDuckGo and webpage reader.
  - 📁 **Workspace Filesystem MCP:** Agent-driven file management, folder creation, and downloads.
- **Human-in-the-Loop (HITL) Safety:** Sensitive tool calls and execution actions pause for explicit user confirmation before running.
- **Per-User Workspaces & Durable Memory:** Real per-thread file system workspaces (downloadable assets, code files, and inline media previews) combined with cross-session memory (`AGENTS.md`).
- **Generative UI & Canvas:** Agents can render interactive JSON component cards (`render_ui`) or isolated interactive HTML widgets (`render_html`) directly inside the chat.
- **Single-Process Deployment:** Fast and unified architecture where a single FastAPI process serves both the backend `/v1` JSON/SSE streaming API and the compiled React 19 SPA.

---

## High-Level System Architecture

```
React 19 SPA (assistant-ui)
     │  HTTPS / Cookie Auth
     ▼  POST /v1/runs (SSE Stream)
FastAPI Backend (:8080)
     ├── App Database (SQLite / PostgreSQL)
     ├── LangGraph Engine & Agent Graph Cache
     ├── MCP Runtime & Tool Connectors (YouTube, WhatsApp, Web, FS)
     ├── User File Workspaces (/data/workspaces)
     └── LLM Providers (Google Gemini / Anthropic / OpenAI)
```

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 19, TypeScript, Vite 8, Tailwind CSS v4, `assistant-ui`, Radix UI, Zustand, TanStack Query |
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy, Alembic, `sse-starlette` |
| **AI & Orchestration** | LangGraph, `deepagents`, Model Context Protocol (MCP) Client |
| **Database & Cache** | SQLite (Dev Mode) / PostgreSQL 16 (Local/Prod), In-Memory Agent Cache |
| **Containerization** | Docker, Docker Compose (Multi-stage build) |

---

## Quick Start (Docker)

### 1. Configure Environment
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```
Generate random secrets for session and credential encryption:
```bash
python -c "import secrets, base64, os; print('JWT_SECRET=' + secrets.token_hex(32)); print('CREDENTIAL_ENCRYPTION_KEY=' + base64.urlsafe_b64encode(os.urandom(32)).decode())"
```
Add your **Google Gemini API Key** to `.env`:
```text
GEMINI_API_KEY=your_gemini_api_key_here
```

### 2. Build and Launch
```bash
docker compose up --build
```

### 3. Open Web UI
Navigate to **`http://localhost:8080`** in your browser, create an account, and start chatting with your autonomous agent!

---

## Repository Structure

```
├── backend/                  # FastAPI + LangGraph + deepagents engine
│   ├── app/
│   │   ├── agent/            # Agent graphs, prompts, middleware, SSE runs
│   │   ├── core/             # Config, Auth, Context, Utilities
│   │   ├── db/               # SQLAlchemy models, SQLite/PG engine, seeds
│   │   ├── routes/           # API routers (auth, models, mcp, runs, workspace)
│   │   └── stores/           # MCP runtime, persistence checkpointers
│   └── mcp_servers/          # Bundled MCP servers (youtube_server, whatsapp_server, workspace_fs)
├── frontend/                 # React 19 + Vite 8 SPA
│   └── src/
│       ├── components/       # assistant-ui threads, workspace dock, generative UI
│       ├── routes/           # Chat, Settings, MCP, Memory, Providers panels
│       └── store/            # Zustand chat and settings stores
├── docker-compose.yml        # All-in-one container stack
└── Dockerfile                # Multi-stage production container build
```

---

## License
MIT License.
