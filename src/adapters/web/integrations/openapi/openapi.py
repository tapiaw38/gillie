from src.core.platform.config.service import ConfigurationService
from openai import AsyncOpenAI
from typing import Optional, List, Dict, Any, Tuple
import os
from src.core.domain import Profile
from src.core.platform.fileprocessor.pdf_processor import FileImageProcessor
from src.core.platform.fileprocessor.xlsx_processor import ExcelImageProcessor
from src.core.platform.fileprocessor.processor import ImageSearchResult
from src.core.platform.fileprocessor.hybrid_processor import HybridDocumentProcessor
from src.core.platform.fileprocessor.rag_processor import RAGDocumentProcessor
from src.core.platform.logging import get_logger, log_function_call, log_execution_time
import pandas as pd
import json
from PyPDF2 import PdfReader
import asyncio
import aiohttp
import tempfile


class OpenAIIntegration:
    def __init__(self, config_service: ConfigurationService):
        self.logger = get_logger(__name__)
        config = config_service.openai_config

        self.api_key = config.api_key
        self.base_url = config.base_url
        self.model = config.model
        self.role = config.role

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=45.0,
            max_retries=3,
        )

        self.image_processor = FileImageProcessor(config_service)
        self.excel_processor = ExcelImageProcessor(config_service)
        self.hybrid_processor = HybridDocumentProcessor(config_service)
        self.rag_processor = RAGDocumentProcessor(config_service)
        self._stored_parameters = {}

        self._processed_documents = {}

        self._consecutive_failures = 0
        self._max_failures = 3
        self._circuit_open_until = None
        self.langchain_service = None
        self.skill_manager = None

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

        self.logger.info(f"OpenAI integration initialized with model: {self.model}")

    def set_skill_manager(self, skill_manager) -> None:
        """Inject SkillManager after construction (avoids circular init order)."""
        self.skill_manager = skill_manager
        if self.langchain_service is not None:
            self.langchain_service.skill_manager = skill_manager

    @log_function_call
    async def ask(
        self,
        question: str,
        context: Optional[str],
        previous_messages: str,
        profile: Profile,
        conversation_id: Optional[str] = None,
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
        )

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
    async def describe_image_from_base64(self, image_base64: str) -> str:
        self.logger.debug("Describing image from base64")
        return await self.image_processor.describe_image(image_base64)

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

    def _is_circuit_open(self) -> bool:
        if self._circuit_open_until is None:
            return False

        import time

        if time.time() < self._circuit_open_until:
            return True

        self._circuit_open_until = None
        self._consecutive_failures = 0
        self.logger.info(
            "Circuit breaker reset - attempting to reconnect to AI service"
        )
        return False

    def _record_failure(self):
        self._consecutive_failures += 1
        self.logger.warning(f"AI service failure #{self._consecutive_failures}")

        if self._consecutive_failures >= self._max_failures:
            import time

            self._circuit_open_until = time.time() + 60
            self.logger.error(
                f"Circuit breaker OPENED - AI service will be bypassed for 60 seconds"
            )

    def _record_success(self):
        if self._consecutive_failures > 0:
            self.logger.info(
                f"AI service recovered after {self._consecutive_failures} failures"
            )
            self._consecutive_failures = 0

    @log_function_call
    async def analyze_text_with_ai(
        self, text: str, actions_text: str
    ) -> Dict[str, Any]:
        self.logger.info(f"Analyzing text with AI: '{text[:100]}...'")

        if self._is_circuit_open():
            self.logger.warning("Circuit breaker is OPEN - skipping AI analysis")
            return {"matches_action": False, "confidence": 0.0, "extracted_params": {}}

        try:
            action = json.loads(actions_text)
            action_name = action.get("name", "")

            prompt = f"""IMPORTANTE: Responde SOLO con JSON válido.

Analiza: "{text}"
Función: {action_name}

¿El texto solicita explícitamente {action_name}?
- "clima", "temperatura", "tiempo" = SÍ
- "hola", "gracias" = NO
- Coordenadas: extrae números como "lat, lon"

RESPUESTA (solo JSON):
{{"matches_action": true/false, "confidence": 0.9, "extracted_params": {{"latitude": "", "longitude": ""}}}}"""

            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": self.role, "content": prompt}],
                    temperature=0.1,
                )

                ai_response = response.choices[0].message.content.strip()
                self.logger.debug(f"AI response received: {ai_response[:200]}...")

                try:
                    import re

                    json_match = re.search(r"\{.*\}", ai_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        result = json.loads(json_str)
                    else:
                        result = {
                            "matches_action": False,
                            "confidence": 0.0,
                            "extracted_params": {},
                        }
                except json.JSONDecodeError as json_error:
                    self.logger.warning(
                        f"Failed to parse AI response as JSON: {json_error}"
                    )
                    result = {
                        "matches_action": False,
                        "confidence": 0.0,
                        "extracted_params": {},
                    }

                self._record_success()

                if result.get("matches_action", False):
                    extracted_params = result.get("extracted_params", {})
                    if (
                        "latitude" in extracted_params
                        and "longitude" in extracted_params
                    ):
                        try:
                            lat = float(extracted_params["latitude"])
                            lon = float(extracted_params["longitude"])
                            if -90 <= lat <= 90 and -180 <= lon <= 180:
                                self.store_parameter(
                                    "consultar_clima", "latitude", str(lat)
                                )
                                self.store_parameter(
                                    "consultar_clima", "longitude", str(lon)
                                )
                                self.logger.info(
                                    f"AI extracted and validated coordinates: lat={lat}, lon={lon}"
                                )
                                result["confidence"] = 0.9
                        except (ValueError, TypeError) as e:
                            self.logger.error(
                                f"Error validating coordinates from AI: {e}"
                            )

                self.logger.info(
                    f"AI analysis completed: matches_action={result.get('matches_action')}, confidence={result.get('confidence')}"
                )
                return result

            except Exception as api_error:
                self._record_failure()

                error_message = str(api_error)
                self.logger.error(f"Error in AI API call: {error_message}")

                if (
                    "Connection error" in error_message
                    or "connection" in error_message.lower()
                ):
                    self.logger.error("Network connectivity issue with AI service")
                elif (
                    "timeout" in error_message.lower()
                    or "timed out" in error_message.lower()
                ):
                    self.logger.error(
                        "AI service timeout - service is slow or overloaded"
                    )
                elif "402" in error_message or "insufficient" in error_message.lower():
                    self.logger.error("AI service billing/credit issue")
                elif "401" in error_message or "unauthorized" in error_message.lower():
                    self.logger.error("AI service authentication issue")
                elif "429" in error_message or "rate limit" in error_message.lower():
                    self.logger.error("AI service rate limit exceeded")
                else:
                    self.logger.error(f"Unknown AI service error: {error_message}")

                raise api_error

        except Exception as e:
            self.logger.error(f"Error in AI analysis: {str(e)}")
            return {"matches_action": False, "confidence": 0.0, "extracted_params": {}}

    def store_parameter(self, action_name: str, param_name: str, param_value: str):
        try:
            param_value = str(param_value).strip()
            if action_name not in self._stored_parameters:
                self._stored_parameters[action_name] = {}
            self._stored_parameters[action_name][param_name] = param_value
            self.logger.debug(
                f"Stored parameter: {action_name}.{param_name} = {param_value}"
            )
        except Exception as e:
            self.logger.error(f"Error storing parameter: {e}")

    @log_function_call
    async def analyze_text(
        self, text: str, actions_text: str
    ) -> Tuple[bool, List[str], str]:
        self.logger.info(f"Analyzing text for actions: '{text[:100]}...'")

        try:
            action = json.loads(actions_text)

            action_name = action.get("name", "").lower()
            url_template = action.get("url", "")
            import re

            required_params = re.findall(r"\{(\w+)\}", url_template)
            self.logger.debug(f"Required parameters: {required_params}")

            ai_result = await self.analyze_text_with_ai(text, actions_text)

            if not ai_result.get("matches_action", False):
                self.logger.debug(
                    "AI analysis failed, falling back to pattern detection"
                )
                ai_result = self._detect_function_with_patterns(
                    text, action_name, required_params
                )

            if ai_result.get("matches_action", False):
                extracted_params = ai_result.get("extracted_params", {})
                for param_name, param_value in extracted_params.items():
                    if param_value and param_value.strip():
                        self.store_parameter(action_name, param_name, param_value)

            stored_action_params = self._stored_parameters.get(action_name, {})
            self.logger.debug(f"Stored parameters: {stored_action_params}")

            missing_params = [
                param for param in required_params if param not in stored_action_params
            ]

            if ai_result.get("matches_action", False) and missing_params:
                self.logger.info(
                    f"Action matches but missing parameters: {missing_params}"
                )
                return False, missing_params, ""

            if ai_result.get("matches_action", False) and not missing_params:
                final_url = url_template
                for param, value in stored_action_params.items():
                    final_url = final_url.replace(f"{{{param}}}", str(value))
                self.logger.info(f"Action ready with final URL: {final_url}")
                return True, [], final_url

            self.logger.debug("Action does not match or parameters incomplete")
            return False, [], ""

        except json.JSONDecodeError:
            self.logger.error("Invalid JSON in actions_text")
            return False, [], ""
        except Exception as e:
            self.logger.error(f"Error analyzing text: {str(e)}")
            return False, [], ""

    def _detect_function_with_patterns(
        self, text: str, action_name: str, required_params: List[str]
    ) -> Dict[str, Any]:
        import re

        text_lower = text.lower().strip()
        self.logger.debug(f"Pattern detection for action: {action_name}")

        matches_action = False

        function_keywords = {
            "consultar_clima": [
                "clima",
                "tiempo",
                "temperatura",
                "pronóstico",
                "weather",
                "lluvia",
                "sol",
                "nublado",
                "frío",
                "calor",
            ],
            "noticias": ["noticias", "news", "actualidad", "información"],
            "traducir": ["traducir", "translate", "idioma", "language"],
            "cotizacion": ["precio", "cotización", "valor", "costo", "dólar", "euro"],
        }

        keywords = function_keywords.get(action_name, [action_name])
        for keyword in keywords:
            if keyword in text_lower:
                matches_action = True
                self.logger.debug(
                    f"Pattern detection: Found keyword '{keyword}' for function '{action_name}'"
                )
                break

        extracted_params = {}

        if (
            matches_action
            and "latitude" in required_params
            and "longitude" in required_params
        ):
            coord_patterns = [
                r"(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)",
                r"latitud[:\s]*(-?\d+\.?\d*).*longitud[:\s]*(-?\d+\.?\d*)",
                r"lat[:\s]*(-?\d+\.?\d*).*lon[:\s]*(-?\d+\.?\d*)",
                r"coordenadas[:\s]*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)",
            ]

            for pattern in coord_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    try:
                        lat, lon = match.groups()
                        lat_float = float(lat)
                        lon_float = float(lon)

                        if -90 <= lat_float <= 90 and -180 <= lon_float <= 180:
                            extracted_params["latitude"] = str(lat_float)
                            extracted_params["longitude"] = str(lon_float)
                            self.logger.info(
                                f"Pattern detection: Extracted coordinates lat={lat_float}, lon={lon_float}"
                            )
                            break
                    except (ValueError, TypeError):
                        continue

        if matches_action and not extracted_params and "latitude" in required_params:
            city_coords = {
                "madrid": {"latitude": "40.4168", "longitude": "-3.7038"},
                "barcelona": {"latitude": "41.3851", "longitude": "2.1734"},
                "valencia": {"latitude": "39.4699", "longitude": "-0.3763"},
                "sevilla": {"latitude": "37.3891", "longitude": "-5.9845"},
                "bilbao": {"latitude": "43.2627", "longitude": "-2.9253"},
                "buenos aires": {"latitude": "-34.6132", "longitude": "-58.3772"},
                "lima": {"latitude": "-12.0464", "longitude": "-77.0428"},
                "bogotá": {"latitude": "4.7110", "longitude": "-74.0721"},
                "santiago": {"latitude": "-33.4489", "longitude": "-70.6693"},
                "méxico": {"latitude": "19.4326", "longitude": "-99.1332"},
                "ciudad de méxico": {"latitude": "19.4326", "longitude": "-99.1332"},
            }

            for city, coords in city_coords.items():
                if city in text_lower:
                    extracted_params.update(coords)
                    self.logger.info(
                        f"Pattern detection: Found city '{city}' with coordinates {coords}"
                    )
                    break

        confidence = (
            0.8
            if matches_action and extracted_params
            else (0.6 if matches_action else 0.0)
        )

        result = {
            "matches_action": matches_action,
            "confidence": confidence,
            "extracted_params": extracted_params,
        }

        self.logger.debug(f"Pattern detection result: {result}")
        return result

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

