from src.core.platform.config.service import ConfigurationService
from openai import AsyncOpenAI
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import os
from src.core.domain import Profile
from src.core.platform.logging import get_logger, log_function_call, log_execution_time
import asyncio
import aiohttp
import tempfile
import json
import time
from pathlib import Path

if TYPE_CHECKING:
    from src.core.platform.fileprocessor.pdf_processor import FileImageProcessor
    from src.core.platform.fileprocessor.xlsx_processor import ExcelImageProcessor
    from src.core.platform.fileprocessor.processor import ImageSearchResult
    from src.core.platform.fileprocessor.hybrid_processor import HybridDocumentProcessor
    from src.core.platform.fileprocessor.rag_processor import RAGDocumentProcessor


class OpenAIIntegration:
    def __init__(self, config_service: ConfigurationService):
        self.logger = get_logger(__name__)
        config = config_service.openai_config

        self.api_key = config.api_key
        self.base_url = config.base_url
        self.model = config.model
        self.role = config.role
        self.auth_type = getattr(config, "auth_type", "api_key")

        self.client = self._build_client()
        self._extra_headers: Dict[str, str] = {}

        self._config_service = config_service
        self._image_processor = None
        self._excel_processor = None
        self._hybrid_processor = None
        self._rag_processor = None
        self._processed_documents = {}

        self.langchain_service = None
        self.skill_manager = None
        self.store_service = None
        self.job_usecases = None

        langchain_config = config_service.langchain_config
        if langchain_config.service_enabled:
            try:
                from src.core.platform.ai import LangChainService

                self.langchain_service = LangChainService(
                    config_service=config_service,
                    openai_integration=self,
                    max_concurrent_requests=langchain_config.max_concurrent_requests,
                    enable_langsmith=config_service.langsmith_config.tracing_enabled,
                )
                self.logger.info(f"LangChain service enabled with LangSmith={config_service.langsmith_config.tracing_enabled}")
            except Exception as e:
                self.logger.error(f"Failed to initialize LangChain service: {e}")
                self.langchain_service = None

        self.logger.info(f"OpenAI integration initialized with model: {self.model}, auth_type: {self.auth_type}")

    @property
    def image_processor(self) -> "FileImageProcessor":
        if self._image_processor is None:
            from src.core.platform.fileprocessor.pdf_processor import FileImageProcessor
            self._image_processor = FileImageProcessor(self._config_service)
        return self._image_processor

    @property
    def excel_processor(self) -> "ExcelImageProcessor":
        if self._excel_processor is None:
            from src.core.platform.fileprocessor.xlsx_processor import ExcelImageProcessor
            self._excel_processor = ExcelImageProcessor(self._config_service)
        return self._excel_processor

    @property
    def hybrid_processor(self) -> "HybridDocumentProcessor":
        if self._hybrid_processor is None:
            from src.core.platform.fileprocessor.hybrid_processor import HybridDocumentProcessor
            self._hybrid_processor = HybridDocumentProcessor(self._config_service)
        return self._hybrid_processor

    @property
    def rag_processor(self) -> "RAGDocumentProcessor":
        if self._rag_processor is None:
            from src.core.platform.fileprocessor.rag_processor import RAGDocumentProcessor
            self._rag_processor = RAGDocumentProcessor(self._config_service)
        return self._rag_processor

    def _build_client(self) -> AsyncOpenAI:
        """Construct an AsyncOpenAI client with the current credentials."""
        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=45.0,
            max_retries=3,
        )

    def reload_provider(self, base_url: str, model: str, api_key: str, auth_type: str) -> None:
        """Hot-reload provider without restarting. Updates client + LangChain LLM."""
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.auth_type = auth_type
        self.client = self._build_client()
        if self.langchain_service is not None:
            self.langchain_service.reload_llm(model=model, base_url=base_url, api_key=api_key, auth_type=auth_type)
        self.logger.info(f"Provider reloaded: model={model}, base_url={base_url}")

    def set_skill_manager(self, skill_manager) -> None:
        """Inject SkillManager after construction (avoids circular init order)."""
        self.skill_manager = skill_manager
        if self.langchain_service is not None:
            self.langchain_service.skill_manager = skill_manager

    def set_store_service(self, store_service) -> None:
        """Inject StoreService after construction."""
        self.store_service = store_service
        if self.langchain_service is not None:
            self.langchain_service.store_service = store_service

    def set_job_usecases(self, job_usecases) -> None:
        """Inject job usecases after construction."""
        self.job_usecases = job_usecases
        if self.langchain_service is not None:
            self.langchain_service.job_usecases = job_usecases


    @log_function_call
    async def ask(
        self,
        question: str,
        context: Optional[str],
        previous_messages: str,
        profile: Profile,
        conversation_id: Optional[str] = None,
        client_workspace: str = "",
    ) -> str:
        self.logger.info(f"Processing question for profile: {profile.user_id}")

        self.logger.info("Using LangChain service for response generation")
        messages_list = self._parse_previous_messages(previous_messages)

        return await self.langchain_service.generate_response(
            question=question,
            context=context,
            previous_messages=messages_list,
            profile=profile,
            conversation_id=conversation_id or profile.user_id,
            use_tools=True,
            client_workspace=client_workspace,
        )

    async def ask_stream(
        self,
        question: str,
        context: Optional[str],
        previous_messages: str,
        profile: Profile,
        conversation_id: Optional[str] = None,
        shell_output_queue=None,
        client_workspace: str = "",
        plan_mode: bool = False,
        has_pty: bool = False,
    ):
        """Stream AI response tokens via LangChain. Yields str tokens and shell_output dicts.

        Args:
            shell_output_queue: Optional asyncio.Queue. When provided, run_shell tool output
                is emitted line-by-line as {"type": "shell_output", "line": "..."} dicts
                in real time rather than buffering until the command finishes.
            client_workspace: Optional path sent by the CLI client via X-Gillie-Workspace.
                When non-empty, overrides the GILLIE_WORKSPACE env var for all file tools.
            plan_mode: When True, state-mutating tools return a description of the intended
                change without applying it (sent via X-Gillie-Mode: plan header).
        """
        if self.langchain_service is None:
            raise Exception("LangChain service not available for streaming")
        messages_list = self._parse_previous_messages(previous_messages)
        async for token in self.langchain_service.generate_response_stream(
            question=question,
            context=context,
            previous_messages=messages_list,
            profile=profile,
            conversation_id=conversation_id or profile.user_id,
            use_tools=True,
            shell_output_queue=shell_output_queue,
            client_workspace=client_workspace,
            plan_mode=plan_mode,
            has_pty=has_pty,
        ):
            yield token

    @log_function_call
    async def search_images_in_files(
        self, search_term: str, profile: Profile, max_results: int = 5
    ) -> List[ImageSearchResult]:
        self.logger.info(
            f"Searching images for term: '{search_term}' in {len(profile.files or [])} files"
        )

        if not profile.files:
            return []

        all_results = []

        for file in profile.files:
            if file.url.lower().endswith(".pdf"):
                try:
                    results = await self.image_processor.search_images_in_pdf(
                        file.url, search_term, max_results
                    )
                    all_results.extend(results)
                    self.logger.debug(f"Found {len(results)} images in PDF: {file.url}")
                except Exception as e:
                    self.logger.error(f"Error searching images in PDF {file.url}: {e}")
                    continue
            elif file.url.lower().endswith((".xlsx", ".xls")):
                try:
                    results = await self.excel_processor.search_images_in_excel(
                        file.url, search_term, max_results
                    )
                    all_results.extend(results)
                    self.logger.debug(
                        f"Found {len(results)} images in Excel: {file.url}"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error searching images in Excel {file.url}: {e}"
                    )
                    continue

        all_results.sort(key=lambda x: x.confidence, reverse=True)
        final_results = all_results[:max_results]
        self.logger.info(f"Total images found: {len(final_results)}")
        return final_results

    @log_function_call
    async def describe_image_from_base64(self, image_base64: str, prompt: str = None) -> str:
        self.logger.debug("Describing image from base64")
        return await self.image_processor.describe_image(image_base64, prompt=prompt)

    @log_function_call
    async def analyze_excel_file(self, excel_url: str) -> dict:
        self.logger.info(f"Analyzing Excel file: {excel_url}")
        return await self.excel_processor.analyze_excel_data(excel_url)

    @log_function_call
    async def extract_text_and_images_from_pdf(
        self, pdf_url: str, search_term: Optional[str] = None
    ) -> dict:
        self.logger.info(f"Extracting text and images from PDF: {pdf_url}")
        try:
            return await self.image_processor.extract_text_and_images(
                pdf_url, search_term
            )
        except Exception as e:
            self.logger.error(f"Error processing PDF with OCR: {e}")
            return {
                "error": f"Error processing PDF with OCR: {str(e)}",
                "analysis": None,
                "extracted_text": None,
                "related_images": None,
                "recommendations": ["Manual review required"],
            }

    @log_function_call
    async def analyze_pdf_content(self, pdf_url: str) -> dict:
        self.logger.info(f"Analyzing PDF content: {pdf_url}")
        try:
            analysis_result = await self.image_processor.analyze_pdf_content(pdf_url)
            result = {
                "has_text": analysis_result.has_text,
                "total_pages": analysis_result.total_pages,
                "text_pages": analysis_result.text_pages,
                "image_pages": analysis_result.image_pages,
                "processing_method": analysis_result.processing_method,
                "text_extraction_count": len(analysis_result.text_extraction_results),
            }
            self.logger.info(
                f"PDF analysis completed: {result['total_pages']} pages, {result['text_extraction_count']} text extractions"
            )
            return result
        except Exception as e:
            self.logger.error(f"Error analyzing PDF content: {e}")
            return {
                "error": f"Error analyzing PDF content: {str(e)}",
                "has_text": False,
                "total_pages": 0,
                "text_pages": [],
                "image_pages": [],
                "processing_method": "error",
            }

    @log_function_call
    async def search_images_with_text_analysis(
        self, search_term: str, profile: Profile, max_results: int = 5
    ) -> List[ImageSearchResult]:
        self.logger.info(
            f"Enhanced image search with text analysis for term: '{search_term}'"
        )

        if not profile.files:
            return []

        all_results = []

        for file in profile.files:
            if file.url.lower().endswith(".pdf"):
                try:
                    results = await self.image_processor.search_images_in_pdf_with_text_analysis(
                        file.url, search_term, max_results
                    )
                    all_results.extend(results)
                    self.logger.debug(
                        f"Enhanced search found {len(results)} images in PDF: {file.url}"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error in enhanced PDF image search {file.url}: {e}"
                    )
                    try:
                        results = await self.image_processor.search_images_in_pdf(
                            file.url, search_term, max_results
                        )
                        all_results.extend(results)
                        self.logger.debug(
                            f"Fallback search found {len(results)} images in PDF: {file.url}"
                        )
                    except Exception as fallback_e:
                        self.logger.error(
                            f"Error in fallback PDF search {file.url}: {fallback_e}"
                        )
                        continue
            elif file.url.lower().endswith((".xlsx", ".xls")):
                try:
                    results = await self.excel_processor.search_images_in_excel(
                        file.url, search_term, max_results
                    )
                    all_results.extend(results)
                    self.logger.debug(
                        f"Found {len(results)} images in Excel: {file.url}"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error searching images in Excel {file.url}: {e}"
                    )
                    continue

        all_results.sort(key=lambda x: x.confidence, reverse=True)
        final_results = all_results[:max_results]
        self.logger.info(
            f"Enhanced search completed: {len(final_results)} total results"
        )
        return final_results

    @log_execution_time
    async def _extract_text_from_excel_async(
        self, file_url: str, chunk_size: int = 1000
    ) -> str:
        self.logger.debug(f"Extracting text from Excel file: {file_url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as response:
                    response.raise_for_status()

                    with tempfile.NamedTemporaryFile(
                        suffix=".xlsx", delete=False
                    ) as temp_file:
                        temp_path = temp_file.name

                        async for chunk in response.content.iter_chunked(8192):
                            temp_file.write(chunk)

            import pandas as pd
            text_parts = []
            try:
                excel_file = pd.ExcelFile(temp_path)

                for sheet_name in excel_file.sheet_names:
                    sheet_text = f"\n--- Sheet: {sheet_name} ---\n"

                    try:
                        df = pd.read_excel(
                            temp_path, sheet_name=sheet_name, nrows=chunk_size
                        )
                        sheet_text += df.to_string(index=False, max_rows=chunk_size)

                        total_rows = len(
                            pd.read_excel(temp_path, sheet_name=sheet_name, usecols=[0])
                        )
                        if total_rows > chunk_size:
                            sheet_text += f"\n... (showing first {chunk_size} of {total_rows} rows)"

                    except Exception as e:
                        sheet_text += f"Error reading sheet {sheet_name}: {e}"

                    text_parts.append(sheet_text)

                    await asyncio.sleep(0)

            finally:
                excel_file.close()
                os.unlink(temp_path)

            extracted_text = "\n".join(text_parts)
            self.logger.debug(
                f"Excel text extraction completed: {len(extracted_text)} characters"
            )
            return extracted_text

        except Exception as e:
            self.logger.error(f"Error reading Excel file {file_url}: {e}")
            return f"Error reading Excel file {file_url}: {e}"

    @log_execution_time
    async def _extract_text_from_pdf_async(
        self, file_url: str, max_pages: int = 50
    ) -> str:
        self.logger.debug(
            f"Extracting text from PDF file: {file_url}, max pages: {max_pages}"
        )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as response:
                    response.raise_for_status()

                    with tempfile.NamedTemporaryFile(
                        suffix=".pdf", delete=False
                    ) as temp_file:
                        temp_path = temp_file.name

                        async for chunk in response.content.iter_chunked(8192):
                            temp_file.write(chunk)

            from PyPDF2 import PdfReader
            text_parts = []
            try:
                with open(temp_path, "rb") as file:
                    reader = PdfReader(file)
                    total_pages = len(reader.pages)

                    pages_to_read = min(max_pages, total_pages)
                    self.logger.debug(
                        f"Processing {pages_to_read} of {total_pages} pages"
                    )

                    for i in range(pages_to_read):
                        page = reader.pages[i]
                        page_text = page.extract_text() or ""
                        text_parts.append(page_text)

                        if i % 10 == 0:
                            await asyncio.sleep(0)

                    if total_pages > max_pages:
                        text_parts.append(
                            f"\n... (showing first {max_pages} of {total_pages} pages)"
                        )

            finally:
                os.unlink(temp_path)

            extracted_text = "\n".join(text_parts)
            self.logger.debug(
                f"PDF text extraction completed: {len(extracted_text)} characters from {pages_to_read} pages"
            )
            return extracted_text

        except Exception as e:
            self.logger.error(f"Error reading PDF file {file_url}: {e}")
            return f"Error reading PDF file {file_url}: {e}"

    async def _extract_text_with_summary(
        self, file_url: str, max_chars: int = 50000
    ) -> str:
        self.logger.debug(
            f"Extracting text with summary from: {file_url}, max chars: {max_chars}"
        )

        if file_url.lower().endswith((".xlsx", ".xls")):
            text = await self._extract_text_from_excel_async(file_url)
        elif file_url.lower().endswith(".pdf"):
            text = await self._extract_text_from_pdf_async(file_url)
        else:
            self.logger.warning(f"Unsupported format: {file_url}")
            return f"Unsupported format: {file_url}"

        if len(text) > max_chars:
            truncated_text = text[:max_chars]
            truncated_text += f"\n\n[TEXT TRUNCATED - File too large. Showing first {max_chars} characters of {len(text)} total]"
            self.logger.info(f"Text truncated: {len(text)} -> {max_chars} characters")
            return truncated_text

        return text

    @log_execution_time
    async def process_document_with_langchain(
        self, file_url: str, file_type: str, use_vectors: bool = True
    ) -> Dict[str, Any]:
        """
        Process document using LangChain hybrid processor
        """
        try:
            self.logger.info(
                f"Processing {file_type} document with LangChain: {file_url}"
            )

            if use_vectors:
                result = await self.hybrid_processor.process_document_with_vectors(
                    file_url, file_type, use_langchain=True
                )
            else:
                if file_type.lower() == "pdf":
                    result = await self.hybrid_processor.process_pdf_hybrid(
                        file_url, use_langchain=True
                    )
                elif file_type.lower() in ["xlsx", "xls"]:
                    result = await self.hybrid_processor.process_xlsx_hybrid(
                        file_url, use_langchain=True
                    )
                else:
                    return {"error": f"Unsupported file type: {file_type}"}

            self.logger.info(
                f"Document processed successfully with method: {result.get('processing_method', 'unknown')}"
            )
            return result

        except Exception as e:
            self.logger.error(f"Error processing document with LangChain: {e}")
            return {"error": f"Error processing document: {str(e)}"}

    @log_execution_time
    async def search_across_documents(
        self, query: str, file_urls: List[str], file_types: List[str]
    ) -> Dict[str, Any]:
        """
        Search across multiple documents using vector similarity
        """
        try:
            self.logger.info(
                f"Searching across {len(file_urls)} documents with query: {query}"
            )

            result = await self.hybrid_processor.search_across_documents(
                query, file_urls, file_types
            )

            if "error" not in result:
                self.logger.info(
                    f"Search completed successfully with {result.get('total_results', 0)} results"
                )

            return result

        except Exception as e:
            self.logger.error(f"Error searching across documents: {e}")
            return {"error": f"Error searching documents: {str(e)}"}

    @log_execution_time
    async def extract_text_hybrid(
        self, file_url: str, file_type: str, use_langchain: bool = True
    ) -> str:
        """
        Extract text using hybrid approach (LangChain + legacy fallback)
        """
        try:
            if use_langchain:
                result = await self.process_document_with_langchain(
                    file_url, file_type, use_vectors=False
                )
            else:
                if file_type.lower() == "pdf":
                    result = await self._extract_text_from_pdf_async(file_url)
                    return result
                elif file_type.lower() in ["xlsx", "xls"]:
                    result = await self._extract_text_from_excel_async(file_url)
                    return result
                else:
                    return f"Unsupported file type: {file_type}"

            if "error" in result:
                self.logger.warning(
                    f"LangChain processing failed: {result['error']}, falling back to legacy"
                )
                if file_type.lower() == "pdf":
                    return await self._extract_text_from_pdf_async(file_url)
                elif file_type.lower() in ["xlsx", "xls"]:
                    return await self._extract_text_from_excel_async(file_url)

            return result.get("extracted_text", {}).get("full_text", "")

        except Exception as e:
            self.logger.error(f"Error in hybrid text extraction: {e}")
            return f"Error extracting text: {str(e)}"

    def _refresh_claude_code_token(self) -> Optional[str]:
        """
        Read the Claude Code OAuth credentials from ~/.claude/.credentials.json.

        Returns the current accessToken if still valid, or attempts to refresh
        it using the stored refreshToken.  Writes the updated credentials back
        to disk so subsequent calls pick up the fresh token.

        Returns the accessToken string, or None on failure.
        """
        creds_path = Path.home() / ".claude" / ".credentials.json"
        if not creds_path.exists():
            self.logger.warning(f"Claude Code credentials not found at {creds_path}")
            return None

        try:
            creds = json.loads(creds_path.read_text())
            oauth = creds.get("claudeAiOauth", {})
            access_token = oauth.get("accessToken")
            refresh_token = oauth.get("refreshToken")
            expires_at_ms = oauth.get("expiresAt", 0)

            if not access_token:
                self.logger.warning("No accessToken in Claude Code credentials")
                return None

            # Use current token if still valid (with a 60-second buffer)
            if time.time() * 1000 < expires_at_ms - 60_000:
                self.logger.info("Claude Code token still valid; reusing existing accessToken")
                return access_token

            # Token is expired — try to refresh
            if not refresh_token:
                self.logger.warning("Token expired and no refreshToken available")
                return None

            self.logger.info("Claude Code token expired; refreshing via OAuth endpoint")
            import urllib.request
            payload = json.dumps({
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            }).encode()
            req = urllib.request.Request(
                "https://claude.ai/api/auth/oauth/token",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read())

            new_access = body.get("access_token")
            new_refresh = body.get("refresh_token", refresh_token)
            new_expires = body.get("expires_in")  # seconds from now

            if not new_access:
                self.logger.warning(f"Token refresh response missing access_token: {body}")
                return None

            # Persist the refreshed credentials
            oauth["accessToken"] = new_access
            oauth["refreshToken"] = new_refresh
            if new_expires:
                oauth["expiresAt"] = int((time.time() + new_expires) * 1000)
            creds["claudeAiOauth"] = oauth
            creds_path.write_text(json.dumps(creds))

            self.logger.info("Claude Code token refreshed and persisted successfully")
            return new_access

        except Exception as e:
            self.logger.error(f"Failed to refresh Claude Code token: {e}")
            return None

    def _handle_bearer_401(self) -> bool:
        """
        Attempt to recover from a 401 by refreshing the Claude Code OAuth token.

        Returns True if the token was refreshed successfully and the client was
        rebuilt; False otherwise.  Only acts when auth_type == "bearer".
        """
        if self.auth_type != "bearer":
            return False

        self.logger.info("Received 401; attempting Claude Code token refresh")
        new_token = self._refresh_claude_code_token()
        if not new_token:
            self.logger.warning("Token refresh returned empty; cannot retry")
            return False

        self.api_key = new_token
        self.client = self._build_client()
        self.logger.info("Token refreshed and client rebuilt successfully")
        return True

    async def simple_completion(self, system: str, user: str) -> str:
        """
        Performs a minimal, tool-free chat completion.

        This is intentionally kept separate from `ask` / `ask_stream` because
        those methods route through LangChain with tools enabled, which is
        inappropriate for internal housekeeping calls such as conversation
        compaction summarisation.

        When auth_type == "bearer" a single transparent retry is attempted on
        401 errors by refreshing the Claude Code OAuth token.

        Args:
            system: The system prompt content.
            user: The user prompt content.

        Returns:
            The assistant reply text, or an empty string on failure.
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        for attempt in range(2):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=1024,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                is_auth_error = "401" in str(e) or "authentication" in str(e).lower()
                if attempt == 0 and is_auth_error and self._handle_bearer_401():
                    continue  # retry with refreshed token
                self.logger.error(f"simple_completion failed: {e}")
                return ""
        return ""

    def _parse_previous_messages(self, previous_messages: str) -> List[Dict[str, Any]]:
        """
        Parse previous messages string into list format for LangChain.

        Args:
            previous_messages: String with format "sender: content - sender: content"

        Returns:
            List of message dictionaries
        """
        if not previous_messages or previous_messages.strip() == "":
            return []

        messages = []
        try:
            # Split by " - " to get individual messages
            message_parts = previous_messages.split(" - ")

            for part in message_parts:
                if ":" in part:
                    sender, content = part.split(":", 1)
                    messages.append({
                        "sender": sender.strip(),
                        "content": content.strip()
                    })
        except Exception as e:
            self.logger.warning(f"Error parsing previous messages: {e}")
            return []

        return messages

