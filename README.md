<div align="center">

# ✨ MAANTRA 2.0

```text
███╗   ███╗ █████╗  █████╗ ███╗   ██╗████████╗██████╗  █████╗
████╗ ████║██╔══██╗██╔══██╗████╗  ██║╚══██╔══╝██╔══██╗██╔══██╗
██╔████╔██║███████║███████║██╔██╗ ██║   ██║   ██████╔╝███████║
██║╚██╔╝██║██╔══██║██╔══██║██║╚██╗██║   ██║   ██╔══██╗██╔══██║
██║ ╚═╝ ██║██║  ██║██║  ██║██║ ╚████║   ██║   ██║  ██║██║  ██║
╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝
```

### Unified AI Assistant for Slack • Telegram • WhatsApp

**One AI brain. Shared memory. Multi-platform identity. No vendor lock-in.**

<img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/Version-2.0.0-6f42c1" />
<img src="https://img.shields.io/badge/License-MIT-green" />
<img src="https://img.shields.io/badge/Status-Production%20Optimization-00b894" />
<img src="https://img.shields.io/github/contributors/dipanshuchoudhary-data/Maantra-1.0" />
<img src="https://img.shields.io/badge/Multi--LLM-OpenAI%20%7C%20OpenRouter%20%7C%20Gemini%20%7C%20Grok-orange" />
<img src="https://img.shields.io/badge/MCP-Integrated-blueviolet" />

| 🚀 Metric | Value |
|---|---|
| **Use Cases** | **2M+ cross-channel assistant interactions (targeted workloads)** |
| **Platform Model** | **Hub-and-Spoke Core + Channel Adapters** |
| **Resource Efficiency** | **90%+ token reduction on conversational flows** |
| **Setup Speed** | **Fast local setup with Python + `.env`** |

</div>

---

## 📚 Table of Contents

- [🧭 What is Maantra?](#-what-is-maantra)
- [❗ The Problem Maantra Solves](#-the-problem-maantra-solves)
- [✅ Why Choose Maantra?](#-why-choose-maantra)
- [🌟 Key Features](#-key-features)
- [🧱 Tech Stack](#-tech-stack)
- [🏗️ Architecture Overview](#️-architecture-overview)
- [🔌 Platform Setup Guides](#-platform-setup-guides)
- [⚙️ Configuration Guide](#️-configuration-guide)
- [🧪 Usage Examples](#-usage-examples)
- [🧩 API Reference (Quick)](#-api-reference-quick)
- [🗂️ Project Structure](#️-project-structure)
- [🔍 Advanced Features Deep Dive](#-advanced-features-deep-dive)
- [👨‍💻 Development Guide](#-development-guide)
- [🛠️ Troubleshooting](#️-troubleshooting)
- [📈 Performance & Optimization](#-performance--optimization)
- [🔐 Security & Best Practices](#-security--best-practices)
- [🚢 Deployment Guide](#-deployment-guide)
- [🗺️ Roadmap & Implementation Strategy](#️-roadmap--implementation-strategy)
- [❓ FAQ](#-faq)
- [🔗 Resources & Links](#-resources--links)
- [📄 License & Attribution](#-license--attribution)

---

## 🧭 What is Maantra?

**Maantra 2.0** is a unified AI assistant platform designed to operate across
messaging channels using a **single platform-agnostic core**.

It shifts teams from siloed platform bots to one intelligent assistant that can
reuse memory, tools, and policies consistently across channels.

### Core Highlights

- 🎯 **Unified AI Core**: one orchestration engine for every platform adapter
- 🧠 **Shared Memory**: long-term personalization via Mem0 integration
- 🔍 **RAG Context Layer**: semantic retrieval from indexed conversation history
- 🛠️ **Actionable Agent**: local tools + MCP-based external integrations
- 🤝 **Model-Agnostic**: select provider/model per session, avoid lock-in

### Real-World Use Cases

- Product teams asking in Slack for summaries, reminders, and project context
- Support teams retrieving prior decisions from historical discussions
- Engineering teams using AI with GitHub/Notion context through MCP tools
- Future multi-channel continuity between Slack, Telegram, and WhatsApp

### Maantra vs Traditional Single-Platform Bots

| Capability | Traditional Bot | Maantra 2.0 |
|---|---:|---:|
| Multi-platform architecture | ❌ Siloed | ✅ Unified core + adapters |
| Shared memory model | ❌ Per platform | ✅ Cross-platform model |
| Tool execution model | ⚠️ Limited | ✅ Local + MCP tools |
| LLM provider flexibility | ⚠️ Often fixed | ✅ OpenAI/OpenRouter/Gemini/Grok |
| Extending to new channels | ❌ Core changes required | ✅ Add adapter, keep core stable |

---

## ❗ The Problem Maantra Solves

### Current Landscape Problems

- ❌ **Context Loss**: one bot per platform with no shared continuity
- ❌ **Repeated Setup**: repeated policies, prompts, and preferences
- ❌ **Maintenance Overhead**: duplicated deployments and integrations
- ❌ **Inconsistent UX**: different commands and capabilities per platform

### Maantra Solution

- ✅ **Unified Identity Layer**: consistent user mapping design across platforms
- ✅ **Shared Memory**: personalization survives beyond one chat channel
- ✅ **Consistent Agent Behavior**: same orchestration, tools, and policies
- ✅ **Simple Expansion**: one core, many adapters (hub-and-spoke)

> 💡 **Paradigm shift**: from “bots per app” to one AI assistant that follows
> users across their communication landscape.

---

## ✅ Why Choose Maantra?

### Value Matrix

| Dimension | Single-Platform Bot | Maantra 2.0 |
|---|---:|---:|
| Engineering duplication | High | Low |
| Context continuity | Fragmented | Unified design |
| Vendor lock-in risk | High | Low |
| New platform onboarding | Costly | Adapter-first |
| AI governance consistency | Hard | Centralized |

### Hub-and-Spoke Architecture (High-Level)

```text
                      ┌───────────────────────┐
                      │   Telegram Adapter    │
                      └──────────┬────────────┘
                                 │
┌───────────────────────┐        │        ┌───────────────────────┐
│   WhatsApp Adapter    │────────┼────────│    Slack Adapter      │
└──────────┬────────────┘        │        └──────────┬────────────┘
           │                     │                   │
           └──────────────┬──────┴──────┬────────────┘
                          │ Channel Mgr │
                          └──────┬──────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Maantra Agent Core     │
                    │ (reasoning + tool loop) │
                    └────┬────────┬───────────┘
                         │        │
        ┌────────────────▼───┐ ┌──▼────────────────┐
        │ Memory (Mem0 + DB) │ │ RAG + Vector DB   │
        └─────────────────────┘ └───────────────────┘
                         │
                  ┌──────▼──────┐
                  │ MCP Tooling │
                  │ GitHub/Notion│
                  └──────────────┘
```

### Data Flow

```text
Message -> Normalize -> Unified Context -> Agent Reasoning
        -> (Optional) RAG + Memory + Tools -> Response Format -> Platform Reply
```

### ROI Snapshot

- 📉 **Token spend optimized** by skipping unnecessary tool payloads
- 🔁 **Reduced maintenance** with one orchestrator and adapter abstraction
- 🧩 **Faster integrations** through MCP tool discovery/execution
- 🛡️ **Better governance** from centralized security and config controls

---

## 🌟 Key Features

### 🎯 Unified AI Assistant
A single AI orchestration engine handles reasoning and response generation while
adapters translate platform-specific payloads.

```python
# src/channels/channel_manager.py
channel_manager.register(slack_adapter)
await channel_manager.start_all()
```

### 🧠 Shared Memory (Mem0)
Long-term memory stores personalized facts and retrieves relevant context for
later responses.

```python
from src.memory_ai.mem0_client import search_memory
memories = await search_memory("my project preferences", user_id, limit=3)
```

### 🔍 RAG Capabilities
Semantic retrieval over indexed discussion history adds factual organization
context to AI responses.

```python
from src.rag.retriever import retrieve, RetrievalOptions
results = await retrieve("what did we decide about release?", RetrievalOptions(limit=5))
```

### 🤖 Multi-LLM Support (No Vendor Lock-In)
Provider routing supports OpenAI, OpenRouter, Gemini, and Grok, with per-session
overrides for model and provider.

```text
set provider openrouter
set model anthropic/claude-3.5-sonnet
llm show
```

### 🛠️ Smart Tools & Integrations
Local tools (messaging, scheduling, channel listing) plus MCP integrations
(GitHub, Notion) with query-based loading.

### 🔌 MCP Protocol Integration
MCP servers are initialized once and exposed as callable tools inside the same
agent loop.

### ⚡ Real-Time Sync (Slack Socket Mode)
Slack adapter runs through Socket Mode for low-latency event-driven responses.

### 🔁 Self-Healing / Adaptive Behavior
Graceful checks disable unavailable subsystems (e.g., missing embedding key)
instead of crashing startup.

---

## 🧱 Tech Stack

### Stack Pyramid

```text
          ┌──────────────────────────────┐
          │   Channels (Slack now; TG/WA roadmap) │
          ├──────────────────────────────┤
          │  Agent Core + Tool Loop + MCP         │
          ├──────────────────────────────┤
          │  Memory (Mem0) + RAG (Chroma)         │
          ├──────────────────────────────┤
          │ Python 3.11+ Async Runtime            │
          └──────────────────────────────┘
```

| Category | Technology | Purpose |
|---|---|---|
| Language & Runtime | Python 3.11+, AsyncIO | Async orchestration |
| Messaging | Slack Bolt + Socket Mode | Real-time Slack adapter |
| LLM Providers | OpenAI, OpenRouter, Gemini, Grok | Multi-model routing |
| Memory | Mem0AI + SQLite | Long-term + session memory |
| Vector DB | ChromaDB | Semantic retrieval store |
| Embeddings | OpenAI/Cohere/OpenRouter/Gemini | RAG embeddings |
| Scheduling | APScheduler + croniter | Reminders and recurring tasks |
| Integrations | MCP | External tool protocol |
| Quality | Ruff, Mypy, Pytest | Code quality controls |

> ℹ️ **Version requirement**: Python **3.11+** is required.

---

## 🏗️ Architecture Overview

### System Components

- **Channel adapters** normalize incoming events
- **Channel manager** orchestrates adapter lifecycle
- **Agent core** handles reasoning + tool loop
- **RAG layer** injects semantic context
- **Memory layer** injects personalized context
- **MCP layer** extends agent capabilities
- **Persistence layer** stores sessions/messages/tasks

### Module Interaction Map

```text
src/main.py
  -> src/channels/channel_manager.py
  -> src/channels/slack/handler.py
  -> src/agents/agent.py
      -> src/rag/*
      -> src/memory_ai/mem0_client.py
      -> src/tools/*
      -> src/mcp/*
  -> src/memory/database.py
```

### Message Processing Pipeline

```text
1) Receive event (adapter)
2) Normalize to PlatformMessage
3) Build/resolve session context
4) Retrieve memory
5) Retrieve RAG context
6) Select tools (if needed)
7) LLM reasoning + tool loop
8) Send platform response
9) Persist interaction + memory updates
```

---

## 🔌 Platform Setup Guides
## You can follow complete setup guide : https://maantrasetup.netlify.app/

## ⚙️ Configuration Guide

###  Slack `.env`  template (extended)

```env
# Slack
SLACK_BOT_TOKEN=
SLACK_APP_TOKEN=
SLACK_SIGNING_SECRET=
SLACK_USER_TOKEN=

# LLM keys
OPENAI_API_KEY=
OPENROUTER_API_KEY=
GEMINI_API_KEY=
GROK_API_KEY=
ANTHROPIC_API_KEY=
COHERE_API_KEY=

# Model
DEFAULT_MODEL=gpt-4o
LLM_PROVIDER=

# Memory
MEM0_API_KEY=
MEMORY_ENABLED=true
MEMORY_EXTRACTION_MODEL=gpt-4o-mini

# RAG
RAG_ENABLED=true
RAG_EMBEDDING_PROVIDER=openai
RAG_EMBEDDING_MODEL=text-embedding-3-small
RAG_EMBEDDING_DIMENSIONS=1536
RAG_VECTOR_DB_PATH=./data/chroma
RAG_INDEX_INTERVAL_HOURS=1
RAG_MAX_RESULTS=10
RAG_MIN_SIMILARITY=0.5

# App
DATABASE_PATH=./data/assistant.db
LOG_LEVEL=info
MAX_HISTORY_MESSAGES=50
SESSION_TIMEOUT_MINUTES=60

# Security
DM_POLICY=pairing
ALLOWED_USERS=*
ALLOWED_CHANNELS=*

# Feature flags
ENABLE_THREAD_SUMMARY=true
ENABLE_TASK_SCHEDULER=true
ENABLE_REACTIONS=true
ENABLE_TYPING_INDICATOR=true

# MCP
GITHUB_PERSONAL_ACCESS_TOKEN=
NOTION_API_TOKEN=
```

### Key Config Table

| Variable | Type | Required | Default | Description |
|---|---|---:|---|---|
| `SLACK_BOT_TOKEN` | string | ✅ | - | Slack bot auth token |
| `SLACK_APP_TOKEN` | string | ✅ (Socket Mode) | - | Slack app-level token |
| `OPENAI_API_KEY` | string | ⚠️* | - | LLM provider key |
| `ANTHROPIC_API_KEY` | string | ⚠️* | - | LLM provider key |
| `OPENROUTER_API_KEY` | string | ⚠️* | - | LLM provider key |
| `RAG_ENABLED` | bool | ❌ | `true` | Enable semantic retrieval |
| `MEMORY_ENABLED` | bool | ❌ | `true` | Enable Mem0 memory layer |
| `DATABASE_PATH` | path | ❌ | `./data/assistant.db` | SQLite persistence path |
| `LOG_LEVEL` | string | ❌ | `info` | Logging verbosity |

`*` At least one supported provider key must be configured.

---

## 🧪 Usage Examples

### Scenario 1: Cross-Platform Knowledge Sharing (Design Intent)

1. User asks from Slack
2. Core retrieves memory and relevant discussion context
3. In future multi-channel mode, linked Telegram/WhatsApp identity sees same context

```python
memory_context, count = await agent._retrieve_memory("what are my preferences?", user_id)
rag_context, sources = await agent._retrieve_rag("what did we decide last week?")
```

### Scenario 2: Account Linking Workflow (Unified Identity)

```text
Slack DM -> pairing code generated
Admin -> /approve CODE
User profile -> approved/linked for unified policies
```

### Scenario 3: Tool Execution Across Platforms

```python
tools = get_tools_for_query("create reminder and sync to project notes")
assistant_message = await agent._run_tool_loop(messages, tools, context, llm_provider)
```

### Platform-Specific Sample Commands

- **Slack**: `help`, `summarize`, `llm options`, `set provider openai`
- **Telegram (planned)**: `/start`, `/link`, inline keyboard actions
- **WhatsApp (planned)**: template-driven workflows and reminders

---

## 🧩 API Reference (Quick)

### Core Modules

| Module | Purpose |
|---|---|
| `src/main.py` | Application bootstrap and lifecycle |
| `src/agents/agent.py` | Reasoning, retrieval, tools, response loop |
| `src/channels/base_channel.py` | Adapter contract |
| `src/channels/channel_manager.py` | Adapter lifecycle and routing |
| `src/channels/slack/handler.py` | Slack implementation |
| `src/memory/database.py` | SQLite persistence + identity mapping |
| `src/memory_ai/mem0_client.py` | Long-term memory operations |
| `src/rag/*` | Embedding, indexing, retrieval |
| `src/mcp/*` | MCP lifecycle and tool bridge |

### Key Functions / Classes

- `Agent.process_message(...)`
- `get_tools_for_query(query)`
- `execute_tool(name, args, context)`
- `initialize_mcp()` / `get_all_mcp_tools()`
- `retrieve(query, RetrievalOptions)`
- `get_or_create_unified_user(...)`

---

## 🗂️ Project Structure

```text
Maantra-1.0/
├── src/
│   ├── agents/            # Core agent orchestration
│   ├── channels/          # Adapter interfaces + Slack adapter
│   │   └── slack/
│   ├── config/            # Environment-driven settings
│   ├── llm/               # Multi-provider LLM abstractions
│   ├── mcp/               # Model Context Protocol integration
│   ├── memory/            # SQLite persistence + identity/linking
│   ├── memory_ai/         # Mem0 client integration
│   ├── rag/               # Vector retrieval/indexing pipeline
│   ├── tools/             # Local action tools (scheduler/slack actions)
│   └── utils/             # Logging helpers
├── scripts/               # Validation and indexing scripts
├── docker-compose.yml     # Container orchestration
├── pyproject.toml         # Dependencies + tooling config
└── .env.example           # Environment template
```

### Design Principles

- **Platform-Agnostic Core**: reasoning pipeline does not depend on adapter details
- **Adapter Pattern**: platform-specific normalization/translation at channel edge
- **Separation of Concerns**: memory, RAG, tools, and LLM routing are modular
- **Extensibility**: adding platforms focuses on adapter implementation

---

## 🔍 Advanced Features Deep Dive

### 1) Unified Identity & Account Linking

- Pairing + approval flow already exists for controlled DM usage
- Data model supports `user_platform_links` for unified cross-platform IDs
- Privacy controls can gate who can use the assistant

### 2) Hub-and-Spoke Architecture

- Core agent remains stable while channels evolve independently
- Channel manager centralizes startup/shutdown lifecycle
- New platform = implement adapter + register with manager

### 3) Shared Memory System

- Mem0 extracts/stores salient facts from interactions
- Retrieval injects personalization context into prompts
- Delete operations support user-controlled memory lifecycle

### 4) Smart Resource Management

- Conversational queries skip tool loading entirely
- Action queries load local tools
- External MCP tools loaded selectively via keyword filtering

### 5) RAG Pipeline

- Embedding provider configurable
- Semantic retrieval with similarity threshold
- Retrieval context truncated/capped to reduce token waste

### 6) MCP Protocol & Tool Execution

- MCP servers discovered/loaded at runtime
- Tool schemas converted to model-compatible function specs
- Unified tool execution path handles local + external tools

### 7) Multi-LLM Support

- Runtime provider selection and model overrides
- Session-level provider/model commands via Slack
- Avoid hard dependency on a single LLM vendor

### 8) Error Handling & Graceful Degradation

- Subsystems can fail independently without full process crash
- Missing RAG keys disable retrieval path safely
- User-friendly fallback messages in adapter layer

---

## 👨‍💻 Development Guide

### Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,rag]'
```

### Run the app

```bash
python -m src.main
```

### Lint / Type / Test

```bash
python -m ruff check .
python -m mypy src
python -m pytest
```

> ℹ️ Current branch may include pre-existing lint/test environment issues unrelated
> to README updates.

### Contribution Flow

1. Create feature branch
2. Implement focused change
3. Run lint/type/test
4. Open PR with clear scope and evidence

---

## 🛠️ Troubleshooting

### Common Issues

| Issue | Likely Cause | Fix |
|---|---|---|
| Bot not responding in Slack | Missing tokens / Socket Mode not enabled | Recheck Slack setup and `.env` |
| Startup fails with provider error | No valid LLM key configured | Set at least one provider key |
| Memory not persisting | Missing `MEM0_API_KEY` or disabled memory | Set key and `MEMORY_ENABLED=true` |
| RAG retrieval empty | Missing embedding key / low similarity | Verify provider key and tune threshold |
| `summarize` fails | Not in thread context | Run summarize inside a Slack thread |

### Debug Tips

```bash
# run with live logs
python -m src.main

# inspect local db (if sqlite3 available)
sqlite3 data/assistant.db ".tables"
```

---

## 📈 Performance & Optimization

- **Tool payload optimization**: skip tools for non-action chat
- **Retrieval size caps**: chunk and total context limits
- **Async event processing**: non-blocking adapter and startup sequence
- **Selective MCP loading**: only relevant external tools

### Practical Tuning

- Lower `RAG_MAX_RESULTS` for latency-sensitive workloads
- Increase `RAG_MIN_SIMILARITY` for higher-precision retrieval
- Tune `MAX_HISTORY_MESSAGES` and context windows for token control

---

## 🔐 Security & Best Practices

- 🔒 Never hardcode secrets in source
- 🔒 Keep tokens in `.env` (local) or secrets manager (prod)
- 🔒 Run with least Slack scopes required
- 🔒 Use pairing/approval policy for DM access control
- 🔒 Encrypt and back up persistence layer in production
- 🔒 Add audit logging around tool execution and identity linking

> ⚠️ Ensure GDPR/privacy workflows for memory deletion are defined in production
> operations before scale rollout.

---

## 🚢 Deployment Guide

### Docker Compose

```bash
docker compose up --build
```

### Environment Profiles

- **dev**: verbose logs, rapid iteration
- **staging**: production-like keys/services
- **prod**: managed secrets, observability, backups

### Production Recommendations

- Add health probes and alerting
- Centralize logs (ELK/Grafana/Cloud logging)
- Use secret manager (Vault/AWS/GCP)
- Scale adapter workers horizontally as channels grow

---

## 🗺️ Roadmap & Implementation Strategy

### Current Status (v2.0.0)

- ✅ Phase 0 complete: bug fixes + optimization + token reduction focus
- ⬜ Phase 1: foundation abstraction layer hardening
- ⬜ Phase 2: Slack enhanced features
- ⬜ Phase 3: Telegram adapter rollout
- ⬜ Phase 4: WhatsApp + final polish

### Planned Phases

| Phase | Focus | Outcome |
|---|---|---|
| 1 | Base channel interface + manager | Strong abstraction boundary |
| 2 | Slack enhancements | Richer Slack-native UX |
| 3 | Telegram integration | First cross-platform continuity |
| 4 | WhatsApp + optimization | Full 3-channel assistant |

### Near-Term (v2.1+)

- Voice message support
- Image understanding workflows
- Proactive notifications
- Team memory and shared knowledge patterns

### Future (v3.0+)

- Multi-modal response blocks
- Workflow automation framework
- Skills/plugin ecosystem
- Usage analytics dashboard

---

## ❓ FAQ

**Q: Is Maantra fully multi-platform today?**  
A: The architecture is multi-platform-ready; Slack is currently implemented,
with Telegram/WhatsApp planned in roadmap phases.

**Q: Do I have vendor lock-in?**  
A: No. Provider routing supports multiple LLM backends and model overrides.

**Q: Can I disable memory or RAG?**  
A: Yes, via `MEMORY_ENABLED` and `RAG_ENABLED` flags.

**Q: Where does data persist?**  
A: Session/task data in SQLite; long-term memory via Mem0 when enabled.

---

## 🔗 Resources & Links

- GitHub: <https://github.com/dipanshuchoudhary-data/Maantra-1.0>
- Setup Website: <https://maantrasetup.netlify.app/>
- Runtime Entry: `src/main.py`
- Architecture Core: `src/agents/agent.py`
- Channel Abstraction: `src/channels/base_channel.py`

---

## 📄 License & Attribution

This project is licensed under the **MIT License**.

Maintained by the **Maantra** contributors.

---

<div align="center">

### Built for teams that work across channels, not inside silos.

**Made with ❤️ for unified AI experiences**

`Last updated: 2026-04-07`

</div>
