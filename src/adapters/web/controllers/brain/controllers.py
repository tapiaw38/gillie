from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Request, status
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/brain", tags=["Brain"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class MemoryItem(BaseModel):
    id: Optional[str]
    type: str
    content: str
    importance: int
    emotion: Optional[str]
    tags: List[str]
    created_at: datetime
    access_count: int
    promoted_to_soul: bool = False


class MemoryListOutput(BaseModel):
    total: int
    data: List[MemoryItem]


class BrainStatsOutput(BaseModel):
    total: int
    promoted: int
    consolidate_candidates: int
    prune_candidates: int
    by_importance: dict
    by_type: dict
    by_age: dict


class ConsolidateOutput(BaseModel):
    written: int
    pruned: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_brain(request: Request):
    return getattr(request.app.state, "brain", None)


def _get_skill_manager(request: Request):
    return getattr(request.app.state, "skill_manager", None)


def _get_user_id(request: Request) -> str:
    return request.state.user.get("user_id", "")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=BrainStatsOutput, status_code=status.HTTP_200_OK)
async def brain_stats(request: Request):
    """Memory distribution by importance, type, and age."""
    brain = _get_brain(request)
    if brain is None:
        return BrainStatsOutput(
            total=0, promoted=0, consolidate_candidates=0, prune_candidates=0,
            by_importance={}, by_type={}, by_age={},
        )

    user_id = _get_user_id(request)
    memories = await brain.episodic_repo.find_by_user_id(user_id, limit=5000)

    now = datetime.now(timezone.utc)
    by_importance: dict = {}
    by_type: dict = {}
    promoted = 0
    age_7d = age_30d = age_90d = age_older = 0
    prune_candidates = 0

    for m in memories:
        by_importance[str(m.importance)] = by_importance.get(str(m.importance), 0) + 1
        by_type[m.type] = by_type.get(m.type, 0) + 1
        if m.promoted_to_soul:
            promoted += 1

        age_days = max(0, (now - m.created_at).days)
        if age_days <= 7:
            age_7d += 1
        elif age_days <= 30:
            age_30d += 1
        elif age_days <= 90:
            age_90d += 1
        else:
            age_older += 1

        if m.importance <= 3 and age_days > 30:
            prune_candidates += 1
        elif m.importance <= 5 and age_days > 90 and m.access_count == 0:
            prune_candidates += 1

    consolidate_candidates = sum(
        v for k, v in by_importance.items() if int(k) >= 7
    )

    return BrainStatsOutput(
        total=len(memories),
        promoted=promoted,
        consolidate_candidates=consolidate_candidates,
        prune_candidates=prune_candidates,
        by_importance=by_importance,
        by_type=by_type,
        by_age={"7d": age_7d, "30d": age_30d, "90d": age_90d, "older": age_older},
    )


@router.get("/memories", response_model=MemoryListOutput, status_code=status.HTTP_200_OK)
async def list_memories(
    request: Request,
    limit: int = 20,
    memory_type: Optional[str] = None,
    min_importance: Optional[int] = None,
):
    """List recent episodic memories."""
    brain = _get_brain(request)
    if brain is None:
        return MemoryListOutput(total=0, data=[])

    user_id = _get_user_id(request)
    memories = await brain.episodic_repo.find_by_user_id(user_id, limit=limit * 5)

    if memory_type:
        memories = [m for m in memories if m.type == memory_type]
    if min_importance is not None:
        memories = [m for m in memories if m.importance >= min_importance]

    memories = memories[:limit]

    return MemoryListOutput(
        total=len(memories),
        data=[
            MemoryItem(
                id=m.id,
                type=m.type,
                content=m.content,
                importance=m.importance,
                emotion=m.emotion,
                tags=m.tags,
                created_at=m.created_at,
                access_count=m.access_count,
                promoted_to_soul=m.promoted_to_soul,
            )
            for m in memories
        ],
    )


@router.post("/consolidate", response_model=ConsolidateOutput, status_code=status.HTTP_200_OK)
async def consolidate(request: Request):
    """Promote high-importance episodic memories to general.skill.md and prune stale ones."""
    brain = _get_brain(request)
    skill_manager = _get_skill_manager(request)

    if brain is None or skill_manager is None:
        return ConsolidateOutput(written=0, pruned=0)

    user_id = _get_user_id(request)
    result = await brain.consolidator.consolidate(
        user_id=user_id,
        skill_manager=skill_manager,
        auto_prune=True,
    )

    from src.adapters.bootstrap.startup_service import StartupService
    StartupService._write_last_maintenance()

    return ConsolidateOutput(
        written=result.get("written", 0),
        pruned=result.get("pruned", 0),
    )
