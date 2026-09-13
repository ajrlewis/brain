from hashlib import sha256
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from brain_auth import AuthContext, AuthorizationDenied, require_access
from brain_core.knowledge import InvalidKnowledgeReference, VersionConflict
from brain_core.settings import Settings
from brain_db import (
    SessionFactory,
    Skill,
    SkillRepository,
    SkillVersion,
    create_engine,
    create_session_factory,
    session_scope,
)
from brain_schemas import (
    InvalidSkillDocument,
    SkillCreate,
    SkillInventoryItem,
    SkillResponse,
    SkillVersionCreate,
    SkillVersionResponse,
    parse_skill_document,
)


class SkillNotFound(Exception):
    """Raised when a live same-tenant Skill does not exist."""


class SkillConflict(Exception):
    """Raised when a Skill violates a uniqueness or structural constraint."""


class DuplicateSkillContent(SkillConflict):
    """Raised when content is already present in a Skill's immutable history."""


class SkillService:
    """Govern Skills through one shared HTTP/MCP application boundary."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self.session_factory = session_factory

    def create_skill(self, context: AuthContext, request: SkillCreate) -> SkillResponse:
        self._validate_document(request.content_markdown)
        with session_scope(self.session_factory) as session:
            repository = SkillRepository(session)
            self._require_context(repository, context)
            self._validate_references(repository, context, request)
            skill = Skill(
                organization_id=context.organization_id,
                folder_id=request.folder_id,
                slug=request.slug,
                name=request.name,
                access_policy_id=request.access_policy_id,
                position=request.position,
                steward_id=request.steward_id,
                created_by_id=context.principal_id,
                updated_by_id=context.principal_id,
            )
            try:
                repository.add_skill(skill)
                version = self._insert_version(repository, context, skill, request.content_markdown)
                skill.current_version_id = version.id
                session.flush()
            except IntegrityError as error:
                raise SkillConflict("Skill conflicts with an existing record") from error
            return self._response(repository, skill)

    def create_skill_version(
        self, context: AuthContext, skill_id: UUID, request: SkillVersionCreate
    ) -> SkillResponse:
        self._validate_document(request.content_markdown)
        with session_scope(self.session_factory) as session:
            repository = SkillRepository(session)
            self._require_context(repository, context)
            skill = repository.get_skill(context.organization_id, skill_id, lock=True)
            if skill is None:
                raise SkillNotFound("Skill was not found")
            self._require_resource(repository, context, skill.access_policy_id)
            if skill.current_version_id != request.expected_current_version_id:
                raise VersionConflict("The Skill current version has changed")
            content_hash = sha256(request.content_markdown.encode()).hexdigest()
            if any(
                version.content_hash == content_hash
                for version in repository.skill_versions(skill.id)
            ):
                raise DuplicateSkillContent("This content already exists for the Skill")
            try:
                version = self._insert_version(repository, context, skill, request.content_markdown)
                skill.current_version_id = version.id
                skill.updated_by_id = context.principal_id
                session.flush()
            except IntegrityError as error:
                raise SkillConflict("Skill version conflicts with existing history") from error
            return self._response(repository, skill)

    def get_skill(
        self, context: AuthContext, skill_id: UUID, version: int | None = None
    ) -> SkillResponse:
        with session_scope(self.session_factory) as session:
            repository = SkillRepository(session)
            self._require_context(repository, context)
            skill = repository.get_skill(context.organization_id, skill_id)
            if skill is None or skill.current_version_id is None:
                raise SkillNotFound("Skill was not found")
            self._require_resource(repository, context, skill.access_policy_id)
            return self._response(repository, skill, version)

    def get_skill_by_slug(
        self, context: AuthContext, slug: str, version: int | None = None
    ) -> SkillResponse:
        with session_scope(self.session_factory) as session:
            repository = SkillRepository(session)
            self._require_context(repository, context)
            skill = repository.get_skill_by_slug(context.organization_id, slug)
            if skill is None or skill.current_version_id is None:
                raise SkillNotFound("Skill was not found")
            self._require_resource(repository, context, skill.access_policy_id)
            return self._response(repository, skill, version)

    def list_skills(self, context: AuthContext) -> list[SkillInventoryItem]:
        with session_scope(self.session_factory) as session:
            repository = SkillRepository(session)
            self._require_context(repository, context)
            result: list[SkillInventoryItem] = []
            for skill, current_version_id, content_hash in repository.skill_inventory(
                context.organization_id
            ):
                try:
                    self._require_resource(repository, context, skill.access_policy_id)
                except AuthorizationDenied:
                    continue
                result.append(
                    SkillInventoryItem(
                        id=skill.id,
                        slug=skill.slug,
                        name=skill.name,
                        current_version_id=current_version_id,
                        content_hash=content_hash,
                    )
                )
            return result

    @staticmethod
    def _validate_document(markdown: str) -> None:
        try:
            parse_skill_document(markdown)
        except InvalidSkillDocument:
            raise

    @staticmethod
    def _insert_version(
        repository: SkillRepository, context: AuthContext, skill: Skill, markdown: str
    ) -> SkillVersion:
        version = SkillVersion(
            organization_id=context.organization_id,
            skill_id=skill.id,
            version=repository.next_skill_version(skill.id),
            content_markdown=markdown,
            content_hash=sha256(markdown.encode()).hexdigest(),
            created_by_id=context.principal_id,
        )
        repository.add_skill_version(version)
        return version

    def _validate_references(
        self, repository: SkillRepository, context: AuthContext, request: SkillCreate
    ) -> None:
        if not repository.principal_exists(context.organization_id, request.steward_id):
            raise InvalidKnowledgeReference("Principal was not found")
        self._require_policy(repository, context, request.access_policy_id)
        if request.folder_id is not None:
            folder = repository.get_folder(context.organization_id, request.folder_id)
            if folder is None or folder.kind != "skill":
                raise InvalidKnowledgeReference("Skill folder was not found")
            self._require_resource(repository, context, folder.access_policy_id)

    @staticmethod
    def _require_context(repository: SkillRepository, context: AuthContext) -> None:
        if not repository.context_is_valid(
            context.organization_id, context.principal_id, context.group_ids
        ):
            raise AuthorizationDenied("The caller's authorization context is not valid")

    @staticmethod
    def _require_policy(repository: SkillRepository, context: AuthContext, policy_id: UUID) -> None:
        groups = repository.policy_group_ids(context.organization_id, policy_id)
        if groups is None:
            raise InvalidKnowledgeReference("Access policy was not found")
        require_access(context, organization_id=context.organization_id, permitted_group_ids=groups)

    @staticmethod
    def _require_resource(
        repository: SkillRepository, context: AuthContext, policy_id: UUID
    ) -> None:
        groups = repository.policy_group_ids(context.organization_id, policy_id)
        if groups is None:
            raise SkillNotFound("Skill was not found")
        require_access(context, organization_id=context.organization_id, permitted_group_ids=groups)

    @staticmethod
    def _version_response(version: SkillVersion) -> SkillVersionResponse:
        return SkillVersionResponse(
            id=version.id,
            skill_id=version.skill_id,
            version=version.version,
            content_markdown=version.content_markdown,
            content_hash=version.content_hash,
            created_by_id=version.created_by_id,
            created_at=version.created_at,
        )

    def _response(
        self, repository: SkillRepository, skill: Skill, requested_version: int | None = None
    ) -> SkillResponse:
        versions = [self._version_response(item) for item in repository.skill_versions(skill.id)]
        current_id = skill.current_version_id
        if requested_version is not None:
            selected = next((item for item in versions if item.version == requested_version), None)
            if selected is None:
                raise SkillNotFound("Skill version was not found")
            current = selected
        else:
            current = next(item for item in versions if item.id == current_id)
        return SkillResponse(
            id=skill.id,
            organization_id=skill.organization_id,
            folder_id=skill.folder_id,
            slug=skill.slug,
            name=skill.name,
            access_policy_id=skill.access_policy_id,
            position=skill.position,
            steward_id=skill.steward_id,
            created_at=skill.created_at,
            updated_at=skill.updated_at,
            current_version=current,
            versions=versions,
        )


def create_skill_service(settings: Settings) -> SkillService:
    """Build the database-backed Skill service without opening a connection."""
    engine = create_engine(settings)
    return SkillService(create_session_factory(engine))
