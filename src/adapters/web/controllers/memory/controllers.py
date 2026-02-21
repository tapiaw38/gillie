from fastapi import APIRouter, status, Request
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
)
from src.core.use_cases.use_cases import Usecases

router = APIRouter(
    prefix="/api/v1/memory",
    tags=["Memory"],
)

_usecases_instance = None


def set_usecases(usecases: Usecases):
    global _usecases_instance
    _usecases_instance = usecases


def get_usecases() -> Usecases:
    if _usecases_instance is None:
        raise Exception("Usecases not initialized. Call set_usecases first.")
    return _usecases_instance


# ─── FAQs ─────────────────────────────────────────────────────────────────────

@router.get("/faqs", status_code=status.HTTP_200_OK)
def list_faqs(request: Request):
    """List all FAQs from faqs.skill.md."""
    usecases = get_usecases()
    faqs = usecases.memory.get_faqs_usecase.execute()
    return FAQListOutput(data=[FAQData(**f) for f in faqs])


@router.post("/faqs", status_code=status.HTTP_201_CREATED)
def add_faq(body: FAQInput, request: Request):
    """Append a new FAQ to faqs.skill.md."""
    usecases = get_usecases()
    result = usecases.memory.add_faq_usecase.execute(body.question, body.answer, body.category)
    return FAQOutput(data=FAQData(**result))


@router.put("/faqs/{faq_id}", status_code=status.HTTP_200_OK)
def update_faq(faq_id: str, body: FAQUpdate, request: Request):
    """Update an existing FAQ in faqs.skill.md."""
    usecases = get_usecases()
    result = usecases.memory.update_faq_usecase.execute(faq_id, body.question, body.answer, body.category)
    return FAQOutput(data=FAQData(**result))


@router.delete("/faqs/{faq_id}", status_code=status.HTTP_200_OK)
def delete_faq(faq_id: str, request: Request):
    """Delete a FAQ from faqs.skill.md."""
    usecases = get_usecases()
    result = usecases.memory.delete_faq_usecase.execute(faq_id)
    return result


# ─── Memory root (memory.md) ──────────────────────────────────────────────────

@router.get("", status_code=status.HTTP_200_OK)
def get_resolved_memory(request: Request):
    """Return memory.md with all skill references inlined."""
    usecases = get_usecases()
    skill_manager = usecases.memory.get_skills_usecase.context_factory().platform_managers.skill_manager
    content = skill_manager.get_resolved_memory()
    return MemoryResolvedOutput(content=content)


@router.get("/root", status_code=status.HTTP_200_OK)
def get_memory_root(request: Request):
    """Return raw content of memory.md."""
    usecases = get_usecases()
    skill_manager = usecases.memory.get_skills_usecase.context_factory().platform_managers.skill_manager
    content = skill_manager.get_memory_root()
    return MemoryRootOutput(content=content)


@router.put("/root", status_code=status.HTTP_200_OK)
def update_memory_root(body: MemoryRootInput, request: Request):
    """Overwrite memory.md with new content."""
    usecases = get_usecases()
    skill_manager = usecases.memory.get_skills_usecase.context_factory().platform_managers.skill_manager
    skill_manager.update_memory_root(body.content)
    return MemoryRootOutput(content=body.content)


# ─── General memory ───────────────────────────────────────────────────────────

@router.get("/general", status_code=status.HTTP_200_OK)
def get_general_memory(request: Request):
    """Return content of general.skill.md."""
    usecases = get_usecases()
    skill_manager = usecases.memory.get_skills_usecase.context_factory().platform_managers.skill_manager
    content = skill_manager.get_general_memory()
    return GeneralMemoryOutput(content=content)


# ─── Skills ───────────────────────────────────────────────────────────────────

@router.get("/skills", status_code=status.HTTP_200_OK)
def list_skills(request: Request):
    """List all available .skill.md files."""
    usecases = get_usecases()
    names = usecases.memory.get_skills_usecase.execute()
    return SkillListOutput(data=[SkillData(name=n) for n in names])


@router.get("/skills/{name}", status_code=status.HTTP_200_OK)
def get_skill(name: str, request: Request):
    """Return content of a specific skill."""
    usecases = get_usecases()
    content = usecases.memory.get_skills_usecase.get_skill(name)
    return SkillContentOutput(name=name, content=content)


# ─── Memory extraction ────────────────────────────────────────────────────────

@router.post("/extract", status_code=status.HTTP_200_OK)
async def extract_memory(request: Request):
    """Run memory extraction job: summarize unextracted conversations → update general.skill.md."""
    usecases = get_usecases()
    user_id = request.state.user.get("user_id")
    result = await usecases.memory.extract_memory_usecase.execute(user_id)
    return ExtractMemoryOutput(**result)
