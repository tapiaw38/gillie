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

## Error Handling System

The application uses a structured error handling system following the same patterns as the Go backend (`auth-api-be`):

### Structure

```
src/core/platform/errors/
├── application_error.py    # ApplicationError base class & factory
├── exception_handler.py    # FastAPI exception handlers
└── mappings/
    ├── __init__.py        # Export all error mappings
    ├── common.py          # Common/generic errors
    ├── profile.py         # Profile domain errors
    ├── conversation.py    # Conversation domain errors
    └── faq.py             # FAQ domain errors
```

### Key Features

- **Unique error codes**: Each error has a unique identifier (e.g., `"profile:create:name-required"`)
- **Appropriate HTTP status codes**: 400, 401, 403, 404, 409, 500, etc.
- **Centralized error messages**: All error messages defined in mapping files
- **Automatic logging**: Errors log with structured context
- **JSON serialization**: Consistent error response format
- **Original error tracking**: Preserves technical error details for debugging
- **FastAPI integration**: Automatic exception handling via middleware

### Usage in Use Cases

```python
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileCreateQueryError,
    ProfileCreateNameRequiredError,
    ProfileGetNotFoundError
)
from pymongo.errors import PyMongoError

class CreateUseCase:
    def execute(self, profile: ProfileInput, user_id: str):
        # Validation
        if not profile.assistant_name or profile.assistant_name.strip() == "":
            raise NewApplicationError(ProfileCreateNameRequiredError)

        try:
            # Repository operations
            profile_id = self.context_factory.repositories.profile.create(new_profile)

            created_profile = self.context_factory.repositories.profile.find_by_id(profile_id)
            if not created_profile:
                raise NewApplicationError(ProfileCreateNotFoundAfterCreationError)

            return ProfileOutput.from_output(created_profile)

        except PyMongoError as e:
            raise NewApplicationError(ProfileCreateQueryError, e)
```

### Usage in Controllers

Controllers don't need try-catch blocks - ApplicationErrors automatically propagate to the exception handler:

```python
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile: ProfileInput,
    request: Request,
    service: Services = Depends(get_instance)
):
    """
    ApplicationErrors are automatically handled by exception handler middleware.
    """
    user_id = request.state.user.get("user_id")
    profile = await service.profile.create(profile, user_id)
    return profile
```

### Error Response Format

```json
{
  "code": "profile:create:name-required",
  "message": "assistant name is required"
}
```

### Adding New Errors

1. Define the error in the appropriate mapping file:

```python
# In src/core/platform/errors/mappings/profile.py
ProfileCustomError = ErrorDetails(
    internal_code="profile:custom:error-type",
    status_code=400,
    message="user-friendly error message"
)
```

2. Export it in `mappings/__init__.py`:

```python
from .profile import ProfileCustomError

__all__ = [
    # ... other exports
    "ProfileCustomError",
]
```

3. Use it in your code:

```python
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import ProfileCustomError

if validation_fails:
    raise NewApplicationError(ProfileCustomError)
```

### Error Code Naming Convention

Format: `{domain}:{action}:{error-type}`

Examples:

- `profile:create:name-required`
- `conversation:message:content-required`
- `faq:get:not-found`
- `common:database-query-error`

### Exception Handler Registration

Exception handlers are registered in `main.py` at startup:

```python
from src.core.platform.errors.exception_handler import register_exception_handlers

app = FastAPI(...)
register_exception_handlers(app)
```

This registers handlers for:

- `ApplicationError`: Returns structured JSON with appropriate status code
- `RequestValidationError`: Pydantic validation errors
- `PyMongoError`: Database errors
- `Exception`: Generic fallback (500 error)

### Best Practices

1. **Validate early**: Check input parameters before database operations
2. **Use appropriate error codes**: Match HTTP status codes to error types
   - 400: Validation errors, bad input
   - 401: Authentication required
   - 403: Forbidden (user lacks permission)
   - 404: Resource not found
   - 409: Conflict (duplicate resource)
   - 500: Server/database errors
3. **User-friendly messages**: `message` field for users, `original_message` for debugging
4. **Never expose sensitive data**: Keep error messages generic for security
5. **Let errors propagate**: Controllers don't need try-catch blocks
6. **Wrap database errors**: Convert PyMongoError to ApplicationError with appropriate context

## Important Notes

- The application requires Tesseract OCR to be installed (included in Docker image)
- PDF processing supports both text-based and scanned (OCR) documents
- MercadoLibre integration is initialized per-user with access tokens (not at startup)
- MongoDB migrations run automatically on startup via `execute_profile_migrations()`
- The API uses dependency injection through FastAPI's `dependency_overrides`
- All MongoDB clients are initialized with separate collections for conversations, profiles, and migrations
- Error handling is centralized through exception handlers - controllers should let ApplicationErrors propagate
