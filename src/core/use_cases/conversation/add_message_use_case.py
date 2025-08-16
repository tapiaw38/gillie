import logging
from src.schemas.schemas import MessageInput, MessageListOutput
from src.core.domain.model import Message, SenderEnum
from datetime import datetime, timezone
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory
from src.adapters.web.utils.image_formatter import format_images_for_chat_response
from typing import Optional
from src.core.platform.functions.http_functions import HTTPFunction, HTTPFunctionParams

# Set up logger
logger = logging.getLogger(__name__)

# Module-level constants
IMAGE_CONFIDENCE_THRESHOLD = 0.3
MAX_IMAGES_TO_SHOW = 3
ENABLE_FAST_IMAGE_PROCESSING = True


class AddMessageUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def convert_messages_to_string(self, messages: list[Message]) -> str:
        """
        Converts a list of Message objects to a single string for context.
        """
        message_objects = [
            f"{message.sender}: {message.content}" for message in messages
        ]
        return " - ".join(message_objects)

    async def _get_spanish_female_voice_id(self) -> Optional[int]:
        """
        Searches for a female Spanish voice among the available voices.
        Returns the voice ID or None if a suitable one is not found.
        Improved error handling to avoid configuration issues.
        """
        try:
            voices = await self.context_factory.integrations.tts.get_available_voices()
            logger.info(f"Voices found: {len(voices)}")

            if not voices:
                logger.warning("No available voices found")
                return None

            for i, voice in enumerate(voices):
                logger.info(
                    f"Voice {i}: {voice.get('name', 'No name')} - Gender: {voice.get('gender', 'Unknown')} - Languages: {voice.get('languages', [])}"
                )

            for voice in voices:
                voice_name = voice.get("name", "").lower()
                languages = voice.get("languages", [])
                gender = voice.get("gender", "").lower()

                spanish_indicators = [
                    "spanish",
                    "español",
                    "es_",
                    "es-",
                    "helena",
                    "sabina",
                    "monica",
                    "paloma",
                    "carmen",
                ]
                female_indicators = ["female", "mujer", "femenina", "woman"]

                is_spanish = any(
                    indicator in voice_name for indicator in spanish_indicators
                ) or any("es" in str(lang).lower() for lang in languages if lang)
                is_female = gender in ["female", "mujer"] or any(
                    indicator in voice_name for indicator in female_indicators
                )

                if is_spanish and is_female:
                    logger.info(f"Voice found: {voice['name']} (ID: {voice['id']}) - ")
                    return voice["id"]

            logger.info("Not found a specific voice, searching")
            for voice in voices:
                gender = voice.get("gender", "").lower()
                if gender in ["female", "mujer"]:
                    logger.info(
                        f"Female voice found: {voice['name']} (ID: {voice['id']}"
                    )
                    return voice["id"]

            logger.warning(
                "Not found a voice that matches the criteria, using default system voice."
            )
            return None

        except Exception as e:
            logger.error(f"Error while fetching voices: {e}")
            return None  # Use default voice if there's an error

    async def _upload_audio_to_s3(
        self, audio_data: bytes, user_id: str, conversation_id: str
    ) -> str:
        """
        Uploads audio data to S3 and returns the public URL.
        """
        try:
            import io
            from datetime import datetime

            # Create a BytesIO object from the audio data
            audio_file = io.BytesIO(audio_data)

            # Generate a unique filename using message ID and timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tts_audio_{conversation_id}_{timestamp}.wav"

            s3_key = self.context_factory.store_service.put_object(
                file=audio_file,
                user_file=user_id,
                filename=filename,
                size=len(audio_data),
                object_id=conversation_id,
            )

            audio_url = self.context_factory.store_service.generate_url(s3_key)

            return audio_url

        except Exception as e:
            logger.error(f"Error uploading audio to S3: {e}")
            raise e

    async def execute(
        self,
        conversation_id: str,
        message: MessageInput,
        sender: SenderEnum,
        user_id: str,
        has_image_processor: Optional[str] = None,
        has_text_to_voice: Optional[str] = None,
    ) -> list[Message]:
        """
        Adds a message to a conversation and processes image extraction if enabled.
        If image processing is activated, first asks OpenAI for the keyword to search in images,
        then uses that keyword for image search instead of the original message content.
        Also processes voice_content if provided to enhance the message content.
        """
        # Process voice_content if provided
        enhanced_content = message.content
        voice_transcription = ""

        if message.voice_content:
            try:
                logger.info("Processing voice context...")

                # Read the audio file content
                audio_content = await message.voice_content.read()

                # Use STT integration to transcribe the audio
                stt_result = await self.context_factory.integrations.stt.audio_bytes_to_text(
                    audio_bytes=audio_content,
                    audio_format=(
                        message.voice_content.filename.split(".")[-1]
                        if message.voice_content.filename
                        else "wav"
                    ),
                    settings={
                        "language": "es-ES",  # Default to Spanish
                        "model": "base",  # Use base model for balance of speed/accuracy
                    },
                )

                if (
                    stt_result.get("success", False)
                    and stt_result.get("text", "").strip()
                ):
                    voice_transcription = stt_result["text"].strip()
                    logger.info(
                        f"Voice transcription successful: '{voice_transcription[:100]}...'"
                    )

                    # Enhance the message content with voice context
                    if voice_transcription:
                        print(f"Voice transcription: {voice_transcription}")
                        enhanced_content = f"{message.content}\n\n[Contexto de voz]: {voice_transcription}"
                else:
                    logger.warning(
                        f"Voice transcription failed: {stt_result.get('error', 'Unknown error')}"
                    )

            except Exception as e:
                logger.error(f"Error processing voice context: {e}")
                # Continue with original content if voice processing fails

        new_message = Message(
            content=enhanced_content,
            sender=sender,
            created_at=datetime.now(timezone.utc),
        )

        try:
            search_conversation = (
                self.context_factory.repositories.conversation.find_by_id(
                    conversation_id
                )
            )
            if not search_conversation:
                logger.error("Conversation not found")
                raise Exception("Conversation not found")

            if user_id != search_conversation.profile.user_id:
                logger.error("User not authorized to add message")
                raise Exception("User not authorized to add message")

            if (
                not hasattr(search_conversation, "messages")
                or search_conversation.messages is None
            ):
                search_conversation.messages = []

            if any(msg.id == new_message.id for msg in search_conversation.messages):
                logger.error(
                    "Message with the same ID already exists in the conversation"
                )
                raise Exception(
                    "Message with the same ID already exists in the conversation"
                )

            search_conversation.messages.append(new_message)

            # Verificar si hay funciones configuradas
            response = ""
            if search_conversation.profile.functions:
                try:
                    # Analizar el mensaje con IA para determinar si coincide con alguna función
                    can_execute, missing_params, complete_url = await self.context_factory.integrations.openai.analyze_text(
                        new_message.content,
                        search_conversation.profile.functions
                    )

                    if can_execute and complete_url:
                        try:
                            # Ejecutar la función HTTP
                            http_params = HTTPFunctionParams(
                                name=["execute_function"],
                                url=[complete_url],
                                method="GET",
                            )
                            http_function = HTTPFunction(http_params)
                            result = await http_function.execute()

                            # Formatear el resultado de manera amigable
                            format_prompt = f"""
                            Actúa como {search_conversation.profile.assistant_name} y convierte esta respuesta técnica en un mensaje amigable:
                            
                            Datos: {result}
                            
                            Reglas:
                            1. Usa un tono conversacional y amigable
                            2. Incluye emojis apropiados
                            3. Explica los datos de manera clara y simple
                            4. Si hay temperaturas, menciona si hace frío o calor
                            5. Si hay viento, describe si es suave o fuerte
                            6. Si hay datos de ubicación, menciona la ciudad o región
                            7. Adapta la respuesta al tipo de servicio consultado
                            """

                            formatted_response = await self.context_factory.integrations.openai.ask(
                                format_prompt,
                                "",
                                "",
                                search_conversation.profile,
                            )
                            
                            # Agregar la URL utilizada al final de la respuesta
                            response = f"{formatted_response}\n\n🔗 **URL consultada:** `{complete_url}`"

                        except Exception as e:
                            logger.error(f"Error executing function: {e}")
                            response = f"¡Ups! 😅 Lo siento, tuve un pequeño problema al consultar la información. ¿Podrías intentarlo de nuevo?"
                    
                    elif missing_params:
                        # Generar mensaje amigable pidiendo los parámetros faltantes
                        missing_params_text = ", ".join(missing_params)
                        
                        parameters_prompt = f"""
                        Actúa como {search_conversation.profile.assistant_name} y ayuda al usuario a proporcionar los parámetros faltantes.
                        
                        Mensaje del usuario: "{new_message.content}"
                        Parámetros necesarios: {missing_params_text}
                        
                        Instrucciones:
                        1. Explica de manera amigable qué información necesitas
                        2. Da ejemplos específicos de cómo proporcionar cada parámetro
                        3. Si son coordenadas, menciona formatos como "40.4168, -3.7038" o nombres de ciudades
                        4. Usa emojis apropiados
                        5. Mantén un tono conversacional y útil
                        
                        Responde solo con el mensaje para el usuario.
                        """
                        
                        response = await self.context_factory.integrations.openai.ask(
                            parameters_prompt,
                            message.context,
                            self.convert_messages_to_string(search_conversation.messages),
                            search_conversation.profile,
                        )
                    
                    else:
                        # El mensaje no está relacionado con funciones, respuesta normal
                        response = await self.context_factory.integrations.openai.ask(
                            new_message.content,
                            message.context,
                            self.convert_messages_to_string(search_conversation.messages),
                            search_conversation.profile,
                        )

                except Exception as analyze_error:
                        logger.error(f"Error in analyze_text (likely AI service issue): {analyze_error}")
                        # Si analyze_text falla, intentar respuesta normal con timeout más corto
                        try:
                            response = await self.context_factory.integrations.openai.ask(
                                new_message.content,
                                message.context,
                                self.convert_messages_to_string(search_conversation.messages),
                                search_conversation.profile,
                            )
                        except Exception as fallback_error:
                            logger.error(f"Error in fallback AI response: {fallback_error}")
                            # Si todo falla, dar una respuesta genérica
                            response = f"¡Hola! Soy {search_conversation.profile.assistant_name} 😊 Disculpa, estoy teniendo algunos problemas técnicos en este momento. ¿Podrías intentarlo de nuevo en unos minutos?"

                except Exception as e:
                    logger.error(f"Error in function processing: {e}")
                    # Si hay error en el procesamiento de funciones, intentar respuesta normal
                    try:
                        response = await self.context_factory.integrations.openai.ask(
                            new_message.content,
                            message.context,
                            self.convert_messages_to_string(search_conversation.messages),
                            search_conversation.profile,
                        )
                    except Exception as final_error:
                        logger.error(f"Error in final fallback AI response: {final_error}")
                        # Respuesta genérica si todo falla
                        response = f"¡Hola! Soy {search_conversation.profile.assistant_name} 😊 Disculpa, estoy teniendo algunos problemas técnicos en este momento. ¿Podrías intentarlo de nuevo en unos minutos?"
            else:
                # Respuesta normal si no hay funciones configuradas
                try:
                    response = await self.context_factory.integrations.openai.ask(
                        new_message.content,
                        message.context,
                        self.convert_messages_to_string(search_conversation.messages),
                        search_conversation.profile,
                    )
                except Exception as no_functions_error:
                    logger.error(f"Error in normal AI response (no functions): {no_functions_error}")
                    # Respuesta genérica si la IA falla completamente
                    response = f"¡Hola! Soy {search_conversation.profile.assistant_name} 😊 Disculpa, estoy teniendo algunos problemas técnicos en este momento. ¿Podrías intentarlo de nuevo en unos minutos?"

            file_images = []
            formatted_images_list = []
            image_search_keyword = new_message.content

            if has_image_processor == "activate":
                # Ask OpenAI for the keyword to search in images
                logger.info("Requesting image search keyword from OpenAI...")
                keyword_prompt = (
                    "Given the following user message, what is the best single keyword or phrase to use to search for relevant images in the user's files? "
                    "Respond ONLY with the keyword or phrase, no explanation.\n\n"
                    f"User message: {new_message.content}"
                )
                image_search_keyword = (
                    await self.context_factory.integrations.openai.ask(
                        keyword_prompt,
                        message.context,
                        self.convert_messages_to_string(search_conversation.messages),
                        search_conversation.profile,
                    )
                )
                logger.info(f"Image search keyword received: '{image_search_keyword}'")

                # Use optimized image search with reduced API calls
                if ENABLE_FAST_IMAGE_PROCESSING:
                    logger.info("Using optimized fast image processing mode")
                    # Limit to fewer results to reduce processing time
                    max_results_for_search = min(MAX_IMAGES_TO_SHOW, 2)
                else:
                    max_results_for_search = MAX_IMAGES_TO_SHOW

                file_images = await self.context_factory.integrations.openai.search_images_in_files(
                    image_search_keyword,
                    search_conversation.profile,
                    max_results_for_search,
                )

                logger.info(f"File images found: {len(file_images)}")

                # Filter by confidence threshold
                file_images = [
                    img
                    for img in file_images
                    if getattr(img, "confidence", 1.0) >= IMAGE_CONFIDENCE_THRESHOLD
                ]

                if file_images:
                    formatted_images = format_images_for_chat_response(
                        file_images,
                        image_search_keyword,
                        max_images_to_show=MAX_IMAGES_TO_SHOW,
                    )
                    formatted_images_list.append(formatted_images)

            audio_url = None
            if has_text_to_voice == "activate":
                try:
                    logger.info("Generating audio response...")

                    tts_settings = {
                        "rate": 150,  # Moderate speed
                        "volume": 0.8,  # High volume
                        # DO NOT include voice_id to avoid configuration errors
                    }

                    audio_data = await self.context_factory.integrations.tts.text_to_speech_stream(
                        text=response, settings=tts_settings
                    )

                    audio_url = await self._upload_audio_to_s3(
                        audio_data, user_id, conversation_id
                    )

                except Exception as e:
                    logger.error(f"Error generating audio: {e}")
                    raise Exception(f"Error generating audio: {e}")

            response_message = Message(
                content=response,
                audio_url=audio_url,
                sender="assistant",
                created_at=datetime.now(timezone.utc),
            )

            search_conversation.messages.append(response_message)

            self.context_factory.repositories.conversation.update_messages_by_id(
                conversation_id,
                search_conversation.messages,
            )

            response_with_images = response
            if has_image_processor == "activate" and formatted_images_list:
                formatted_images = "\n".join(formatted_images_list)
                if formatted_images:
                    response_with_images += f"\n\n{formatted_images}"
                    response_message.content = response_with_images
                    search_conversation.messages[-1] = response_message

            return MessageListOutput.from_output(search_conversation.messages)

        except PyMongoError as e:
            logger.error(f"Error interacting with the database: {e}")
            raise Exception(f"Error interacting with the database: {e}")

        except Exception as e:
            logger.error(f"Error executing AddMessageUseCase: {e}")
            raise Exception(f"Error executing AddMessageUseCase: {e}")