from src.core.platform.appcontext.appcontext import Factory


class ListOwnerMemoriesUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(
        self,
        owner_user_id: str,
        contact_id: str | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        ctx = self.context_factory()
        if not ctx.repositories.episodic_memory:
            return {"items": [], "has_more": False, "next_offset": None}
        return await ctx.repositories.episodic_memory.find_by_owner_user_id(
            owner_user_id=owner_user_id,
            contact_id=contact_id,
            query=query,
            limit=limit,
            offset=offset,
        )
