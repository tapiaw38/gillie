from .attention import AttentionSystem
from .episodic_vector_service import EpisodicVectorService
from .soul_vector_service import SoulVectorService
from .memory_consolidator import MemoryConsolidator
from .memory_writer import EpisodicMemoryWriter
from .working_memory import WorkingMemoryAssembler


class BrainServices:
    """Container for all brain / cognitive-layer services."""

    def __init__(
        self,
        episodic_vector: EpisodicVectorService,
        soul_vector: SoulVectorService,
        episodic_repo,
        memory_writer: EpisodicMemoryWriter,
        working_memory: WorkingMemoryAssembler,
        attention: AttentionSystem,
        consolidator: MemoryConsolidator,
    ):
        self.episodic_vector = episodic_vector
        self.soul_vector = soul_vector
        self.episodic_repo = episodic_repo
        self.memory_writer = memory_writer
        self.working_memory = working_memory
        self.attention = attention
        self.consolidator = consolidator

    @classmethod
    def create(cls, episodic_repo, qdrant_adapter, embedding_service, openai_integration) -> "BrainServices":
        attention = AttentionSystem()
        episodic_vector = EpisodicVectorService(qdrant_adapter, embedding_service)
        soul_vector = SoulVectorService(qdrant_adapter, embedding_service)
        memory_writer = EpisodicMemoryWriter(episodic_repo, episodic_vector, openai_integration)
        working_memory = WorkingMemoryAssembler(episodic_vector, episodic_repo, attention, soul_vector)
        consolidator = MemoryConsolidator(episodic_repo, openai_integration, episodic_vector, soul_vector)

        return cls(
            episodic_vector=episodic_vector,
            soul_vector=soul_vector,
            episodic_repo=episodic_repo,
            memory_writer=memory_writer,
            working_memory=working_memory,
            attention=attention,
            consolidator=consolidator,
        )


__all__ = [
    "BrainServices",
    "AttentionSystem",
    "EpisodicVectorService",
    "SoulVectorService",
    "EpisodicMemoryWriter",
    "MemoryConsolidator",
    "WorkingMemoryAssembler",
]
