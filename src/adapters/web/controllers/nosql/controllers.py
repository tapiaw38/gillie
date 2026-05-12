import os

from fastapi import APIRouter, Body, HTTPException, Request, status

from src.core.platform.nosql.client import MongoDBClient


router = APIRouter(
    prefix="/nosql",
    tags=["nosql"],
)


def ensure_debug_mode(request: Request) -> None:
    app_mode = str(getattr(request.app.state.config_service.server_config, "mode", "release"))
    if app_mode != "debug":
        raise HTTPException(status_code=403, detail="nosql endpoints are only available in debug mode")
    if os.getenv("ENABLE_NOSQL_DEBUG_ENDPOINTS", "").lower() != "true":
        raise HTTPException(
            status_code=403,
            detail="nosql endpoints require ENABLE_NOSQL_DEBUG_ENDPOINTS=true",
        )


def select_client(request: Request, collection: str) -> MongoDBClient:
    config = request.app.state.config_service.nosql_config
    if collection == "profiles":
        c = config.profiles
        return MongoDBClient(c.database_uri, c.database, c.collection)
    if collection == "conversations":
        c = config.conversations
        return MongoDBClient(c.database_uri, c.database, c.collection)
    raise ValueError("Colección no soportada: " + str(collection))


@router.post("/search", status_code=status.HTTP_200_OK)
async def search_documents(
    request: Request,
    body: dict = Body(...),
    skip: int = 0,
    limit: int = 10,
):
    ensure_debug_mode(request)
    client = select_client(request, body.get("collection"))
    try:
        cursor = client.find(body.get("filter", {})).skip(skip).limit(limit)
        return [doc async for doc in cursor]
    finally:
        await client.disconnect()


@router.post("/upsert", status_code=status.HTTP_200_OK)
async def upsert_document(
    request: Request,
    body: dict = Body(...),
):
    ensure_debug_mode(request)
    client = select_client(request, body.get("collection"))
    try:
        filter = body.get("filter", {})
        update = body.get("update", {})
        result = await client.update_one(filter, {"$set": update})
        if result.matched_count == 0:
            res = await client.insert_one(update)
            return {"inserted_id": str(res.inserted_id)}
        return {"matched_count": result.matched_count, "modified_count": result.modified_count}
    finally:
        await client.disconnect()


@router.post("/upsert-bulk", status_code=status.HTTP_200_OK)
async def upsert_bulk_documents(
    request: Request,
    body: dict = Body(...),
):
    ensure_debug_mode(request)
    client = select_client(request, body.get("collection"))
    try:
        documents = body.get("documents", [])
        inserted = []
        for doc in documents:
            result = await client.update_one({"_id": doc.get("_id")}, {"$set": doc})
            if result.matched_count == 0:
                res = await client.insert_one(doc)
                inserted.append(str(res.inserted_id))
        return {"inserted_ids": inserted}
    finally:
        await client.disconnect()


@router.post("/delete", status_code=status.HTTP_200_OK)
async def delete_documents(
    request: Request,
    body: dict = Body(...),
):
    ensure_debug_mode(request)
    client = select_client(request, body.get("collection"))
    try:
        result = await client.delete_one(body.get("filter", {}))
        return {"deleted_count": result.deleted_count}
    finally:
        await client.disconnect()


@router.post("/count", status_code=status.HTTP_200_OK)
async def count_documents(
    request: Request,
    body: dict = Body(...),
):
    ensure_debug_mode(request)
    client = select_client(request, body.get("collection"))
    try:
        count = await client.get_collection().count_documents(body.get("filter", {}))
        return {"count": count}
    finally:
        await client.disconnect()


@router.post("/find-first", status_code=status.HTTP_200_OK)
async def find_first_document(
    request: Request,
    body: dict = Body(...),
):
    ensure_debug_mode(request)
    client = select_client(request, body.get("collection"))
    try:
        doc = await client.find_one(body.get("filter", {}))
        return doc if doc else {}
    finally:
        await client.disconnect()
