from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from brain_auth import AuthContext, AuthorizationDenied
from brain_core import (
    DuplicateSkillContent,
    InvalidKnowledgeReference,
    SkillNotFound,
    SkillService,
    VersionConflict,
)
from brain_db import Folder, Skill, SkillVersion
from brain_schemas import InvalidSkillDocument, SkillCreate, SkillVersionCreate

ORG = UUID("10000000-0000-0000-0000-000000000001")
PRINCIPAL = UUID("20000000-0000-0000-0000-000000000001")
GROUP = UUID("30000000-0000-0000-0000-000000000001")
OPEN_POLICY = UUID("40000000-0000-0000-0000-000000000001")
RESTRICTED_POLICY = UUID("40000000-0000-0000-0000-000000000002")


def document(name: str = "retrieve", body: str = "Read records.") -> str:
    return f"""---
name: {name}
description: A test Skill.
inputs:
  request:
    type: string
    required: true
outputs:
  result:
    type: object
tools:
  - list_pages
---

# Test

{body}
"""


class FakeSkillRepository:
    policies: dict[UUID, set[UUID]]
    skills_by_id: dict[UUID, Skill]
    versions_by_skill: dict[UUID, list[SkillVersion]]
    folders: dict[UUID, Folder]

    def __init__(self, session: Session) -> None:
        self.session = session

    @classmethod
    def reset(cls) -> None:
        cls.policies = {OPEN_POLICY: set(), RESTRICTED_POLICY: {GROUP}}
        cls.skills_by_id = {}
        cls.versions_by_skill = {}
        cls.folders = {}

    def context_is_valid(
        self, organization_id: UUID, principal_id: UUID, group_ids: frozenset[UUID]
    ) -> bool:
        return organization_id == ORG and principal_id == PRINCIPAL

    def principal_exists(self, organization_id: UUID, principal_id: UUID) -> bool:
        return organization_id == ORG and principal_id == PRINCIPAL

    def policy_group_ids(self, organization_id: UUID, policy_id: UUID) -> set[UUID] | None:
        return self.policies.get(policy_id) if organization_id == ORG else None

    def get_folder(self, organization_id: UUID, folder_id: UUID) -> Folder | None:
        folder = self.folders.get(folder_id)
        return folder if folder is not None and folder.organization_id == organization_id else None

    def add_skill(self, skill: Skill) -> None:
        now = datetime.now(UTC)
        skill.id = uuid4()
        skill.created_at = now
        skill.updated_at = now
        self.skills_by_id[skill.id] = skill
        self.versions_by_skill[skill.id] = []

    def get_skill(
        self, organization_id: UUID, skill_id: UUID, *, lock: bool = False
    ) -> Skill | None:
        skill = self.skills_by_id.get(skill_id)
        return skill if skill is not None and skill.organization_id == organization_id else None

    def get_skill_by_slug(self, organization_id: UUID, slug: str) -> Skill | None:
        return next(
            (
                skill
                for skill in self.skills_by_id.values()
                if skill.organization_id == organization_id and skill.slug == slug
            ),
            None,
        )

    def skills(self, organization_id: UUID) -> list[Skill]:
        return [
            skill
            for skill in self.skills_by_id.values()
            if skill.organization_id == organization_id and skill.current_version_id is not None
        ]

    def skill_inventory(self, organization_id: UUID) -> list[tuple[Skill, UUID, str]]:
        return [
            (skill, version.id, version.content_hash)
            for skill in self.skills(organization_id)
            for version in self.versions_by_skill[skill.id]
            if version.id == skill.current_version_id
        ]

    def add_skill_version(self, version: SkillVersion) -> None:
        version.id = uuid4()
        version.created_at = datetime.now(UTC)
        self.versions_by_skill[version.skill_id].append(version)

    def skill_versions(self, skill_id: UUID) -> list[SkillVersion]:
        return self.versions_by_skill[skill_id]

    def next_skill_version(self, skill_id: UUID) -> int:
        return len(self.versions_by_skill[skill_id]) + 1


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> SkillService:
    FakeSkillRepository.reset()
    monkeypatch.setattr("brain_core.skills.SkillRepository", FakeSkillRepository)
    return SkillService(lambda: Mock(spec=Session))


@pytest.fixture
def context() -> AuthContext:
    return AuthContext(ORG, PRINCIPAL, frozenset({GROUP}))


def test_skill_create_read_list_and_version_concurrency(
    service: SkillService, context: AuthContext
) -> None:
    created = service.create_skill(
        context,
        SkillCreate(
            slug="retrieve",
            name="Retrieve",
            content_markdown=document(),
            access_policy_id=OPEN_POLICY,
            steward_id=PRINCIPAL,
        ),
    )

    assert service.get_skill(context, created.id).current_version.content_markdown == document()
    assert service.get_skill_by_slug(context, "retrieve", version=1).id == created.id
    assert [item.slug for item in service.list_skills(context)] == ["retrieve"]

    updated = service.create_skill_version(
        context,
        created.id,
        SkillVersionCreate(
            expected_current_version_id=created.current_version.id,
            content_markdown=document(body="Read only relevant records."),
        ),
    )
    assert updated.current_version.version == 2
    assert [item.version for item in updated.versions] == [1, 2]

    with pytest.raises(VersionConflict):
        service.create_skill_version(
            context,
            created.id,
            SkillVersionCreate(
                expected_current_version_id=created.current_version.id,
                content_markdown=document(body="A stale proposal."),
            ),
        )
    with pytest.raises(DuplicateSkillContent):
        service.create_skill_version(
            context,
            created.id,
            SkillVersionCreate(
                expected_current_version_id=updated.current_version.id,
                content_markdown=document(body="Read only relevant records."),
            ),
        )


def test_skill_validation_missing_and_authorization(
    service: SkillService, context: AuthContext
) -> None:
    with pytest.raises(InvalidSkillDocument):
        service.create_skill(
            context,
            SkillCreate(
                slug="invalid",
                name="Invalid",
                content_markdown="# No frontmatter",
                access_policy_id=OPEN_POLICY,
                steward_id=PRINCIPAL,
            ),
        )
    with pytest.raises(InvalidKnowledgeReference):
        service.create_skill(
            context,
            SkillCreate(
                slug="missing-policy",
                name="Missing",
                content_markdown=document("missing-policy"),
                access_policy_id=uuid4(),
                steward_id=PRINCIPAL,
            ),
        )
    with pytest.raises(SkillNotFound):
        service.get_skill(context, uuid4())

    created = service.create_skill(
        context,
        SkillCreate(
            slug="restricted",
            name="Restricted",
            content_markdown=document("restricted"),
            access_policy_id=RESTRICTED_POLICY,
            steward_id=PRINCIPAL,
        ),
    )
    outsider = AuthContext(ORG, PRINCIPAL, frozenset())
    assert service.list_skills(outsider) == []
    with pytest.raises(AuthorizationDenied):
        service.get_skill(outsider, created.id)


def test_missing_version_and_invalid_skill_folder(
    service: SkillService, context: AuthContext
) -> None:
    folder_id = uuid4()
    FakeSkillRepository.folders[folder_id] = Folder(
        id=folder_id,
        organization_id=ORG,
        kind="page",
        access_policy_id=OPEN_POLICY,
    )
    with pytest.raises(InvalidKnowledgeReference):
        service.create_skill(
            context,
            SkillCreate(
                slug="foldered",
                name="Foldered",
                content_markdown=document("foldered"),
                access_policy_id=OPEN_POLICY,
                steward_id=PRINCIPAL,
                folder_id=folder_id,
            ),
        )
    created = service.create_skill(
        context,
        SkillCreate(
            slug="retrieve",
            name="Retrieve",
            content_markdown=document(),
            access_policy_id=OPEN_POLICY,
            steward_id=PRINCIPAL,
        ),
    )
    with pytest.raises(SkillNotFound):
        service.get_skill(context, created.id, version=99)
