# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Assistant IA API is a Python FastAPI-based intelligent assistant service with advanced AI capabilities including NLP, PDF processing with OCR, RAG (Retrieval-Augmented Generation), and multi-modal document processing. The API provides conversational interfaces, profile management, and integrations with external services like OpenAI and MercadoLibre.

## Development Commands

### Running the Application

```bash
# Build Docker containers
make build

# Start services (API + MongoDB)
make run

# Stop services
make stop
```

The API runs on `http://localhost:8000` and automatically redirects to `/docs` (Swagger UI).

### Testing

```bash
# Run all tests inside Docker container
make test

# Run tests with verbose output
make test-v

# Run tests locally (requires venv activation)
pytest
pytest -v  # verbose mode
```

### Local Development (without Docker)

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run API directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Architecture

### Hexagonal Architecture (Ports & Adapters)

The codebase follows hexagonal/clean architecture principles with clear separation of concerns:

```
src/
├── core/                    # Business logic layer (hexagon core)
│   ├── domain/             # Domain models (Profile, Conversation, Message)
│   ├── use_cases/          # Application use cases
│   ├── services/           # Core services
│   └── platform/           # Infrastructure abstractions
├── adapters/               # External interfaces
│   ├── web/               # HTTP controllers, middlewares, integrations
│   ├── datasources/       # Repository implementations (MongoDB)
│   ├── services/          # Service adapters
│   └── storeservice/      # Storage service (S3)
├── routes/                # Route management
└── schemas/               # API request/response schemas
```

### Key Architectural Components

#### Context Factory Pattern
The application uses a factory pattern for dependency injection via `src/core/platform/appcontext/appcontext.py`:
- `Context`: Holds repositories, integrations, store_service, config_service
- `Factory`: Creates Context instances with injected dependencies
- All use cases receive `Factory` and instantiate `Context` when needed

#### Initialization Flow (main.py)
1. Initialize configuration service (`init_config()`)
2. Create MongoDB clients (migrations, conversations, profiles)
3. Run database migrations
4. Initialize S3 session and store service
5. Create datasources → repositories
6. Create integrations (OpenAI, TTS, STT, MercadoLibre)
7. Create context factory
8. Create use cases from factory
9. Setup routes with services and middleware

#### Use Cases Organization
Use cases are grouped by domain (`src/core/use_cases/use_cases.py`):
- **Profile**: create, find, update, API key management, file operations, integrations
- **Conversation**: create, find, add messages, delete messages

Each use case receives a `Factory` and creates a `Context` for accessing dependencies.

#### Repositories
Located in `src/adapters/datasources/repositories/`:
- **profile**: User profile CRUD, API keys, files, integrations
- **conversation**: Conversation CRUD, message management
- **inmemory**: In-memory repositories for testing

### Platform Components

#### File Processors (`src/core/platform/fileprocessor/`)
- **pdf_processor.py**: Advanced PDF processing with OCR (Tesseract), text extraction, image analysis
- **langchain_processor.py**: LangChain-based document processing
- **rag_processor.py**: RAG implementation with FAISS vector stores
- **hybrid_processor.py**: Hybrid search combining vector and keyword search
- **xlsx_processor.py**: Excel file processing

#### Function Executors (`src/core/platform/functions/`)
- **function_executor.py**: Basic function execution
- **workflow_executor.py**: Multi-step workflow execution
- **smart_function_executor.py**: Intelligent function routing and execution
- **http_functions.py**: HTTP-based function calls

#### Integrations (`src/adapters/web/integrations/`)
- **openapi**: OpenAI API integration
- **tts**: Text-to-Speech services
- **stt**: Speech-to-Text services
- **mercadolibre**: MercadoLibre marketplace integration (initialized per-user with credentials)

### Domain Models (`src/core/domain/model.py`)

Core entities using Pydantic:
- **Profile**: User profile with assistant configuration, business context, API keys, files, integrations
- **Conversation**: Conversation with title, messages, and associated profile
- **Message**: Individual messages with content, audio, sender (user/assistant)
- **ApiKey**: API key management with limits and activation status
- **File**: File metadata (name, URL, creation date)
- **Integration**: Third-party service configurations

### Configuration

Configuration is managed through `src/core/platform/config/service.py`:
- Environment variables loaded via `.env` file
- NoSQL configurations (MongoDB URIs, databases, collections)
- S3/object storage configuration
- Integration credentials (OpenAI API keys, etc.)

### Controllers (`src/adapters/web/controllers/`)
- **conversation**: Conversation management endpoints
- **profile**: Profile management endpoints
- **nosql**: Database operations endpoints
- **whatsapp**: WhatsApp integration endpoints

### Middleware

- **AuthorizationMiddleware** (`src/adapters/web/middlewares/authorization.py`): API key validation and authorization

## Testing

Tests are located in `tests/repositories/`:
- Use `pytest` as the test framework
- Use `mongomock` for MongoDB mocking
- Example: `test_conversation.py` demonstrates repository testing patterns

## Dependencies

Key technologies:
- **FastAPI**: Web framework
- **MongoDB**: NoSQL database (via pymongo)
- **OpenAI**: LLM integration
- **LangChain**: Document processing and RAG
- **FAISS**: Vector similarity search
- **Tesseract OCR**: Image text extraction (Spanish/English)
- **PyMuPDF, PyPDF2**: PDF processing
- **Boto3**: AWS S3 integration
- **Pydantic**: Data validation
- **pytest**: Testing framework

## Important Notes

- The application requires Tesseract OCR to be installed (included in Docker image)
- PDF processing supports both text-based and scanned (OCR) documents
- MercadoLibre integration is initialized per-user with access tokens (not at startup)
- MongoDB migrations run automatically on startup via `execute_profile_migrations()`
- The API uses dependency injection through FastAPI's `dependency_overrides`
- All MongoDB clients are initialized with separate collections for conversations, profiles, and migrations
