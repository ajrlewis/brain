import os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import cast
from uuid import UUID, uuid5

import yaml
from sqlalchemy import Table, inspect
from sqlalchemy.dialects.postgresql import insert

from brain_db.base import Base
from brain_db.models import (
    AccessPolicy,
    AccessPolicyGroup,
    Folder,
    Group,
    GroupMembership,
    Organization,
    Page,
    PageVersion,
    PageVersionSource,
    Principal,
    Source,
)
from brain_db.offline import (
    create_offline_engine,
    create_offline_session_factory,
    offline_session_scope,
)
from brain_schemas import parse_skill_document

NAMESPACE = UUID("8d18e949-c857-54f1-87c8-106abf75547c")


@dataclass(frozen=True)
class SeedSettings:
    database_url: str


@dataclass(frozen=True)
class NorthstarBundle:
    root: Path
    manifest: dict[str, object]
    documents: dict[str, str]


def northstar_id(name: str) -> UUID:
    return uuid5(NAMESPACE, name)


def model_table(model: type[Base]) -> Table:
    return cast(Table, inspect(model).local_table)


def northstar_bundle_root() -> Path:
    repository_bundle = Path(__file__).resolve().parents[4] / "examples" / "northstar"
    if repository_bundle.is_dir():
        return repository_bundle
    return Path(__file__).resolve().parent / "_bundles" / "northstar"


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Northstar {label} must be a mapping")
    raw_mapping = cast(dict[object, object], value)
    if any(not isinstance(key, str) for key in raw_mapping):
        raise ValueError(f"Northstar {label} must be a mapping")
    return cast(dict[str, object], value)


def _records(manifest: dict[str, object], name: str) -> list[dict[str, object]]:
    value = manifest.get(name)
    if not isinstance(value, list):
        raise ValueError(f"Northstar manifest must contain a {name} list")
    return [_mapping(record, f"{name} entry") for record in cast(list[object], value)]


def _text(record: dict[str, object], name: str) -> str:
    value = record.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Northstar manifest field '{name}' must be a non-empty string")
    return value


def _json(record: dict[str, object], name: str) -> dict[str, object]:
    return _mapping(record.get(name, {}), f"field '{name}'")


def _bundle_text(root: Path, relative_file: str) -> str:
    resolved_root = root.resolve()
    if Path(relative_file).is_absolute():
        raise ValueError("Northstar file must stay within the bundle")
    path = (resolved_root / relative_file).resolve()
    if not path.is_relative_to(resolved_root) or not path.is_file():
        raise ValueError("Northstar file must stay within the bundle and exist")
    try:
        content = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"Northstar file must be UTF-8 text: {relative_file}") from error
    if not content.strip():
        raise ValueError(f"Northstar file must not be empty: {relative_file}")
    return content


def load_northstar_bundle(root: Path | None = None) -> NorthstarBundle:
    bundle_root = root or northstar_bundle_root()
    try:
        loaded: object = yaml.safe_load((bundle_root / "seed" / "manifest.yaml").read_text())
    except (OSError, yaml.YAMLError) as error:
        raise ValueError("Northstar manifest is not readable valid YAML") from error
    manifest = _mapping(loaded, "manifest")
    if manifest.get("bundle") != "northstar" or manifest.get("version") != 1:
        raise ValueError("Northstar manifest must declare bundle northstar version 1")

    named_collections = (
        "organizations",
        "principals",
        "groups",
        "policies",
        "folders",
        "sources",
        "pages",
    )
    keys: set[str] = set()
    for collection in named_collections:
        for record in _records(manifest, collection):
            key = _text(record, "key")
            if key in keys:
                raise ValueError(f"Northstar stable key is duplicated: {key}")
            keys.add(key)

    for collection, fields in (
        ("principals", ("organization",)),
        ("groups", ("organization",)),
        ("memberships", ("organization", "group", "principal")),
        ("policies", ("organization",)),
        ("policy_groups", ("organization", "policy", "group")),
        ("folders", ("organization", "policy")),
        ("sources", ("organization", "policy")),
        ("pages", ("organization", "folder", "policy")),
    ):
        for record in _records(manifest, collection):
            for field in fields:
                reference = _text(record, field)
                if reference not in keys:
                    raise ValueError(f"Northstar reference does not resolve: {reference}")

    documents: dict[str, str] = {}
    for source in _records(manifest, "sources"):
        relative_file = _text(source, "document")
        documents[relative_file] = _bundle_text(bundle_root, relative_file)
    for page in _records(manifest, "pages"):
        versions = page.get("versions")
        if not isinstance(versions, list) or not versions:
            raise ValueError("Northstar Page must contain at least one version")
        for raw_version in cast(list[object], versions):
            version = _mapping(raw_version, "Page version")
            version_key = _text(version, "key")
            if version_key in keys:
                raise ValueError(f"Northstar stable key is duplicated: {version_key}")
            keys.add(version_key)
            relative_file = _text(version, "file")
            documents[relative_file] = _bundle_text(bundle_root, relative_file)
            provenance = version.get("provenance", [])
            if not isinstance(provenance, list):
                raise ValueError("Northstar Page version provenance must be a list")
            for raw_link in cast(list[object], provenance):
                link = _mapping(raw_link, "provenance entry")
                source_key = _text(link, "source")
                if source_key not in keys:
                    raise ValueError(f"Northstar reference does not resolve: {source_key}")

    for skill_path in sorted((bundle_root / "skills").glob("*/SKILL.md")):
        parse_skill_document(skill_path.read_bytes().decode("utf-8"))
    return NorthstarBundle(bundle_root, manifest, documents)


def seed_northstar(database_url: str, *, bundle_root: Path | None = None) -> None:
    """Insert the checked-in synthetic Northstar corpus with stable identifiers."""
    bundle = load_northstar_bundle(bundle_root)
    manifest = bundle.manifest
    engine = create_offline_engine(SeedSettings(database_url=database_url))
    factory = create_offline_session_factory(engine)
    alex = northstar_id("principal:alex")
    cortex = northstar_id("principal:cortex")

    def identifier(record: dict[str, object], field: str = "key") -> UUID:
        return northstar_id(_text(record, field))

    with offline_session_scope(factory) as session:
        rows: list[tuple[type[Base], list[dict[str, object]]]] = [
            (
                Organization,
                [
                    {"id": identifier(row), "slug": _text(row, "slug"), "name": _text(row, "name")}
                    for row in _records(manifest, "organizations")
                ],
            ),
            (
                Principal,
                [
                    {
                        "id": identifier(row),
                        "organization_id": identifier(row, "organization"),
                        "kind": _text(row, "kind"),
                        "external_subject": _text(row, "external_subject"),
                        "display_name": _text(row, "display_name"),
                        "is_active": True,
                    }
                    for row in _records(manifest, "principals")
                ],
            ),
            (
                Group,
                [
                    {
                        "id": identifier(row),
                        "organization_id": identifier(row, "organization"),
                        "slug": _text(row, "slug"),
                        "name": _text(row, "name"),
                    }
                    for row in _records(manifest, "groups")
                ],
            ),
            (
                GroupMembership,
                [
                    {
                        "organization_id": identifier(row, "organization"),
                        "group_id": identifier(row, "group"),
                        "principal_id": identifier(row, "principal"),
                    }
                    for row in _records(manifest, "memberships")
                ],
            ),
            (
                AccessPolicy,
                [
                    {
                        "id": identifier(row),
                        "organization_id": identifier(row, "organization"),
                        "name": _text(row, "name"),
                    }
                    for row in _records(manifest, "policies")
                ],
            ),
            (
                AccessPolicyGroup,
                [
                    {
                        "organization_id": identifier(row, "organization"),
                        "access_policy_id": identifier(row, "policy"),
                        "group_id": identifier(row, "group"),
                    }
                    for row in _records(manifest, "policy_groups")
                ],
            ),
            (
                Folder,
                [
                    {
                        "id": identifier(row),
                        "organization_id": identifier(row, "organization"),
                        "kind": "page",
                        "slug": _text(row, "slug"),
                        "name": _text(row, "name"),
                        "access_policy_id": identifier(row, "policy"),
                        "position": row.get("position", 0),
                        "steward_id": alex,
                        "created_by_id": cortex,
                        "updated_by_id": cortex,
                    }
                    for row in _records(manifest, "folders")
                ],
            ),
            (
                Source,
                [
                    {
                        "id": identifier(row),
                        "organization_id": identifier(row, "organization"),
                        "source_type": _text(row, "source_type"),
                        "title": _text(row, "title"),
                        "canonical_uri": row.get("canonical_uri"),
                        "external_id": _text(row, "external_id"),
                        "status": "active",
                        "access_policy_id": identifier(row, "policy"),
                        "metadata": _json(row, "metadata"),
                        "provenance": _json(row, "provenance"),
                        "created_by_id": cortex,
                        "updated_by_id": cortex,
                        "steward_id": alex,
                    }
                    for row in _records(manifest, "sources")
                ],
            ),
        ]
        for model, values in rows:
            session.execute(insert(model_table(model)).values(values).on_conflict_do_nothing())

        for page_spec in _records(manifest, "pages"):
            page_id = identifier(page_spec)
            organization_id = identifier(page_spec, "organization")
            session.execute(
                insert(model_table(Page))
                .values(
                    id=page_id,
                    organization_id=organization_id,
                    folder_id=identifier(page_spec, "folder"),
                    slug=_text(page_spec, "slug"),
                    title=_text(page_spec, "title"),
                    access_policy_id=identifier(page_spec, "policy"),
                    position=0,
                    steward_id=alex,
                    created_by_id=cortex,
                    updated_by_id=cortex,
                )
                .on_conflict_do_nothing()
            )
            raw_versions = cast(list[object], page_spec["versions"])
            current_version_id: UUID | None = None
            for version_number, raw_version in enumerate(raw_versions, 1):
                version = _mapping(raw_version, "Page version")
                version_id = identifier(version)
                markdown = bundle.documents[_text(version, "file")]
                session.execute(
                    insert(model_table(PageVersion))
                    .values(
                        id=version_id,
                        organization_id=organization_id,
                        page_id=page_id,
                        version=version_number,
                        content_markdown=markdown,
                        content_hash=sha256(markdown.encode()).hexdigest(),
                        created_by_id=cortex,
                    )
                    .on_conflict_do_nothing()
                )
                links: list[dict[str, object]] = []
                for raw_link in cast(list[object], version.get("provenance", [])):
                    link = _mapping(raw_link, "provenance entry")
                    links.append(
                        {
                            "organization_id": organization_id,
                            "page_version_id": version_id,
                            "source_id": identifier(link, "source"),
                            "relationship": _text(link, "relationship"),
                            "metadata": _json(link, "metadata"),
                        }
                    )
                if links:
                    session.execute(
                        insert(model_table(PageVersionSource))
                        .values(links)
                        .on_conflict_do_nothing()
                    )
                current_version_id = version_id
            session.query(Page).filter(Page.id == page_id).update(
                {Page.current_version_id: current_version_id}, synchronize_session=False
            )
    engine.dispose()


def run() -> None:
    database_url = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://brain:brain@localhost:5432/brain"
    )
    seed_northstar(database_url)


if __name__ == "__main__":
    run()
