from src.core.platform.config.service import ConfigurationService
from openai import AsyncOpenAI
from typing import Optional, List, Dict, Any, Tuple
from src.adapters.web.integrations.openapi.context import (
    CONTEXT_INFORMATION,
    CONTEXT_ROLE_ASSISTANT,
    CONTEXT_ROLE_SELLER,
    CONTEXT_ROLE_TUTOR,
    CONTEXT_RULES,
)
from src.core.domain.model import Profile
from src.core.platform.fileprocessor.pdf_processor import FileImageProcessor
from src.core.platform.fileprocessor.xlsx_processor import ExcelImageProcessor
from src.core.platform.fileprocessor.processor import ImageSearchResult
import pandas as pd
import requests
import json
from io import BytesIO
from PyPDF2 import PdfReader
import asyncio
import aiohttp
import aiofiles
import tempfile
import os
from pathlib import Path


class OpenAIIntegration:
    def __init__(self, config_service: ConfigurationService):
        config = config_service.openai_config

        self.api_key = config.api_key
        self.base_url = config.base_url
        self.model = config.model
        self.role = config.role

        self.client = AsyncOpenAI(
            api_key=self.api_key, 
            base_url=self.base_url,
            timeout=45.0,  # Aumentar timeout a 45 segundos para conexiones lentas
            max_retries=3   # Aumentar reintentos para problemas de conectividad
        )

        self.image_processor = FileImageProcessor(config_service)
        self.excel_processor = ExcelImageProcessor(config_service)
        self._stored_parameters = {}
        
        # Circuit breaker para manejar fallos consecutivos
        self._consecutive_failures = 0
        self._max_failures = 3
        self._circuit_open_until = None

    async def ask(
        self,
        question: str,
        context: Optional[str],
        previous_messages: str,
        profile: Profile,
    ) -> str:

        extracted_text = ""
        if profile.files:
            for file in profile.files:
                try:
                    if file.url.lower().endswith((".xlsx", ".xls")):
                        extracted_text += (
                            await self._extract_text_from_excel_async(file.url) + "\n"
                        )
                    elif file.url.lower().endswith(".pdf"):
                        extracted_text += (
                            await self._extract_text_from_pdf_async(file.url) + "\n"
                        )
                    else:
                        raise ValueError(f"Unsupported file format: {file.url}")
                except Exception as e:
                    print(f"Error processing file {file.url}: {e}")
                    continue

        full_context = f"{context or ''}\n{extracted_text.strip()}"

        question_message = CONTEXT_INFORMATION.format(
            assistant_name=profile.assistant_name,
            business_name=profile.business_name,
            business_context=profile.business_context,
            functions=profile.functions,
            product_context=full_context,
            question=question,
            previous_messages=previous_messages,
        )

        if profile.role == "seller":
            question_message += CONTEXT_ROLE_SELLER
        elif profile.role == "tutor":
            question_message += CONTEXT_ROLE_TUTOR
        elif profile.role == "assistant":
            question_message += CONTEXT_ROLE_ASSISTANT

        question_message += CONTEXT_RULES

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": self.role, "content": question_message},
            ],
        )
        return response.choices[0].message.content

    async def search_images_in_files(
        self, search_term: str, profile: Profile, max_results: int = 5
    ) -> List[ImageSearchResult]:
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
                except Exception as e:
                    print(f"Error searching images in PDF {file.url}: {e}")
                    continue
            elif file.url.lower().endswith((".xlsx", ".xls")):
                try:
                    results = await self.excel_processor.search_images_in_excel(
                        file.url, search_term, max_results
                    )
                    all_results.extend(results)
                except Exception as e:
                    print(f"Error searching images in Excel {file.url}: {e}")
                    continue

        all_results.sort(key=lambda x: x.confidence, reverse=True)
        return all_results[:max_results]

    async def describe_image_from_base64(self, image_base64: str) -> str:
        return await self.image_processor.describe_image(image_base64)

    async def analyze_text_for_function(
        self, 
        message: str, 
        functions_config: str
    ) -> Tuple[bool, List[str], Optional[str]]:
        """
        Analyze if the message is requesting a function and what parameters are needed
        
        Returns:
            - bool: True if all parameters are available and function can be executed
            - List[str]: Missing parameters
            - Optional[str]: Complete URL if ready to execute
        """
        try:
            from src.core.platform.functions.function_parameter_manager import FunctionParameterManager
            
            # This should be stored per conversation, but for now we'll create a new instance
            # In production, you'd want to inject this as a dependency
            param_manager = FunctionParameterManager()
            
            # For now, we'll use a dummy conversation_id
            # In the real implementation, this should come from the conversation context
            conversation_id = "temp_conversation"
            
            return param_manager.analyze_message_for_function(
                message, functions_config, conversation_id
            )
            
        except Exception as e:
            # Fallback to original behavior if there's an error
            return False, [], None

    async def analyze_excel_file(self, excel_url: str) -> dict:
        """Analyze Excel file structure and data"""
        return await self.excel_processor.analyze_excel_data(excel_url)

    async def extract_text_and_images_from_pdf(
        self, pdf_url: str, search_term: Optional[str] = None
    ) -> dict:
        """
        Extract text and images from PDF using OCR if necessary.
        Uses the enhanced PDF processor with OCR capabilities.

        Args:
            pdf_url: URL of the PDF to process
            search_term: Optional search term to filter images

        Returns:
            Dictionary with extracted text, related images and metadata
        """
        try:
            return await self.image_processor.extract_text_and_images(
                pdf_url, search_term
            )
        except Exception as e:
            return {
                "error": f"Error processing PDF with OCR: {str(e)}",
                "analysis": None,
                "extracted_text": None,
                "related_images": None,
                "recommendations": ["Manual review required"],
            }

    async def analyze_pdf_content(self, pdf_url: str) -> dict:
        """
        Analyze PDF content to determine processing method needed.

        Args:
            pdf_url: URL of the PDF to analyze

        Returns:
            Dictionary with analysis results
        """
        try:
            analysis_result = await self.image_processor.analyze_pdf_content(pdf_url)
            return {
                "has_text": analysis_result.has_text,
                "total_pages": analysis_result.total_pages,
                "text_pages": analysis_result.text_pages,
                "image_pages": analysis_result.image_pages,
                "processing_method": analysis_result.processing_method,
                "text_extraction_count": len(analysis_result.text_extraction_results),
            }
        except Exception as e:
            return {
                "error": f"Error analyzing PDF content: {str(e)}",
                "has_text": False,
                "total_pages": 0,
                "text_pages": [],
                "image_pages": [],
                "processing_method": "error",
            }

    async def search_images_with_text_analysis(
        self, search_term: str, profile: Profile, max_results: int = 5
    ) -> List[ImageSearchResult]:
        """
        Enhanced image search that includes text analysis for PDFs.
        Uses OCR when PDFs don't have readable text.

        Args:
            search_term: Term to search for
            profile: User profile with files
            max_results: Maximum number of results to return

        Returns:
            List of ImageSearchResult with enhanced descriptions
        """
        if not profile.files:
            return []

        all_results = []

        for file in profile.files:
            if file.url.lower().endswith(".pdf"):
                try:
                    # Use enhanced search with text analysis
                    results = await self.image_processor.search_images_in_pdf_with_text_analysis(
                        file.url, search_term, max_results
                    )
                    all_results.extend(results)
                except Exception as e:
                    print(f"Error in enhanced PDF image search {file.url}: {e}")
                    # Fallback to original method
                    try:
                        results = await self.image_processor.search_images_in_pdf(
                            file.url, search_term, max_results
                        )
                        all_results.extend(results)
                    except Exception as fallback_e:
                        print(f"Error in fallback PDF search {file.url}: {fallback_e}")
                        continue
            elif file.url.lower().endswith((".xlsx", ".xls")):
                try:
                    results = await self.excel_processor.search_images_in_excel(
                        file.url, search_term, max_results
                    )
                    all_results.extend(results)
                except Exception as e:
                    print(f"Error searching images in Excel {file.url}: {e}")
                    continue

        all_results.sort(key=lambda x: x.confidence, reverse=True)
        return all_results[:max_results]

    async def _extract_text_from_excel_async(
        self, file_url: str, chunk_size: int = 1000
    ) -> str:
        """
        Extracts text from large Excel files asynchronously and in chunks
        """
        try:
            # Download file in chunks
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as response:
                    response.raise_for_status()

                    # Use temporary file to handle large files
                    with tempfile.NamedTemporaryFile(
                        suffix=".xlsx", delete=False
                    ) as temp_file:
                        temp_path = temp_file.name

                        # Write in chunks to avoid memory saturation
                        async for chunk in response.content.iter_chunked(8192):
                            temp_file.write(chunk)

            # Process Excel with pandas using chunks and lazy loading
            text_parts = []
            try:
                # Read metadata first to optimize
                excel_file = pd.ExcelFile(temp_path)

                for sheet_name in excel_file.sheet_names:
                    # Read sheet by chunks for large files
                    sheet_text = f"\n--- Sheet: {sheet_name} ---\n"

                    # For very large files, read only the first N rows
                    try:
                        df = pd.read_excel(
                            temp_path, sheet_name=sheet_name, nrows=chunk_size
                        )
                        sheet_text += df.to_string(index=False, max_rows=chunk_size)

                        # If there are more rows, add a summary
                        total_rows = len(
                            pd.read_excel(temp_path, sheet_name=sheet_name, usecols=[0])
                        )
                        if total_rows > chunk_size:
                            sheet_text += f"\n... (showing first {chunk_size} of {total_rows} rows)"

                    except Exception as e:
                        sheet_text += f"Error reading sheet {sheet_name}: {e}"

                    text_parts.append(sheet_text)

                    # Yield control to event loop to avoid blocking
                    await asyncio.sleep(0)

            finally:
                excel_file.close()
                # Clean up temporary file
                os.unlink(temp_path)

            return "\n".join(text_parts)

        except Exception as e:
            return f"Error reading Excel file {file_url}: {e}"

    async def _extract_text_from_pdf_async(
        self, file_url: str, max_pages: int = 50
    ) -> str:
        """
        Extracts text from large PDF files asynchronously
        """
        try:
            # Download PDF in chunks
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as response:
                    response.raise_for_status()

                    with tempfile.NamedTemporaryFile(
                        suffix=".pdf", delete=False
                    ) as temp_file:
                        temp_path = temp_file.name

                        # Write in chunks
                        async for chunk in response.content.iter_chunked(8192):
                            temp_file.write(chunk)

            # Process PDF with page limit
            text_parts = []
            try:
                with open(temp_path, "rb") as file:
                    reader = PdfReader(file)
                    total_pages = len(reader.pages)

                    # Limit pages for very large files
                    pages_to_read = min(max_pages, total_pages)

                    for i in range(pages_to_read):
                        page = reader.pages[i]
                        page_text = page.extract_text() or ""
                        text_parts.append(page_text)

                        # Yield control every 10 pages
                        if i % 10 == 0:
                            await asyncio.sleep(0)

                    # Add information about unprocessed pages
                    if total_pages > max_pages:
                        text_parts.append(
                            f"\n... (showing first {max_pages} of {total_pages} pages)"
                        )

            finally:
                # Clean up temporary file
                os.unlink(temp_path)

            return "\n".join(text_parts)

        except Exception as e:
            return f"Error reading PDF file {file_url}: {e}"

    async def _extract_text_with_summary(
        self, file_url: str, max_chars: int = 50000
    ) -> str:
        """
        Extracts text with character limit and generates summary if necessary
        """
        if file_url.lower().endswith((".xlsx", ".xls")):
            text = await self._extract_text_from_excel_async(file_url)
        elif file_url.lower().endswith(".pdf"):
            text = await self._extract_text_from_pdf_async(file_url)
        else:
            return f"Unsupported format: {file_url}"

        # If text is too long, truncate and add information
        if len(text) > max_chars:
            truncated_text = text[:max_chars]
            truncated_text += f"\n\n[TEXT TRUNCATED - File too large. Showing first {max_chars} characters of {len(text)} total]"
            return truncated_text

        return text

    def _is_circuit_open(self) -> bool:
        """Verifica si el circuit breaker está abierto"""
        if self._circuit_open_until is None:
            return False
        
        import time
        if time.time() < self._circuit_open_until:
            return True
        
        # Reset circuit breaker después del tiempo de espera
        self._circuit_open_until = None
        self._consecutive_failures = 0
        print("Circuit breaker reset - attempting to reconnect to AI service")
        return False

    def _record_failure(self):
        """Registra un fallo y abre el circuit breaker si es necesario"""
        self._consecutive_failures += 1
        print(f"AI service failure #{self._consecutive_failures}")
        
        if self._consecutive_failures >= self._max_failures:
            import time
            self._circuit_open_until = time.time() + 60  # 60 segundos de espera
            print(f"Circuit breaker OPENED - AI service will be bypassed for 60 seconds")

    def _record_success(self):
        """Registra un éxito y resetea el contador de fallos"""
        if self._consecutive_failures > 0:
            print(f"AI service recovered after {self._consecutive_failures} failures")
            self._consecutive_failures = 0

    async def analyze_text_with_ai(self, text: str, actions_text: str) -> Dict[str, Any]:
        """
        Utiliza IA para analizar si el texto corresponde a una acción y extraer parámetros.
        
        Args:
            text (str): El texto a analizar
            actions_text (str): JSON con las acciones y sus URLs
            
        Returns:
            Dict[str, Any]: Diccionario con el resultado del análisis
        """
        # Verificar circuit breaker
        if self._is_circuit_open():
            print("Circuit breaker is OPEN - skipping AI analysis")
            return {
                "matches_action": False,
                "confidence": 0.0,
                "extracted_params": {}
            }
        
        try:
            action = json.loads(actions_text)
            action_name = action.get('name', '')
            
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
                    messages=[
                          {"role": self.role, "content": prompt}
                    ],
                    temperature=0.1
                )
                
                ai_response = response.choices[0].message.content.strip()
                print(f"Raw AI response: {ai_response}")
                
                # Intentar extraer JSON de la respuesta
                try:
                    # Buscar JSON en la respuesta
                    import re
                    json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        result = json.loads(json_str)
                    else:
                        # Si no hay JSON, crear respuesta por defecto
                        result = {"matches_action": False, "confidence": 0.0, "extracted_params": {}}
                except json.JSONDecodeError as json_error:
                    print(f"JSON parsing error: {json_error}")
                    print(f"Attempting to parse: {ai_response}")
                    # Crear respuesta por defecto si no se puede parsear
                    result = {"matches_action": False, "confidence": 0.0, "extracted_params": {}}
                
                print(f"AI Analysis result: {result}")
                
                # Registrar éxito
                self._record_success()
                
                # Validar y almacenar coordenadas si se encuentran
                if result.get("matches_action", False):
                    extracted_params = result.get("extracted_params", {})
                    if "latitude" in extracted_params and "longitude" in extracted_params:
                        try:
                            lat = float(extracted_params["latitude"])
                            lon = float(extracted_params["longitude"])
                            if -90 <= lat <= 90 and -180 <= lon <= 180:
                                self.store_parameter("consultar_clima", "latitude", str(lat))
                                self.store_parameter("consultar_clima", "longitude", str(lon))
                                print(f"AI extracted and validated coordinates: lat={lat}, lon={lon}")
                                result["confidence"] = 0.9  # Alta confianza si encontramos coordenadas válidas
                        except (ValueError, TypeError) as e:
                            print(f"Error validating coordinates from AI: {e}")
                
                return result
                
            except Exception as api_error:
                # Registrar fallo
                self._record_failure()
                
                # Manejo específico de errores de la API
                error_message = str(api_error)
                print(f"Error in AI API call: {error_message}")
                
                # Clasificar el tipo de error para mejor logging
                if "Connection error" in error_message or "connection" in error_message.lower():
                    print("Network connectivity issue with AI service")
                elif "timeout" in error_message.lower() or "timed out" in error_message.lower():
                    print("AI service timeout - service is slow or overloaded")
                elif "402" in error_message or "insufficient" in error_message.lower():
                    print("AI service billing/credit issue")
                elif "401" in error_message or "unauthorized" in error_message.lower():
                    print("AI service authentication issue")
                elif "429" in error_message or "rate limit" in error_message.lower():
                    print("AI service rate limit exceeded")
                else:
                    print(f"Unknown AI service error: {error_message}")
                
                # Re-lanzar el error para que sea manejado por el nivel superior
                raise api_error
            
        except Exception as e:
            print(f"Error in AI analysis: {str(e)}")
            return {
                "matches_action": False,
                "confidence": 0.0,
                "extracted_params": {}
            }

    def store_parameter(self, action_name: str, param_name: str, param_value: str):
        """
        Almacena un parámetro proporcionado por el usuario para una acción específica.
        
        Args:
            action_name (str): Nombre de la acción
            param_name (str): Nombre del parámetro
            param_value (str): Valor del parámetro
        """
        try:
            param_value = str(param_value).strip()
            if action_name not in self._stored_parameters:
                self._stored_parameters[action_name] = {}
            self._stored_parameters[action_name][param_name] = param_value
            print(f"Stored parameter: {action_name}.{param_name} = {param_value}")
        except Exception as e:
            print(f"Error storing parameter: {e}")

    async def analyze_text(self, text: str, actions_text: str) -> Tuple[bool, List[str], str]:
        """
        Analiza un texto y determina si coincide con alguna acción definida, usando IA.
        
        Args:
            text (str): El texto a analizar
            actions_text (str): JSON con las acciones y sus URLs
            
        Returns:
            Tuple[bool, List[str], str]: (
                bool: True si tiene todos los parámetros, False si faltan,
                list: Lista de parámetros faltantes,
                str: URL final con parámetros reemplazada si está completa, vacía si no
            )
        """
        try:
            print(f"Analyzing text: {text}")
            print(f"Actions text: {actions_text}")
            
            # Convertir el texto de acciones a diccionario
            action = json.loads(actions_text)
            
            # Obtener el nombre y la URL de la acción
            action_name = action.get('name', '').lower()
            url_template = action.get('url', '')
            print(f"Action name: {action_name}")
            print(f"URL template: {url_template}")
            
            # Extraer los parámetros requeridos de la URL usando regex
            import re
            required_params = re.findall(r'\{(\w+)\}', url_template)
            print(f"Required parameters: {required_params}")
            
            # Analizar el texto con IA
            ai_result = await self.analyze_text_with_ai(text, actions_text)
            print(f"AI Analysis result: {ai_result}")
            
            # Si la IA no detectó la función, usar detección de patrones como fallback
            if not ai_result.get("matches_action", False):
                print("AI didn't detect function, trying pattern detection...")
                ai_result = self._detect_function_with_patterns(text, action_name, required_params)
                print(f"Pattern detection result: {ai_result}")
            
            # Si la IA o patrones detectaron que coincide con la función, procesar parámetros
            if ai_result.get("matches_action", False):
                # Extraer parámetros del resultado de IA o patrones
                extracted_params = ai_result.get("extracted_params", {})
                for param_name, param_value in extracted_params.items():
                    if param_value and param_value.strip():
                        self.store_parameter(action_name, param_name, param_value)
            
            # Verificar si tenemos todos los parámetros necesarios
            stored_action_params = self._stored_parameters.get(action_name, {})
            print(f"Stored parameters: {stored_action_params}")
            
            # Verificar qué parámetros faltan
            missing_params = [
                param for param in required_params 
                if param not in stored_action_params
            ]
            print(f"Missing parameters: {missing_params}")
            
            # Si la función coincide pero faltan parámetros
            if ai_result.get("matches_action", False) and missing_params:
                return False, missing_params, ""
            
            # Si tenemos todos los parámetros, construir la URL final
            if ai_result.get("matches_action", False) and not missing_params:
                final_url = url_template
                for param, value in stored_action_params.items():
                    final_url = final_url.replace(f'{{{param}}}', str(value))
                print(f"Final URL: {final_url}")
                return True, [], final_url
            
            # Si no coincide con la función
            return False, [], ""
            
        except json.JSONDecodeError:
            return False, [], ""
        except Exception as e:
            print(f"Error analyzing text: {str(e)}")
            return False, [], ""

    def _detect_function_with_patterns(self, text: str, action_name: str, required_params: List[str]) -> Dict[str, Any]:
        """
        Sistema de detección de patrones como fallback cuando la IA no funciona correctamente.
        Usa regex y palabras clave para detectar funciones y extraer parámetros.
        """
        import re
        
        text_lower = text.lower().strip()
        
        # Detectar si el texto solicita la función usando palabras clave
        matches_action = False
        
        # Palabras clave para diferentes tipos de funciones
        function_keywords = {
            'consultar_clima': ['clima', 'tiempo', 'temperatura', 'pronóstico', 'weather', 'lluvia', 'sol', 'nublado', 'frío', 'calor'],
            'noticias': ['noticias', 'news', 'actualidad', 'información'],
            'traducir': ['traducir', 'translate', 'idioma', 'language'],
            'cotizacion': ['precio', 'cotización', 'valor', 'costo', 'dólar', 'euro']
        }
        
        # Buscar palabras clave para la función específica
        keywords = function_keywords.get(action_name, [action_name])
        for keyword in keywords:
            if keyword in text_lower:
                matches_action = True
                print(f"Pattern detection: Found keyword '{keyword}' for function '{action_name}'")
                break
        
        # Extraer parámetros si la función coincide
        extracted_params = {}
        
        if matches_action and 'latitude' in required_params and 'longitude' in required_params:
            # Buscar coordenadas en diferentes formatos
            coord_patterns = [
                r'(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)',  # "lat, lon"
                r'latitud[:\s]*(-?\d+\.?\d*).*longitud[:\s]*(-?\d+\.?\d*)',  # "latitud: X longitud: Y"
                r'lat[:\s]*(-?\d+\.?\d*).*lon[:\s]*(-?\d+\.?\d*)',  # "lat: X lon: Y"
                r'coordenadas[:\s]*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)'  # "coordenadas: lat, lon"
            ]
            
            for pattern in coord_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    try:
                        lat, lon = match.groups()
                        lat_float = float(lat)
                        lon_float = float(lon)
                        
                        # Validar rangos de coordenadas
                        if -90 <= lat_float <= 90 and -180 <= lon_float <= 180:
                            extracted_params['latitude'] = str(lat_float)
                            extracted_params['longitude'] = str(lon_float)
                            print(f"Pattern detection: Extracted coordinates lat={lat_float}, lon={lon_float}")
                            break
                    except (ValueError, TypeError):
                        continue
        
        # Buscar ciudades conocidas si no hay coordenadas y la función coincide
        if matches_action and not extracted_params and 'latitude' in required_params:
            city_coords = {
                'madrid': {'latitude': '40.4168', 'longitude': '-3.7038'},
                'barcelona': {'latitude': '41.3851', 'longitude': '2.1734'},
                'valencia': {'latitude': '39.4699', 'longitude': '-0.3763'},
                'sevilla': {'latitude': '37.3891', 'longitude': '-5.9845'},
                'bilbao': {'latitude': '43.2627', 'longitude': '-2.9253'},
                'buenos aires': {'latitude': '-34.6132', 'longitude': '-58.3772'},
                'lima': {'latitude': '-12.0464', 'longitude': '-77.0428'},
                'bogotá': {'latitude': '4.7110', 'longitude': '-74.0721'},
                'santiago': {'latitude': '-33.4489', 'longitude': '-70.6693'},
                'méxico': {'latitude': '19.4326', 'longitude': '-99.1332'},
                'ciudad de méxico': {'latitude': '19.4326', 'longitude': '-99.1332'}
            }
            
            for city, coords in city_coords.items():
                if city in text_lower:
                    extracted_params.update(coords)
                    print(f"Pattern detection: Found city '{city}' with coordinates {coords}")
                    break
        
        confidence = 0.8 if matches_action and extracted_params else (0.6 if matches_action else 0.0)
        
        return {
            "matches_action": matches_action,
            "confidence": confidence,
            "extracted_params": extracted_params
        }

