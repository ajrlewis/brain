import argparse
import os
from dataclasses import dataclass
from difflib import unified_diff
from hashlib import sha256
from pathlib import Path
from typing import cast
from uuid import UUID, uuid5

import yaml
from sqlalchemy import Table, inspect, select
from sqlalchemy.dialects.postgresql import insert

from brain_db.base import Base
from brain_db.models import AccessPolicy, Organization, Principal, Skill, SkillVersion
from brain_db.offline import (
    create_offline_engine,
    create_offline_session_factory,
    offline_session_scope,
)
from brain_schemas import parse_skill_document

DEFAULT_NAMESPACE = UUID("a44bda51-9701-53b9-909f-dcc14a8f973f")
AVAILABLE_TOOLS = {
    "create_page",
    "create_page_version",
    "create_source",
    "get_page",
    "get_page_by_path",
    "get_skill_by_slug",
    "get_source",
    "list_pages",
    "list_sources",
    "list_skills",
}


@dataclass(frozen=True)
class DefaultSkill:
    slug: str
    name: str
    position: int
    content_markdown: str
    references: tuple["BundleReference", ...] = ()

    @property
    def content_hash(self) -> str:
        return sha256(self.content_markdown.encode()).hexdigest()


@dataclass(frozen=True)
class BundleReference:
    path: str
    content: bytes

    @property
    def content_hash(self) -> str:
        return sha256(self.content).hexdigest()


@dataclass(frozen=True)
class SeedDefaultsResult:
    created: tuple[str, ...]
    preserved: tuple[str, ...]


@dataclass(frozen=True)
class DefaultSkillReview:
    slug: str
    status: str
    current_version_id: UUID | None
    diff: str


@dataclass(frozen=True)
class DatabaseSettings:
    database_url: str


def model_table(model: type[Base]) -> Table:
    return cast(Table, inspect(model).local_table)


def default_bundle_root() -> Path:
    repository_bundle = Path(__file__).resolve().parents[4] / "content" / "default"
    if repository_bundle.is_dir():
        return repository_bundle
    return Path(__file__).resolve().parent / "_bundles" / "default"


def _bundle_file(bundle_root: Path, relative_file: str, label: str) -> Path:
    if not relative_file or Path(relative_file).is_absolute():
        raise ValueError(f"{label} must be a relative path within the bundle")
    resolved_root = bundle_root.resolve()
    path = (resolved_root / relative_file).resolve()
    if not path.is_relative_to(resolved_root):
        raise ValueError(f"{label} must stay within the bundle")
    if not path.is_file():
        raise ValueError(f"{label} does not exist: {relative_file}")
    return path


def load_default_bundle(root: Path | None = None) -> tuple[DefaultSkill, ...]:
    bundle_root = root or default_bundle_root()
    try:
        loaded: object = yaml.safe_load((bundle_root / "manifest.yaml").read_text())
    except (OSError, yaml.YAMLError) as error:
        raise ValueError("Default Skill manifest is not readable valid YAML") from error
    if not isinstance(loaded, dict):
        raise ValueError("Default Skill manifest must declare version 1")
    manifest = cast(dict[object, object], loaded)
    if manifest.get("version") != 1:
        raise ValueError("Default Skill manifest must declare version 1")
    if manifest.get("bundle") != "brain-default-skills":
        raise ValueError("Default Skill manifest has an invalid bundle identity")
    entries = manifest.get("skills")
    if not isinstance(entries, list):
        raise ValueError("Default Skill manifest must contain a skills list")
    skills: list[DefaultSkill] = []
    contracts: dict[str, dict[str, object]] = {}
    for raw_entry in cast(list[object], entries):
        entry = raw_entry
        if not isinstance(entry, dict):
            raise ValueError("Default Skill manifest entries must be mappings")
        entry = cast(dict[object, object], entry)
        slug, name, relative_file, position = (
            entry.get("slug"),
            entry.get("name"),
            entry.get("file"),
            entry.get("position"),
        )
        if not isinstance(slug, str) or not isinstance(name, str):
            raise ValueError("Default Skill manifest identities must be strings")
        if not isinstance(relative_file, str) or not isinstance(position, int):
            raise ValueError("Default Skill manifest file and position are invalid")
        expected_file = f"skills/{slug}/SKILL.md"
        if relative_file != expected_file:
            raise ValueError(f"Default Skill '{slug}' must use {expected_file}")
        path = _bundle_file(bundle_root, relative_file, "Default Skill file")
        try:
            markdown = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(f"Default Skill '{slug}' must be UTF-8 Markdown") from error
        frontmatter = parse_skill_document(markdown)
        if frontmatter["name"] != slug:
            raise ValueError(f"Default Skill '{slug}' frontmatter name does not match")
        tools = cast(list[str], frontmatter["tools"])
        unknown = set(tools) - AVAILABLE_TOOLS
        if unknown:
            raise ValueError(f"Default Skill '{slug}' advertises unavailable tools: {unknown}")
        raw_references = entry.get("references", [])
        if not isinstance(raw_references, list):
            raise ValueError(f"Default Skill '{slug}' references must be a list of paths")
        reference_values = cast(list[object], raw_references)
        if any(not isinstance(reference, str) for reference in reference_values):
            raise ValueError(f"Default Skill '{slug}' references must be a list of paths")
        references: list[BundleReference] = []
        expected_reference_root = f"skills/{slug}/references/"
        for reference in cast(list[str], reference_values):
            if not reference.startswith(expected_reference_root):
                raise ValueError(f"Default Skill '{slug}' reference is outside its references/")
            reference_path = _bundle_file(bundle_root, reference, "Default Skill reference")
            references.append(BundleReference(reference, reference_path.read_bytes()))
        if len({reference.path for reference in references}) != len(references):
            raise ValueError(f"Default Skill '{slug}' contains duplicate references")
        skills.append(DefaultSkill(slug, name, position, markdown, tuple(references)))
        contracts[slug] = frontmatter
    slugs = [skill.slug for skill in skills]
    if len(slugs) != len(set(slugs)) or set(slugs) != {
        "index",
        "ingest",
        "retrieve",
        "update",
        "lint",
    }:
        raise ValueError("Default Skill manifest must define each canonical Skill exactly once")
    positions = [skill.position for skill in skills]
    if positions != sorted(positions) or len(positions) != len(set(positions)):
        raise ValueError("Default Skill positions must be unique and ordered")
    declared_files = {f"skills/{skill.slug}/SKILL.md" for skill in skills} | {
        reference.path for skill in skills for reference in skill.references
    }
    actual_files = {
        path.relative_to(bundle_root).as_posix()
        for path in (bundle_root / "skills").rglob("*")
        if path.is_file()
    }
    if actual_files != declared_files:
        raise ValueError("Default Skill bundle contains undeclared or missing files")
    index = next(skill for skill in skills if skill.slug == "index")
    for slug in set(slugs) - {"index"}:
        if f"`{slug}`" not in index.content_markdown:
            raise ValueError(f"Default Skill '{slug}' is unreachable from index")
    routes = contracts["index"].get("routes")
    if not isinstance(routes, dict):
        raise ValueError("Default Skill index must declare route contracts")
    raw_routes = cast(dict[object, object], routes)
    if set(raw_routes) != set(slugs) - {"index"}:
        raise ValueError("Default Skill index routes must reach every non-index Skill")
    for raw_slug, raw_route in raw_routes.items():
        if not isinstance(raw_slug, str) or not isinstance(raw_route, dict):
            raise ValueError("Default Skill index routes must be named mappings")
        route = cast(dict[object, object], raw_route)
        purpose, inputs, tools = route.get("purpose"), route.get("inputs"), route.get("tools")
        if not isinstance(purpose, str) or not purpose.strip():
            raise ValueError(f"Default Skill route '{raw_slug}' must declare its purpose")
        if not isinstance(inputs, list):
            raise ValueError(f"Default Skill route '{raw_slug}' inputs are invalid")
        raw_inputs = cast(list[object], inputs)
        if not all(isinstance(item, str) for item in raw_inputs):
            raise ValueError(f"Default Skill route '{raw_slug}' inputs are invalid")
        if not isinstance(tools, list):
            raise ValueError(f"Default Skill route '{raw_slug}' tools are invalid")
        raw_tools = cast(list[object], tools)
        if not all(isinstance(item, str) for item in raw_tools):
            raise ValueError(f"Default Skill route '{raw_slug}' tools are invalid")
        target_inputs = cast(dict[str, dict[str, object]], contracts[raw_slug]["inputs"])
        required_inputs = {
            name for name, definition in target_inputs.items() if definition.get("required") is True
        }
        if set(cast(list[str], inputs)) != required_inputs:
            raise ValueError(f"Default Skill route '{raw_slug}' inputs do not match its contract")
        target_tools = set(cast(list[str], contracts[raw_slug]["tools"]))
        if not set(cast(list[str], tools)) <= target_tools:
            raise ValueError(f"Default Skill route '{raw_slug}' advertises unsupported tools")
    return tuple(skills)


def seed_defaults(
    database_url: str,
    *,
    organization_slug: str,
    policy_name: str,
    steward_external_subject: str,
    audit_external_subject: str,
    bundle_root: Path | None = None,
) -> SeedDefaultsResult:
    """Create missing version-one defaults and preserve every existing current Skill."""
    bundle = load_default_bundle(bundle_root)
    engine = create_offline_engine(DatabaseSettings(database_url))
    factory = create_offline_session_factory(engine)
    created: list[str] = []
    preserved: list[str] = []
    with offline_session_scope(factory) as session:
        organization = session.scalar(
            select(Organization).where(
                Organization.slug == organization_slug,
                Organization.deleted_at.is_(None),
            )
        )
        if organization is None:
            raise ValueError("Target Organization was not found")
        policy = session.scalar(
            select(AccessPolicy).where(
                AccessPolicy.organization_id == organization.id,
                AccessPolicy.name == policy_name,
                AccessPolicy.deleted_at.is_(None),
            )
        )
        if policy is None:
            raise ValueError("Target access policy was not found")

        def principal(subject: str, role: str) -> Principal:
            record = session.scalar(
                select(Principal).where(
                    Principal.organization_id == organization.id,
                    Principal.external_subject == subject,
                    Principal.is_active.is_(True),
                    Principal.deleted_at.is_(None),
                )
            )
            if record is None:
                raise ValueError(f"Target {role} Principal was not found")
            return record

        steward = principal(steward_external_subject, "steward")
        audit = principal(audit_external_subject, "audit")
        for bundled in bundle:
            skill_id = uuid5(DEFAULT_NAMESPACE, f"{organization.id}:skill:{bundled.slug}")
            session.execute(
                insert(model_table(Skill))
                .values(
                    id=skill_id,
                    organization_id=organization.id,
                    slug=bundled.slug,
                    name=bundled.name,
                    access_policy_id=policy.id,
                    position=bundled.position,
                    steward_id=steward.id,
                    created_by_id=audit.id,
                    updated_by_id=audit.id,
                )
                .on_conflict_do_nothing()
            )
            skill = session.scalar(
                select(Skill)
                .where(
                    Skill.organization_id == organization.id,
                    Skill.slug == bundled.slug,
                    Skill.deleted_at.is_(None),
                )
                .with_for_update()
            )
            if skill is None:
                raise RuntimeError("Default Skill could not be resolved after insert")
            if skill.current_version_id is not None:
                preserved.append(bundled.slug)
                continue
            version_id = uuid5(DEFAULT_NAMESPACE, f"{skill.id}:version:1:{bundled.content_hash}")
            session.execute(
                insert(model_table(SkillVersion))
                .values(
                    id=version_id,
                    organization_id=organization.id,
                    skill_id=skill.id,
                    version=1,
                    content_markdown=bundled.content_markdown,
                    content_hash=bundled.content_hash,
                    created_by_id=audit.id,
                )
                .on_conflict_do_nothing()
            )
            version = session.scalar(
                select(SkillVersion).where(
                    SkillVersion.skill_id == skill.id,
                    SkillVersion.version == 1,
                )
            )
            if version is None:
                raise RuntimeError("Default Skill version could not be resolved after insert")
            skill.current_version_id = version.id
            created.append(bundled.slug)
    engine.dispose()
    return SeedDefaultsResult(tuple(created), tuple(preserved))


def review_defaults(
    database_url: str,
    *,
    organization_slug: str,
    bundle_root: Path | None = None,
) -> tuple[DefaultSkillReview, ...]:
    """Compare bundled documents with deployment state without changing either."""
    bundle = load_default_bundle(bundle_root)
    engine = create_offline_engine(DatabaseSettings(database_url))
    factory = create_offline_session_factory(engine)
    reviews: list[DefaultSkillReview] = []
    with offline_session_scope(factory) as session:
        organization = session.scalar(
            select(Organization).where(
                Organization.slug == organization_slug,
                Organization.deleted_at.is_(None),
            )
        )
        if organization is None:
            raise ValueError("Target Organization was not found")
        for bundled in bundle:
            skill = session.scalar(
                select(Skill).where(
                    Skill.organization_id == organization.id,
                    Skill.slug == bundled.slug,
                    Skill.deleted_at.is_(None),
                )
            )
            current = (
                session.get(SkillVersion, skill.current_version_id)
                if skill is not None and skill.current_version_id is not None
                else None
            )
            if current is None:
                reviews.append(DefaultSkillReview(bundled.slug, "missing", None, ""))
                continue
            if current.content_hash == bundled.content_hash:
                reviews.append(DefaultSkillReview(bundled.slug, "current", current.id, ""))
                continue
            difference = "".join(
                unified_diff(
                    current.content_markdown.splitlines(keepends=True),
                    bundled.content_markdown.splitlines(keepends=True),
                    fromfile=f"deployment/{bundled.slug}.md",
                    tofile=f"bundle/{bundled.slug}.md",
                )
            )
            reviews.append(DefaultSkillReview(bundled.slug, "diverged", current.id, difference))
    engine.dispose()
    return tuple(reviews)


def run() -> None:
    parser = argparse.ArgumentParser(description="Seed Brain's repository-owned default Skills")
    parser.add_argument("--organization", required=True, help="Organization slug")
    parser.add_argument("--policy", required=True, help="Access policy name")
    parser.add_argument("--steward", required=True, help="Steward Principal external subject")
    parser.add_argument("--audit-principal", required=True, help="Audit Principal external subject")
    parser.add_argument(
        "--review", action="store_true", help="Print bundle/deployment diffs without writing"
    )
    arguments = parser.parse_args()
    database_url = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://brain:brain@localhost:5432/brain"
    )
    if arguments.review:
        for review in review_defaults(database_url, organization_slug=arguments.organization):
            print(f"{review.slug}: {review.status}")
            if review.diff:
                print(review.diff, end="" if review.diff.endswith("\n") else "\n")
        return
    result = seed_defaults(
        database_url,
        organization_slug=arguments.organization,
        policy_name=arguments.policy,
        steward_external_subject=arguments.steward,
        audit_external_subject=arguments.audit_principal,
    )
    print(
        f"created={','.join(result.created) or '-'} preserved={','.join(result.preserved) or '-'}"
    )


if __name__ == "__main__":
    run()
