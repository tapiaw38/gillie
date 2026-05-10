from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Request, status
from starlette.concurrency import run_in_threadpool

from src.core.platform.config.service import get_config_service
from src.core.platform.nosql.client import Client, MongoDBClient


router = APIRouter(
    prefix="/nosql",
    tags=["nosql"],
)


def insert_one_handler(client: Client, document: dict) -> dict:
    result = client.insert_one(document)
    return {"inserted_id": str(result.inserted_id)}


def ensure_debug_mode(request: Request) -> None:
    app_mode = str(getattr(request.app.state.config_service.server_config, "mode", "release"))
    if app_mode != "debug":
        raise HTTPException(status_code=403, detail="nosql endpoints are only available in debug mode")


def select_client(collection: str) -> Client:
    config = get_config_service().nosql_config
    if collection == "profiles":
        profiles = config.profiles
        return MongoDBClient(
            profiles.database_uri,
            profiles.database,
            profiles.collection,
        )
    if collection == "conversations":
        conversations = config.conversations
        return MongoDBClient(
            conversations.database_uri,
            conversations.database,
            conversations.collection,
        )
    raise ValueError("Colección no soportada: " + str(collection))


@router.post("/search", status_code=status.HTTP_200_OK)
async def search_documents(
    request: Request,
    body: dict = Body(...),
    skip: int = 0,
    limit: int = 10,
):
    ensure_debug_mode(request)
    collection = body.get("collection")
    filter = body.get("filter", {})
    client = select_client(collection)
    return await run_in_threadpool(
        lambda: [doc for doc in client.find(filter).skip(skip).limit(limit)]
    )


@router.post("/upsert", status_code=status.HTTP_200_OK)
async def upsert_document(
    request: Request,
    body: dict = Body(...),
):
    ensure_debug_mode(request)
    collection = body.get("collection")
    filter = body.get("filter", {})
    update = body.get("update", {})
    client = select_client(collection)
    result = await run_in_threadpool(client.update_one, filter, {"$set": update})
    if result.matched_count == 0:
        return await run_in_threadpool(insert_one_handler, client, update)
    return {"matched_count": result.matched_count, "modified_count": result.modified_count}


@router.post("/upsert-bulk", status_code=status.HTTP_200_OK)
async def upsert_bulk_documents(
    request: Request,
    body: dict = Body(...),
):
    ensure_debug_mode(request)
    collection = body.get("collection")
    documents = body.get("documents", [])
    client = select_client(collection)

    def _upsert_bulk() -> dict:
        inserted = []
        for doc in documents:
            result = client.update_one({"_id": doc.get("_id")}, {"$set": doc})
            if result.matched_count == 0:
                res = client.insert_one(doc)
                inserted.append(str(res.inserted_id))
        return {"inserted_ids": inserted}

    return await run_in_threadpool(_upsert_bulk)


@router.post("/delete", status_code=status.HTTP_200_OK)
async def delete_documents(
    request: Request,
    body: dict = Body(...),
):
    ensure_debug_mode(request)
    collection = body.get("collection")
    filter = body.get("filter", {})
    client = select_client(collection)
    result = await run_in_threadpool(client.delete_one, filter)
    return {"deleted_count": result.deleted_count}


@router.post("/count", status_code=status.HTTP_200_OK)
async def count_documents(
    request: Request,
    body: dict = Body(...),
):
    ensure_debug_mode(request)
    collection = body.get("collection")
    filter = body.get("filter", {})
    client = select_client(collection)
    count = await run_in_threadpool(client.get_collection().count_documents, filter)
    return {"count": count}


@router.post("/find-first", status_code=status.HTTP_200_OK)
async def find_first_document(
    request: Request,
    body: dict = Body(...),
):
    ensure_debug_mode(request)
    collection = body.get("collection")
    filter = body.get("filter", {})
    client = select_client(collection)
    doc = await run_in_threadpool(client.find_one, filter)
    return doc if doc else {}
