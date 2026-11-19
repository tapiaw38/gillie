# Gillie

Single-user AI assistant. Gillie combines FastAPI backend, terminal agent, Electron dashboard, document/RAG pipeline, voice, integrations and optional avatar companion. Setup and local operation run through `./gillie`.

## Highlights

- **Agent loop** — LangGraph tool calling with streaming tool progress, safe approval prompts and plan mode.
- **Local-first workflow** — terminal agent understands workspace files, `@` references and approved shell/file actions.
- **Knowledge** — Markdown skill memory, FAQs, episodic brain, document ingestion and FAISS/Qdrant retrieval.
- **Interfaces** — CLI, Electron dashboard, HTTP API, voice mode and WhatsApp-compatible integrations.
- **Companion avatar** — optional VRM Electron overlay controlled through MCP.

---

## Requirements

- Python 3.10+
- Node.js 18+ for dashboard or avatar
- Docker (only if using local MongoDB)
- Linux (systemd service management)

---

## Installation

```bash
git clone <repo-url>
cd gillie
./install.sh
```

`install.sh` will:

1. Verify Python 3.10+
2. Create a `.venv` virtual environment
3. Install Python dependencies from `requirements.txt`
4. Make the `./gillie` CLI executable

Optional system dependencies (installed separately):

- `tesseract` — required for PDF OCR processing
- `ffmpeg` — required for TTS/STT audio processing

---

## Quick Start

```bash
# 1. Run the setup wizard
./gillie init

# 2. Start MongoDB (if using Docker local mode)
./gillie db start

# 3. Start the API server
./gillie start

# 4. Open terminal agent in a workspace
./gillie agent
```

API: `http://localhost:8000`. Swagger: `http://localhost:8000/docs`.

For dashboard:

```bash
./gillie ui start
```

For voice conversation:

```bash
./gillie agent listen
```

---

## CLI Reference

Run `./gillie --help` or `./gillie <command> --help` for current flags.

| Command | Purpose |
| --- | --- |
| `init`, `status`, `start`, `install`, `reset` | Setup and API lifecycle |
| `agent`, `agent listen`, `agent workspace`, `agent list` | Terminal chat, voice, workspace and conversations |
| `ui` | Electron dashboard: `start`, `dev`, `build`, `stop`, `install` |
| `db`, `qdrant` | Local Docker MongoDB/Qdrant lifecycle and maintenance |
| `provider`, `services`, `profile`, `config` | Assistant/provider configuration |
| `memory`, `brain`, `contact` | Skills, FAQs, episodic memory and contacts |
| `avatar` | VRM companion lifecycle |
| `service`, `tunnel`, `expose` | systemd, SSH tunnel and nginx operations |

### `./gillie init`

Interactive setup wizard. Configures the assistant profile, database, AI provider, and all optional services. Saves configuration to `~/.gillie/config.json`.

```bash
./gillie init           # run wizard
./gillie init --force   # overwrite existing config
```

**What the wizard covers:**

- Assistant name and business profile
- MongoDB setup: Docker local or external URI
- AI provider: API key, base URL, model, temperature, max tokens
- LangChain / RAG (FAISS or Qdrant vector store)
- Embeddings provider (HuggingFace or OpenAI)
- S3 file storage
- TTS / STT (audio)
- WhatsApp webhook
- MercadoLibre integration
- LangSmith observability
- Server host, port, log level

---

### `./gillie start`

Start the API server. Reads `~/.gillie/config.json`.

```bash
./gillie start
./gillie start --host 0.0.0.0 --port 8080
./gillie start --reload          # dev mode with auto-reload
./gillie start --workers 4       # multiple worker processes
```

---

### `./gillie status`

Show current configuration summary.

```bash
./gillie status
```

Example output:

```sh
✨🐙 Gillie — Sofia
Config: /home/user/.gillie/config.json

 User ID    a1b2c3d4-...
 Assistant  Sofia
 Business   My Store
 Model      deepseek-chat
 MongoDB    mongodb://localhost:27017
 Server     0.0.0.0:8000
```

---

### `./gillie db` — MongoDB management

Manages the local MongoDB container via Docker Compose (`docker-compose.mongo.yml`). Automatically detects Docker Compose v2 (`docker compose`) or v1 (`docker-compose`).

> Commands are no-ops if MongoDB is configured as **external**.

| Command                   | Description                        |
| ------------------------- | ---------------------------------- |
| `./gillie db start`       | Start MongoDB container (detached) |
| `./gillie db stop`        | Stop MongoDB container             |
| `./gillie db restart`     | Restart MongoDB container          |
| `./gillie db status`      | Show container status and URI      |
| `./gillie db logs`        | Show recent logs (last 50 lines)   |
| `./gillie db logs -f`     | Follow log output                  |
| `./gillie db logs -n 100` | Show last N lines                  |

---

### `./gillie service` — systemd service management

Manages the API as a systemd service. By default, installs as a **user service** (`~/.config/systemd/user/`), requiring no sudo. Use `--system` to manage a system-wide service (`/etc/systemd/system/`).

| Command                             | Description                               |
| ----------------------------------- | ----------------------------------------- |
| `./gillie service install`          | Create unit file and enable service       |
| `./gillie service install --system` | Install as system service (requires sudo) |
| `./gillie service uninstall`        | Disable and remove unit file              |
| `./gillie service start`            | Start the service                         |
| `./gillie service stop`             | Stop the service                          |
| `./gillie service restart`          | Restart the service                       |
| `./gillie service status`           | Show service status                       |
| `./gillie service logs`             | Show recent logs (last 50 lines)          |
| `./gillie service logs -f`          | Follow log output                         |
| `./gillie service logs -n 100`      | Show last N lines                         |

**Run as daemon example:**

```bash
./gillie service install
./gillie service start
./gillie service status
./gillie service logs -f
```

---

### `./gillie config` — identity and profile management

This command manages the assistant identity: its `user_id` (UUID) and profile fields. Stored in `~/.gillie/config.json`.

```bash
./gillie config show       # display user_id + full profile
./gillie config edit       # edit profile fields + optional ID regeneration
./gillie config reset-id   # regenerate the user_id with confirmation
```

`config edit` prompts for all profile fields and offers to regenerate the User ID at the end. `config reset-id` is a focused command just for replacing the UUID.

---

### `./gillie profile` — profile management

```bash
./gillie profile show   # display current profile
./gillie profile edit   # interactively edit profile fields
```

---

### `./gillie services` — services configuration

```bash
./gillie services show   # display all service configurations
./gillie services edit   # interactively edit a service
```

---

### `./gillie memory` — knowledge tree management

The memory system gives the assistant persistent knowledge. All files live in `~/.gillie/memory/`.

#### Architecture: `memory.md` as root

`memory.md` is the root of the knowledge tree. It is auto-created on first startup and references other skill files using the `ver X.skill.md` directive. At request time, the API resolves those references by inlining the content of each skill file before sending context to the LLM.

```sh
~/.gillie/memory/
├── memory.md            ← root (auto-created, always loaded)
├── faqs.skill.md        ← referenced from memory.md
├── general.skill.md     ← only always-on core facts
└── *.skill.md           ← any additional skills
```

**Default `memory.md`:**

```markdown
# Memoria del Asistente

Árbol de conocimiento del asistente. Cada sección puede referenciar skills específicas.

## Preguntas Frecuentes

ver faqs.skill.md

## Conocimiento General

Solo hechos nucleares que deben estar siempre en contexto.
No usar para memoria consolidada de conversaciones; eso vive en el soul store.

ver general.skill.md
```

Each `ver X.skill.md` line is replaced with the full content of the referenced file when building the LLM context.

#### `./gillie memory show`

Display the raw `memory.md` content and list all skills it references, with their disk status.

```bash
./gillie memory show
```

#### `./gillie memory edit`

Open `memory.md` in `$EDITOR` (falls back to `nano`). Changes are saved back to the API on exit.

```bash
./gillie memory edit
```

#### `./gillie memory extract`

Run the legacy conversation summarization job. It summarizes recent unextracted conversations and stores those summaries on the conversation records only.

```bash
./gillie memory extract
```

#### `./gillie memory faqs` — FAQ management

FAQs are stored as structured blocks inside `faqs.skill.md` and referenced automatically from `memory.md`.

```bash
./gillie memory faqs list            # list all FAQs
./gillie memory faqs add             # add a FAQ interactively
./gillie memory faqs delete <id>     # delete a FAQ by ID
```

#### `./gillie memory skills` — browse skill files

```bash
./gillie memory skills list          # list all *.skill.md files
./gillie memory skills show <name>   # display content of a skill
```

---

## Configuration

Configuration is stored in a single file under `~/.gillie/`, created by `./gillie init`:

| File                    | Contents                                                            |
| ----------------------- | ------------------------------------------------------------------- |
| `~/.gillie/config.json` | Assistant identity, profile, server settings, services, and logging |

They can be edited manually or interactively via `./gillie config edit`, `./gillie profile edit`, and `./gillie services edit`.

### `~/.gillie/config.json`

```json
{
  "user_id": "a1b2c3d4-...",
  "profile": {
    "assistant_name": "Sofia",
    "business_name": "My Store",
    "functions": "...",
    "response_language": "en"
  },
  "server": {
    "host": "0.0.0.0",
    "port": 8000,
    "mode": "release"
  },
  "services": {
    "mongodb": {
      "uri": "mongodb://localhost:27017",
      "database": "gillie-db",
      "mode": "docker"
    },
    "openai": {
      "api_key": "sk-...",
      "base_url": "https://api.deepseek.com",
      "model": "deepseek-chat",
      "temperature": 0.7,
      "max_tokens": 2000
    },
    "langchain": { "enabled": false },
    "qdrant": { "enabled": false },
    "s3": { "enabled": false },
    "tts": { "enabled": false },
    "stt": { "enabled": false },
    "whatsapp": { "enabled": false, "verify_token": "" },
    "mercadolibre": { "enabled": false },
    "langsmith": { "enabled": false }
  },
  "logging": {
    "environment": "development",
    "log_level": "INFO"
  }
}
```

### MongoDB modes

| Mode       | Description                                                  |
| ---------- | ------------------------------------------------------------ |
| `docker`   | Local MongoDB managed via `./gillie db start/stop`           |
| `external` | Remote or self-hosted MongoDB URI — `db` commands are no-ops |

---

## Architecture

The project follows **hexagonal architecture** (ports & adapters):

```sh
src/
├── core/
│   ├── domain/          # Profile, Conversation, Message models
│   ├── use_cases/       # Application business logic
│   ├── services/        # Core services
│   └── platform/        # Config, errors, file processors, functions
├── adapters/
│   ├── web/             # HTTP controllers, middlewares, integrations
│   ├── datasources/     # MongoDB repository implementations
│   └── storeservice/    # S3 storage
├── routes/              # Route registration
└── schemas/             # API request/response schemas
```

Key patterns:

- **Context Factory** — dependency injection for use cases via `src/core/platform/appcontext/`
- **Single-user middleware** — injects the configured `user_id` into every request automatically
- **Structured errors** — all errors have a unique code (e.g. `profile:create:name-required`) and appropriate HTTP status

### Agent execution

When LangChain service is enabled, Gillie runs tool-capable conversations through a LangGraph state machine:

```text
system + history + user input
            │
          model ── no tool call ──> final response
            │
         one tool
            │
      validation / approval / execution
            │
      ToolMessage observation
            └──────────────────────> model
```

Tools run one at a time. This prevents a paused approval from replaying completed side effects. Streaming clients receive text plus structured events for tool start/result, shell output, local files and approval requests. Plan mode reports intended mutations without applying them.

Use `./gillie agent` for terminal approval modes and `./gillie ui start` for dashboard approval dialogs. Unattended callers run without interactive approvals.

### Workspace agent

`./gillie agent` sends current workspace in `X-Gillie-Workspace`. Assistant can inspect files, use `@path`, `@@glob/**` and `@https://…` references, stream shell output and request approval for risky operations. Set default workspace:

```bash
./gillie agent workspace /path/to/project
```

---

## Integrations

Enable integrations in `./gillie init` or `./gillie services edit`. Credentials stay in local configuration or environment variables; do not commit them.

| Integration | Primary capability | Setup notes |
| --- | --- | --- |
| Google Calendar | Read and manage events | OAuth client and redirect URI |
| Google Drive | Browse, ingest and search Drive files | OAuth client and redirect URI |
| Gmail | Read and manage mailbox data | OAuth client and redirect URI |
| WhatsApp | Webhook messaging and device management | Webhook verification token/device setup |
| Slack, Telegram | Messaging channels | Channel-specific credentials/webhook setup |
| Notion | Workspace content integration | Notion integration credentials |
| Jira, ClickUp, Teams | Work-management integrations | Provider credentials/configuration |
| MercadoLibre | Marketplace integration | MercadoLibre credentials |
| S3/local storage | Uploaded-file storage | Select local storage or configure AWS S3 |

OAuth callback defaults are documented in [`.env.example`](.env.example). Register the exact public callback URL when exposing Gillie behind a domain.

## Configuration and secrets

`~/.gillie/config.json` is CLI-managed single-user configuration. `.env` is environment-based server configuration. Use one source of truth for each deployment; do not put production secrets in Git.

**Priority:** if `~/.gillie/config.json` exists, the API loads it and `.env` is not used for server settings. Without it, the API falls back to `.env` (`load_dotenv`). Never commit `config.json`, `.env` or any API key.

Important environment groups:

| Group | Examples |
| --- | --- |
| Server | `APP_HOST`, `APP_PORT`, `APP_JWT_SECRET`, `LOG_LEVEL` |
| Provider | `AI_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` |
| Data | `DATABASE_URI`, `DB_NAME`, `QDRANT_HOST`, `QDRANT_API_KEY` |
| Agent/RAG | `LANGCHAIN_SERVICE_ENABLED`, `LANGCHAIN_VECTOR_STORE`, `EMBEDDING_PROVIDER` |
| Observability | `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGSMITH_TRACING_ENABLED` |
| Avatar | `AVATAR_MCP_URL`, `AVATAR_MCP_TIMEOUT` |

Copy [`.env.example`](.env.example) for an environment-driven deployment. Rotate a leaked provider, OAuth, database or AWS credential immediately.

## Knowledge, RAG and Brain

Gillie has three different knowledge mechanisms:

| Feature | Purpose | CLI |
| --- | --- | --- |
| Memory skills and FAQs | Curated, always-available assistant knowledge | `gillie memory` |
| Document RAG | Retrieved chunks from uploaded/ingested files | `gillie qdrant reindex` when needed |
| Brain | Episodic memories plus consolidated soul knowledge | `gillie brain` |

RAG flow: ingestion (file upload or Drive) → text extraction (PDF/OCR, DOCX, XLSX) → chunking → embeddings → vector store (Qdrant or FAISS) → retrieval at chat time.

Brain requires Qdrant. Useful commands:

```bash
./gillie brain status
./gillie brain stats
./gillie brain search "customer preference"
./gillie brain consolidate
./gillie brain prune
```

`brain clear`, `db reset` and `qdrant reset` remove data. Review their confirmation prompts and back up data first.

## Dashboard

`./gillie ui start` launches the Electron dashboard from `ui/` (builds first if sources changed; `--rebuild` forces it). Requires Node.js; package manager is detected from the lockfile (`yarn.lock` → yarn, `pnpm-lock.yaml` → pnpm, else npm). Use it for chat, approval dialogs and managing assistant configuration against the running API.

## Security and operations

- **Auth:** requests from loopback skip auth when `AUTH_TRUST_LOCALHOST=true` (default). Remote requests must send an active API key in the `X-API-Key` header. Set `AUTH_TRUST_LOCALHOST=false` behind a reverse proxy, otherwise proxied traffic looks local.
- Keep API on loopback unless deliberate remote access is needed.
- Agent tools are confined to the active workspace (`X-Gillie-Workspace`); risky tools need approval.
- Back up `~/.gillie/` too: it holds identity, services and credentials.
- Use `./gillie expose install` only with a controlled domain, TLS and secure secrets.
- Use `./gillie tunnel` for SSH-tunneled remote access instead of exposing MongoDB or Qdrant directly.
- Agent tools may read workspace files, access network services or request mutations. Review approval prompts; use plan mode for a dry-run workflow.
- Back up MongoDB before `db reset`, migration work or production upgrades. Back up Qdrant collections before reset/reindex operations. Gillie has no backup command; use the database tools directly:

```bash
# Docker local mode; adjust container name (see `docker ps`) and URI
docker exec <mongo-container> mongodump --archive > gillie-mongo.archive
docker exec -i <mongo-container> mongorestore --archive --drop < gillie-mongo.archive
# Qdrant: stop it, then copy its storage volume
```

- Run `./gillie service install` for a user-level systemd service; use `./gillie service logs -f` to diagnose it.

### Health and troubleshooting

| Symptom | Check |
| --- | --- |
| API unavailable | `./gillie status`, `./gillie start`, `./gillie service status` |
| MongoDB unavailable | `./gillie db status`, then `./gillie db start` for Docker mode |
| Qdrant unavailable | `./gillie qdrant status`, then `./gillie qdrant start` |
| Provider errors | `./gillie provider status`; verify key, base URL and model |
| Dashboard will not open | `./gillie ui install`, then `./gillie ui start --rebuild` |
| OCR/audio unavailable | Install system dependencies: `./gillie install --system` (Tesseract, audio libs) |
| Browser tools fail | `playwright install chromium` inside the venv |
| Auth 401 from a remote client | Send `X-API-Key`; check `AUTH_TRUST_LOCALHOST` |
| Logs | `./gillie service logs -f`, `./gillie db logs`, `./gillie qdrant logs` |
| Avatar bridge unavailable | Start avatar and check `http://127.0.0.1:47850/health` |

## Testing and UI development

```bash
# Backend
source .venv/bin/activate
pytest
pytest tests/platform -q

# Dashboard
cd ui
npm install
npm run build
```

Lint the dashboard with `npm run lint` (eslint, applies fixes). There is no Python linter or type checker configured. Use `./gillie ui dev` for dashboard development. Run `./gillie --help` after CLI changes and keep this README command matrix synchronized with `cli/main.py`.

### Limitations

- Linux is required for systemd lifecycle management and full native avatar/audio behavior (`gillie service`, `expose`).
- Docker is optional and used for local MongoDB/Qdrant services.
- External providers, OAuth channels and cloud storage require their own credentials and network access.

---

## Avatar — companion app

`avatar/` is a realtime character presence for voice sessions: a transparent, always-on-top
Electron overlay that renders a VRM character, lip-syncs it to whatever the voice app is
playing, and exposes an MCP server so the assistant can drive its own body. Built with
Vue 3, TypeScript, three.js and electron-vite, following the same layout as `ui/`.

```bash
./gillie avatar start              # install, build if stale, and launch
./gillie avatar start --rebuild    # force a renderer rebuild first
./gillie avatar stop
./gillie agent listen -a           # voice mode with the avatar on screen
```

Inside `avatar/`, the usual npm scripts are available: `dev`, `build`, `test`,
`type-check`, `lint`, `assets:check` (verifies the character asset contract), and
`dist:linux` / `dist:windows` / `dist:mac` for packaging.

### Layout

```sh
avatar/
├── electron/
│   ├── main/        # Window, tray, avatar:// protocol, HTTP bridge, MCP server,
│   │                # and the audio listeners (PipeWire on Linux, native helper elsewhere)
│   └── preload/     # Sandboxed CommonJS preload exposing window.avatarBridge
├── src/
│   ├── avatar/      # Framework-free three.js layer: VRM loading, animation mixer,
│   │                # procedural motion, lip sync, blink, camera framing, render stage
│   ├── components/  # AvatarStage.vue, the canvas the stage draws into
│   ├── composables/ # useAvatarBridge, turning bridge events into body animation
│   └── types/       # Shared renderer-side bridge types
├── public/assets/   # model.vrm plus the .vrma animation clips
├── native/          # C++/Objective-C audio listener helpers
└── scripts/         # Asset contract, native build, packaging, release helpers
```

### Integration surface

The main process listens on `127.0.0.1:47850` (override with `AVATAR_BRIDGE_PORT`):

| Method | Path      | Description                                            |
| ------ | --------- | ------------------------------------------------------ |
| POST   | `/events` | Accepts `state`, `audio-level`, and `animation` events |
| POST   | `/mcp`    | Streamable HTTP MCP endpoint (see tools below)         |
| GET    | `/health` | Liveness plus the last voice state                     |

The MCP endpoint exposes `play_animation`, `control_window`, `get_status`,
`set_voice_state` and `set_audio_level`. The API reaches it through
`AVATAR_MCP_URL` (default `http://127.0.0.1:47850/mcp`, timeout `AVATAR_MCP_TIMEOUT`),
which is what backs the assistant's `avatar_play_animation`, `avatar_control_window`
and `avatar_get_status` tools.

The `avatar://` URL scheme is also handled (`avatar://show`,
`avatar://speaking?level=0.4`, `avatar://dance`, and so on). Set `AVATAR_DEBUG=1` for
verbose listener logging and `AVATAR_TARGET_PROCESS_PATTERN` to change which
application's audio is followed.

Environment lighting is generated at runtime with three.js `RoomEnvironment`, so no HDRI
file is fetched or shipped.

### Character assets

`avatar/public/assets/model.vrm` and the clips under `avatar/public/assets/animations/`
are local media and are ignored by Git. See `avatar/ASSET_LICENSES.md` before
distributing any build that contains them.

---

## API Endpoints

In default single-user local mode, middleware resolves configured user identity automatically. Treat a remotely exposed API as a security boundary: use TLS, restrict network access and configure authentication appropriate to deployment. Swagger is the authoritative complete endpoint reference.

| Domain        | Base path        |
| ------------- | ---------------- |
| Profile       | `/profile`       |
| Conversations | `/conversation`  |
| WhatsApp      | `/whatsapp`      |
| Memory        | `/api/v1/memory` |

### Memory endpoints

| Method | Path                        | Description                                    |
| ------ | --------------------------- | ---------------------------------------------- |
| GET    | `/api/v1/memory`            | Return `memory.md` with all skill refs inlined |
| GET    | `/api/v1/memory/root`       | Return raw `memory.md`                         |
| PUT    | `/api/v1/memory/root`       | Overwrite `memory.md` (`{"content": "..."}`)   |
| GET    | `/api/v1/memory/general`    | Return raw `general.skill.md` core facts       |
| GET    | `/api/v1/memory/faqs`       | List all FAQs                                  |
| POST   | `/api/v1/memory/faqs`       | Add a FAQ                                      |
| PUT    | `/api/v1/memory/faqs/{id}`  | Update a FAQ                                   |
| DELETE | `/api/v1/memory/faqs/{id}`  | Delete a FAQ                                   |
| GET    | `/api/v1/memory/skills`     | List all `.skill.md` files                     |
| GET    | `/api/v1/memory/skills/{n}` | Return content of a specific skill             |
| POST   | `/api/v1/memory/extract`    | Run legacy conversation summarization          |

Full interactive documentation: `http://localhost:8000/docs`

---

## Development

### Run locally without Docker

```bash
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Run tests

```bash
source .venv/bin/activate
pytest
pytest -v
```

### Docker

The supported local database workflow is managed by CLI:

```bash
./gillie db start
./gillie start
```

`Dockerfile` builds API image for custom deployments. MongoDB compose definition lives in `docker-compose.mongo.yml`; Qdrant definition lives in `docker-compose.qdrant.yml`. `make` targets are legacy helpers and require a matching deployment compose file.

---

## PDF Processing

The API includes advanced PDF processing with OCR support:

- Automatic detection of text-based vs scanned PDFs
- Tesseract OCR for scanned documents (Spanish + English)
- Image extraction and relevance scoring
- RAG integration with FAISS or Qdrant vector stores

Requires `tesseract` installed on the system.

---

## License

MIT, Copyright (c) 2026 tapiaw38. See [`LICENSE`](LICENSE).

The MIT license covers the source of Gillie and its companion applications (`ui/`,
`avatar/`). It does **not** cover third-party media shipped alongside them: the VRM model
and `.vrma` animation clips under `avatar/public/assets/` are local media, ignored by Git,
and governed by their own terms. Read [`avatar/ASSET_LICENSES.md`](avatar/ASSET_LICENSES.md)
before publishing a repository or a release that contains them — it also documents how to
replace the assets and how the release gate (`npm run assets:release`, inside `avatar/`)
enforces the license metadata.
