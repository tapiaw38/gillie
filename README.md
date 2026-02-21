# Gillie API

A single-user AI assistant API built with FastAPI. Supports conversational interfaces, document processing (PDF/OCR), RAG with vector search, TTS/STT, WhatsApp webhooks, and MercadoLibre integration. Managed entirely through a CLI tool.

---

## Requirements

- Python 3.10+
- Docker (only if using local MongoDB)
- Linux (systemd service management)

---

## Installation

```bash
git clone <repo-url>
cd gillie-api
./install.sh
```

`install.sh` will:

1. Verify Python 3.10+
2. Create a `.venv` virtual environment
3. Install all dependencies from `requirements.txt`
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
```

The API will be available at `http://localhost:8000`. Swagger UI at `http://localhost:8000/docs`.

---

## CLI Reference

### `./gillie init`

Interactive setup wizard. Configures the assistant profile, database, AI provider, and all optional services. Saves configuration to `~/.gillie/soul.json` and `~/.gillie/config.json`.

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

Start the API server. Reads `~/.gillie/soul.json` and `~/.gillie/config.json`.

```bash
./gillie start
./gillie start --host 0.0.0.0 --port 8080
./gillie start --reload          # dev mode with auto-reload
./gillie start --workers 4       # multiple worker processes
```

---

### `./gillie status`

Show current configuration summary, including both file paths.

```bash
./gillie status
```

Example output:

```sh
✨🐟 Gillie — Sofia
Soul:   /home/user/.gillie/soul.json
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

### `./gillie soul` — soul management

The soul is the assistant's identity: its `user_id` (UUID) and full profile. Stored in `~/.gillie/soul.json`.

```bash
./gillie soul show       # display user_id + full profile
./gillie soul edit       # edit profile fields + optional ID regeneration
./gillie soul reset-id   # regenerate the user_id with confirmation
```

`soul edit` prompts for all profile fields and offers to regenerate the User ID at the end. `soul reset-id` is a focused command just for replacing the UUID.

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
├── general.skill.md     ← updated automatically by memory extraction
└── *.skill.md           ← any additional skills
```

**Default `memory.md`:**

```markdown
# Memoria del Asistente

Árbol de conocimiento del asistente. Cada sección puede referenciar skills específicas.

## Preguntas Frecuentes

ver faqs.skill.md

## Conocimiento General

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

Run memory extraction: summarize recent unextracted conversations and append the result to `general.skill.md`.

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

Configuration is split into two files under `~/.gillie/`, both created by `./gillie init`:

| File                    | Contents                                           |
| ----------------------- | -------------------------------------------------- |
| `~/.gillie/soul.json`   | Assistant identity: `user_id` (UUID) and `profile` |
| `~/.gillie/config.json` | Technical settings: server, services, logging      |

They can be edited manually or interactively via `./gillie soul edit`, `./gillie profile edit`, and `./gillie services edit`.

### `~/.gillie/soul.json`

```json
{
  "user_id": "a1b2c3d4-...",
  "profile": {
    "assistant_name": "Sofia",
    "business_name": "My Store",
    "business_context": "...",
    "functions": "...",
    "role": "seller"
  }
}
```

### `~/.gillie/config.json`

```json
{
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

---

## API Endpoints

All endpoints are prefixed according to the domain. Authentication is handled automatically by the single-user middleware — no token required.

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
| GET    | `/api/v1/memory/general`    | Return raw `general.skill.md`                  |
| GET    | `/api/v1/memory/faqs`       | List all FAQs                                  |
| POST   | `/api/v1/memory/faqs`       | Add a FAQ                                      |
| PUT    | `/api/v1/memory/faqs/{id}`  | Update a FAQ                                   |
| DELETE | `/api/v1/memory/faqs/{id}`  | Delete a FAQ                                   |
| GET    | `/api/v1/memory/skills`     | List all `.skill.md` files                     |
| GET    | `/api/v1/memory/skills/{n}` | Return content of a specific skill             |
| POST   | `/api/v1/memory/extract`    | Run memory extraction from conversations       |

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

### Docker (API + MongoDB together)

```bash
make build
make run
make stop
```

---

## PDF Processing

The API includes advanced PDF processing with OCR support:

- Automatic detection of text-based vs scanned PDFs
- Tesseract OCR for scanned documents (Spanish + English)
- Image extraction and relevance scoring
- RAG integration with FAISS or Qdrant vector stores

Requires `tesseract` installed on the system.
