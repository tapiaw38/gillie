from fastapi import APIRouter, Depends, Body, HTTPException, status
from src.adapters.services.services import Services
from src.adapters.services.whatsapp.service import WhatsAppService
from src.adapters.services.profile.service import ProfileService
from typing import Dict, Any

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])

@router.post("/webhook")
async def whatsapp_webhook(
    payload: Dict[Any, Any] = Body(...),
    services: Services = Depends(Services.get_instance)
):
    """
    Webhook para recibir mensajes de WhatsApp
    """
    # Verificar si el payload es un mensaje o una verificación del webhook
    if payload.get("object") == "whatsapp_business_account":
        # Verificamos si hay un entry.changes
        if not payload.get("entry") or not payload.get("entry")[0].get("changes"):
            return {"status": "success", "message": "Payload no contiene cambios para procesar"}
            
        # Obtener el ID de negocio de WhatsApp del payload
        business_account_id = None
        try:
            business_account_id = payload["entry"][0]["changes"][0]["value"]["metadata"]["business_account_id"]
        except (KeyError, IndexError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="No se pudo obtener el business_account_id del payload"
            )
            
        # Buscar el perfil correspondiente con esta integración de WhatsApp activa
        profile = await services.profile.find_by_whatsapp_business_id(business_account_id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"No se encontró un perfil con el business_account_id: {business_account_id}"
            )
            
        # Crear el servicio de WhatsApp y procesar el mensaje
        whatsapp_service = WhatsAppService(services.conversation)
        result = await whatsapp_service.process_message(payload, profile)
        
        return result
        
    # Si el payload no es de tipo whatsapp_business_account, no lo procesamos
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, 
        detail="Payload no es de tipo whatsapp_business_account"
    )

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str, 
    hub_verify_token: str, 
    hub_challenge: str,
    services: Services = Depends(Services.get_instance)
):
    """
    Verificar el webhook para WhatsApp Cloud API
    """
    from src.core.platform.config.service import get_config_service
    
    # El token debe configurarse en la configuración y coincidir con el configurado en Facebook
    config_service = get_config_service()
    verify_token = config_service.whatsapp_config.verify_token
    
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        return int(hub_challenge)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Verificación fallida"
        )
