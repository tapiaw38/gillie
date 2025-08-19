from fastapi import APIRouter, Depends, Body, HTTPException, status, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from src.adapters.services.services import Services
from src.adapters.services.whatsapp.service import WhatsAppService
from src.adapters.services.profile.service import ProfileService
from typing import Dict, Any
import logging
import os

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])


@router.post("/webhook")
async def whatsapp_webhook(
    payload: Dict[Any, Any] = Body(...),
    services: Services = Depends(Services.get_instance),
):
    """
    Webhook para recibir mensajes de WhatsApp
    """
    if payload.get("object") == "whatsapp_business_account":
        # Verificamos si hay un entry.changes
        if not payload.get("entry") or not payload.get("entry")[0].get("changes"):
            return {
                "status": "success",
                "message": "Payload no contiene cambios para procesar",
            }

        # Obtener el ID de negocio de WhatsApp del payload
        business_account_id = None
        try:
            business_account_id = payload["entry"][0]["changes"][0]["value"][
                "metadata"
            ]["business_account_id"]
        except (KeyError, IndexError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo obtener el business_account_id del payload",
            )

        # Buscar el perfil correspondiente con esta integración de WhatsApp activa
        profile = await services.profile.find_by_whatsapp_business_id(
            business_account_id
        )

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró un perfil con el business_account_id: {business_account_id}",
            )

        # Crear el servicio de WhatsApp y procesar el mensaje
        whatsapp_service = WhatsAppService(services.conversation)
        result = await whatsapp_service.process_message(payload, profile)

        return result

    # Si el payload no es de tipo whatsapp_business_account, no lo procesamos
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Payload no es de tipo whatsapp_business_account",
    )


@router.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    """
    Verificar el webhook para WhatsApp Cloud API
    Esta función maneja la verificación del webhook cuando WhatsApp intenta validar tu endpoint.
    WhatsApp envía parámetros con formato hub.mode, hub.verify_token y hub.challenge
    """
    logger = logging.getLogger(__name__)
    
    # Obtener los parámetros directamente de la URL original
    url = str(request.url)
    logger.info(f"URL completa recibida: {url}")
    
    # Extraer los parámetros manualmente ya que FastAPI no maneja bien los parámetros con punto
    import re
    
    # Extraer los parámetros con expresiones regulares
    mode_match = re.search(r'hub\.mode=([^&]+)', url)
    token_match = re.search(r'hub\.verify_token=([^&]+)', url)
    challenge_match = re.search(r'hub\.challenge=([^&]+)', url)
    
    hub_mode = mode_match.group(1) if mode_match else None
    hub_verify_token = token_match.group(1) if token_match else None
    hub_challenge = challenge_match.group(1) if challenge_match else None
    
    # Log para ayudar a depurar
    logger.info(f"Solicitud de verificación de webhook recibida: mode={hub_mode}, token={hub_verify_token}, challenge={hub_challenge}")
    
    # Verificar que se recibieron todos los parámetros necesarios
    if not hub_mode or not hub_verify_token or not hub_challenge:
        logger.error("Faltan parámetros en la solicitud de verificación")
        return f"Faltan parámetros de verificación: mode={hub_mode}, token={hub_verify_token}, challenge={hub_challenge}"
    
    # Obtener el token directamente desde las variables de entorno para simplificar
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "assistant_ia_whatsapp_verification_token")
    logger.info(f"Token de verificación configurado: {verify_token}")
    
    # Verificar el token
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info(f"Verificación exitosa, devolviendo challenge: {hub_challenge}")
        # Devolver el challenge como texto plano
        try:
            # Convertir a entero si es posible
            challenge_int = int(hub_challenge)
            return PlainTextResponse(content=str(challenge_int))
        except (TypeError, ValueError):
            logger.error(f"Error al convertir challenge a entero: {hub_challenge}")
            return PlainTextResponse(content=hub_challenge)
    else:
        logger.error(f"Verificación fallida: token recibido '{hub_verify_token}' no coincide con token esperado '{verify_token}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=f"Verificación fallida: Token recibido no coincide con el esperado."
        )
