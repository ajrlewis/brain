from brain_core.knowledge import KnowledgeService
from brain_core.settings import Settings
from brain_core.skills import SkillService
from brain_db import create_async_engine, create_async_session_factory


def create_persistence_services(settings: Settings) -> tuple[KnowledgeService, SkillService]:
    """Build runtime services over one shared engine while retaining one session per operation."""
    engine = create_async_engine(settings)
    factory = create_async_session_factory(engine)
    return KnowledgeService(factory), SkillService(factory)
