from fastapi import APIRouter, status, Request, Depends
from typing import Optional
from starlette.concurrency import run_in_threadpool
from src.schemas.memory import (
    FAQInput,
    FAQUpdate,
    FAQData,
    FAQListOutput,
    FAQOutput,
    SkillListOutput,
    SkillData,
    SkillContentOutput,
    GeneralMemoryOutput,
    ExtractMemoryOutput,
    MemoryRootOutput,
    MemoryRootInput,
    MemoryResolvedOutput,
    OwnerMemoryData,
    OwnerMemoryListOutput,
)
from src.core.use_cases.use_cases import Usecases
from src.adapters.web.dependencies import get_usecases

router = APIRouter(
    prefix="/api/v1/memory",
    tags=["Memory"],
)


@router.get("/faqs", status_code=status.HTTP_200_OK)
async def list_faqs(request: Request, usecases: Usecases = Depends(get_usecases)):
    """List all FAQs from faqs.skill.md."""
    faqs = await run_in_threadpool(usecases.memory.get_faqs_usecase.execute)
    return FAQListOutput(data=[FAQData(**f) for f in faqs])


@router.post("/faqs", status_code=status.HTTP_201_CREATED)
async def add_faq(body: FAQInput, request: Request, usecases: Usecases = Depends(get_usecases)):
    """Append a new FAQ to faqs.skill.md."""
    result = await run_in_threadpool(
        usecases.memory.add_faq_usecase.execute,
        body.question,
        body.answer,
        body.category,
    )
    return FAQOutput(data=FAQData(**result))


@router.put("/faqs/{faq_id}", status_code=status.HTTP_200_OK)
async def update_faq(faq_id: str, body: FAQUpdate, request: Request, usecases: Usecases = Depends(get_usecases)):
    """Update an existing FAQ in faqs.skill.md."""
    result = await run_in_threadpool(
        usecases.memory.update_faq_usecase.execute,
        faq_id,
        body.question,
        body.answer,
        body.category,
    )
    return FAQOutput(data=FAQData(**result))


@router.delete("/faqs/{faq_id}", status_code=status.HTTP_200_OK)
async def delete_faq(faq_id: str, request: Request, usecases: Usecases = Depends(get_usecases)):
    """Delete a FAQ from faqs.skill.md."""
    result = await run_in_threadpool(usecases.memory.delete_faq_usecase.execute, faq_id)
    return result


@router.get("", status_code=status.HTTP_200_OK)
async def get_resolved_memory(request: Request, usecases: Usecases = Depends(get_usecases)):
    """Return memory.md with all skill references inlined."""
    skill_manager = usecases.memory.get_skills_usecase.context_factory().platform_managers.skill_manager
    content = await run_in_threadpool(skill_manager.get_resolved_memory)
    return MemoryResolvedOutput(content=content)


@router.get("/root", status_code=status.HTTP_200_OK)
async def get_memory_root(request: Request, usecases: Usecases = Depends(get_usecases)):
    """Return raw content of memory.md."""
    skill_manager = usecases.memory.get_skills_usecase.context_factory().platform_managers.skill_manager
    content = await run_in_threadpool(skill_manager.get_memory_root)
    return MemoryRootOutput(content=content)


@router.put("/root", status_code=status.HTTP_200_OK)
async def update_memory_root(body: MemoryRootInput, request: Request, usecases: Usecases = Depends(get_usecases)):
    """Overwrite memory.md with new content."""
    skill_manager = usecases.memory.get_skills_usecase.context_factory().platform_managers.skill_manager
    await run_in_threadpool(skill_manager.update_memory_root, body.content)
    return MemoryRootOutput(content=body.content)


@router.get("/general", status_code=status.HTTP_200_OK)
async def get_general_memory(request: Request, usecases: Usecases = Depends(get_usecases)):
    """Return content of general.skill.md."""
    skill_manager = usecases.memory.get_skills_usecase.context_factory().platform_managers.skill_manager
    content = await run_in_threadpool(skill_manager.get_general_memory)
    return GeneralMemoryOutput(content=content)


@router.get("/skills", status_code=status.HTTP_200_OK)
async def list_skills(request: Request, usecases: Usecases = Depends(get_usecases)):
    """List all available .skill.md files."""
    names = await run_in_threadpool(usecases.memory.get_skills_usecase.execute)
    return SkillListOutput(data=[SkillData(name=n) for n in names])


@router.get("/skills/{name}", status_code=status.HTTP_200_OK)
async def get_skill(name: str, request: Request, usecases: Usecases = Depends(get_usecases)):
    """Return content of a specific skill."""
    content = await run_in_threadpool(usecases.memory.get_skills_usecase.get_skill, name)
    return SkillContentOutput(name=name, content=content)


# ─── Memory extraction ────────────────────────────────────────────────────────

@router.post("/extract", status_code=status.HTTP_200_OK)
async def extract_memory(request: Request, usecases: Usecases = Depends(get_usecases)):
    """Run legacy conversation summarization for unextracted conversations."""
    user_id = request.state.user.get("user_id")
    result = await usecases.memory.extract_memory_usecase.execute(user_id)
    return ExtractMemoryOutput(**result)


@router.get("/owner/episodes", status_code=status.HTTP_200_OK)
async def list_owner_episodes(
    request: Request,
    contact_id: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    usecases: Usecases = Depends(get_usecases),
):
    owner_user_id = request.state.user.get("user_id")
    result = await usecases.memory.list_owner_memories_usecase.execute(
        owner_user_id=owner_user_id,
        contact_id=contact_id,
        query=query,
        limit=limit,
        offset=offset,
    )
    episodes = result.get("items", [])
    return OwnerMemoryListOutput(
        data=[
            OwnerMemoryData(
                id=item.id or "",
                owner_user_id=getattr(item, "owner_user_id", None),
                memory_scope_id=getattr(item, "memory_scope_id", None),
                source_conversation_id=item.source_conversation_id,
                content=item.content,
                importance=item.importance,
                emotion=item.emotion,
                tags=item.tags or [],
                created_at=item.created_at,
            )
            for item in episodes
        ],
        has_more=bool(result.get("has_more", False)),
        next_offset=result.get("next_offset"),
    )
