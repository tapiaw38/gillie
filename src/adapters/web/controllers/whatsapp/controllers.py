from fastapi import APIRouter, Depends, Body, HTTPException, status, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from src.adapters.services.services import Services
from src.adapters.services.whatsapp.service import WhatsAppService
from src.adapters.services.profile.service import ProfileService
from typing import Dict, Any, List, Deque
import logging
import os
import json
from collections import deque
from datetime import datetime

# Cola para almacenar los últimos payloads recibidos (hasta 10)
last_payloads = deque(maxlen=10)

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])

@router.get("/verify", response_class=PlainTextResponse)
async def verify_endpoint():
    """
    Endpoint simple para verificar que el servidor está funcionando y accesible.
    Útil para depurar problemas de conexión con el webhook.
    """
    logger = logging.getLogger(__name__)
    logger.info("Solicitud de verificación simple recibida")
    return "WhatsApp webhook server is running"
    

@router.post("/test-send")
async def test_send_message(
    phone_number: str = Body(..., embed=True),
    message: str = Body(..., embed=True),
    services: Services = Depends(Services.get_instance),
):
    """
    Endpoint para probar el envío de mensajes de WhatsApp
    """
    logger = logging.getLogger(__name__)
    try:
        logger.info(f"Solicitud de prueba de envío a {phone_number}: {message}")
        
        # Buscar un perfil con integración de WhatsApp activa
        profile = await services.profile.find_with_active_whatsapp_integration()
        
        if not profile:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "No se encontró perfil con integración de WhatsApp activa"}
            )
            
        # Encontrar la integración de WhatsApp
        whatsapp_integration = None
        for integration in profile.integrations:
            if integration.name == "whatsapp" and integration.activated:
                whatsapp_integration = integration
                break
                
        if not whatsapp_integration:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "No se encontró integración de WhatsApp activa en el perfil"}
            )
        
        # Inicializar el cliente de WhatsApp
        from src.adapters.web.integrations.whatsapp.whatsapp import WhatsAppIntegration
        
        wa_client = WhatsAppIntegration(
            access_token=whatsapp_integration.config["accessToken"],
            phone_number_id=whatsapp_integration.config["phoneNumberId"]
        )
        
        # Enviar mensaje
        result = wa_client.send_message(phone_number, message)
        
        return {
            "status": "success" if result else "error",
            "message": "Mensaje enviado correctamente" if result else "Error al enviar el mensaje",
            "phone_number": phone_number
        }
        
    except Exception as e:
        logger.error(f"Error al probar envío: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Error al enviar mensaje: {str(e)}"}
        )


@router.get("/debug")
async def debug_payloads():
    """
    Endpoint de depuración para ver los últimos payloads recibidos
    """
    logger = logging.getLogger(__name__)
    logger.info("Solicitud de depuración de payloads recibida")
    
    if not last_payloads:
        return {"message": "No hay payloads registrados"}
    
    # Convertir la cola a una lista para la respuesta
    payload_list = list(last_payloads)
    
    return {"count": len(payload_list), "payloads": payload_list}


@router.post("/webhook")
async def whatsapp_webhook(
    payload: Dict[Any, Any] = Body(...),
    services: Services = Depends(Services.get_instance),
):
    """
    Webhook para recibir mensajes de WhatsApp
    """
    logger = logging.getLogger(__name__)
    try:
        # Registrar el payload para depuración
        timestamp = datetime.now().isoformat()
        sanitized_payload = json.loads(json.dumps(payload))  # Crear copia segura
        last_payloads.append({
            "timestamp": timestamp,
            "payload": sanitized_payload
        })
        
        # Log del payload recibido (limitado para seguridad)
        logger.info(f"Webhook POST recibido - object: {payload.get('object')}")
        
        # Verificar si el payload es un mensaje de WhatsApp
        if payload.get("object") != "whatsapp_business_account":
            logger.warning(f"Payload incorrecto, objeto recibido: {payload.get('object')}")
            return JSONResponse(
                status_code=200,  # Devolver 200 aunque sea incorrecto para evitar reintento
                content={"status": "ignored", "message": "Payload no es de tipo whatsapp_business_account"}
            )
            
        # Verificamos si hay un entry.changes
        if not payload.get("entry") or not payload.get("entry")[0].get("changes"):
            logger.info("Payload no contiene cambios para procesar")
            return {"status": "success", "message": "Payload no contiene cambios para procesar"}
            
        # Obtener el ID de negocio de WhatsApp del payload
        business_account_id = None
        try:
            # Registrar la estructura del payload para depuración
            logger.debug(f"Estructura del payload: {payload}")
            
            # Intentar obtener el ID del negocio a través de diferentes rutas en el payload
            if "entry" in payload and len(payload["entry"]) > 0:
                entry = payload["entry"][0]
                logger.debug(f"Entry encontrado: {entry}")
                
                if "changes" in entry and len(entry["changes"]) > 0:
                    value = entry["changes"][0]["value"]
                    logger.debug(f"Value encontrado: {value}")
                    
                    # Intenta encontrar el business_account_id en diferentes ubicaciones
                    if "metadata" in value and "business_account_id" in value["metadata"]:
                        business_account_id = value["metadata"]["business_account_id"]
                    elif "metadata" in value and "phone_number_id" in value["metadata"]:
                        # Usar phone_number_id como alternativa si no hay business_account_id
                        business_account_id = value["metadata"]["phone_number_id"]
                    elif "phone_number_id" in value:
                        business_account_id = value["phone_number_id"]
            
            if not business_account_id and "phone_number_id" in payload:
                # Fallback si el business_account_id no está en la estructura esperada
                business_account_id = payload["phone_number_id"]
                
            # Si aún no se encuentra, buscar recursivamente en todo el payload
            if not business_account_id:
                def search_for_id(obj, keys=["business_account_id", "phone_number_id", "from_id"]):
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if key in keys and value:
                                return value
                            result = search_for_id(value, keys)
                            if result:
                                return result
                    elif isinstance(obj, list):
                        for item in obj:
                            result = search_for_id(item, keys)
                            if result:
                                return result
                    return None
                
                business_account_id = search_for_id(payload)
            
            if business_account_id:
                logger.info(f"Business Account ID extraído: {business_account_id}")
            else:
                # Si no se encuentra ningún ID, usar un valor predeterminado para depuración
                logger.warning("No se pudo encontrar un ID de negocio, usando 'default' para depuración")
                business_account_id = "default"
                
        except (KeyError, IndexError) as e:
            logger.error(f"Error al obtener business_account_id: {str(e)}")
            logger.debug(f"Estructura del payload: {payload}")
            # Continuar con un ID predeterminado para depuración en lugar de retornar error
            business_account_id = "default"
            logger.info("Usando business_account_id 'default' para depuración")
            
        # Buscar el perfil correspondiente con esta integración de WhatsApp activa
        try:
            # Si estamos usando el ID por defecto para depuración, intentar obtener cualquier perfil con integración WhatsApp
            if business_account_id == "default":
                logger.info("Buscando un perfil con cualquier integración de WhatsApp activa")
                profile = await services.profile.find_with_active_whatsapp_integration()
            else:
                profile = await services.profile.find_by_whatsapp_business_id(business_account_id)
            
            if not profile:
                # Si no se encuentra el perfil con el ID específico, intentar encontrar cualquier perfil con WhatsApp
                if business_account_id != "default":
                    logger.warning(f"No se encontró un perfil con el business_account_id: {business_account_id}, buscando perfiles con WhatsApp activo")
                    profile = await services.profile.find_with_active_whatsapp_integration()
                
                if not profile:
                    logger.warning("No se encontró ningún perfil con integración de WhatsApp activa")
                    return JSONResponse(
                        status_code=200,  # Devolver 200 aunque no se encuentre para evitar reintento
                        content={"status": "error", "message": "No se encontró ningún perfil con integración de WhatsApp activa"}
                    )
                
            logger.info(f"Perfil encontrado para business_account_id {business_account_id}: {profile.id}")
                
            # Crear el servicio de WhatsApp y procesar el mensaje
            whatsapp_service = WhatsAppService(services.conversation)
            result = await whatsapp_service.process_message(payload, profile)
            
            logger.info(f"Mensaje procesado exitosamente: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error al buscar perfil o procesar mensaje: {str(e)}", exc_info=True)
            # Siempre devolver 200 para WhatsApp aunque haya error
            return JSONResponse(
                status_code=200,
                content={"status": "error", "message": f"Error al procesar el mensaje: {str(e)}"}
            )
            
    except Exception as e:
        logger.error(f"Error no manejado en webhook: {str(e)}", exc_info=True)
        # Siempre devolver 200 para WhatsApp aunque haya error
        return JSONResponse(
            status_code=200,
            content={"status": "error", "message": f"Error general: {str(e)}"}
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
