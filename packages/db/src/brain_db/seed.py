import os
from dataclasses import dataclass
from hashlib import sha256
from typing import cast
from uuid import UUID, uuid5

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

NAMESPACE = UUID("8d18e949-c857-54f1-87c8-106abf75547c")


@dataclass(frozen=True)
class SeedSettings:
    database_url: str


def northstar_id(name: str) -> UUID:
    return uuid5(NAMESPACE, name)


def model_table(model: type[Base]) -> Table:
    return cast(Table, inspect(model).local_table)


def seed_northstar(database_url: str) -> None:
    """Insert the synthetic Northstar example once, using stable identifiers."""
    engine = create_offline_engine(SeedSettings(database_url=database_url))
    factory = create_offline_session_factory(engine)
    org = northstar_id("organization:northstar")
    other_org = northstar_id("organization:harbour")
    alex = northstar_id("principal:alex")
    cortex = northstar_id("principal:cortex")
    harbour_user = northstar_id("principal:harbour")
    investment = northstar_id("group:investment")
    operations = northstar_id("group:operations")
    org_wide = northstar_id("policy:organization-wide")
    deal_team = northstar_id("policy:deal-team")
    people_folder = northstar_id("folder:people")
    portfolio_folder = northstar_id("folder:portfolio")
    memo_source = northstar_id("source:orion-memo")
    update_source = northstar_id("source:orion-update")
    restricted_source = northstar_id("source:committee-notes")

    with offline_session_scope(factory) as session:
        rows: list[tuple[type[Base], list[dict[str, object]]]] = [
            (
                Organization,
                [
                    {"id": org, "slug": "northstar", "name": "Northstar Equity Partners"},
                    {"id": other_org, "slug": "harbour", "name": "Harbour Example Holdings"},
                ],
            ),
            (
                Principal,
                [
                    {
                        "id": alex,
                        "organization_id": org,
                        "kind": "user",
                        "external_subject": "northstar-alex",
                        "display_name": "Alex Rowan",
                        "is_active": True,
                    },
                    {
                        "id": cortex,
                        "organization_id": org,
                        "kind": "agent",
                        "external_subject": "northstar-cortex",
                        "display_name": "Cortex Ingestion Agent",
                        "is_active": True,
                    },
                    {
                        "id": harbour_user,
                        "organization_id": other_org,
                        "kind": "user",
                        "external_subject": "harbour-user",
                        "display_name": "Harbour User",
                        "is_active": True,
                    },
                ],
            ),
            (
                Group,
                [
                    {
                        "id": investment,
                        "organization_id": org,
                        "slug": "investment-team",
                        "name": "Investment Team",
                    },
                    {
                        "id": operations,
                        "organization_id": org,
                        "slug": "portfolio-operations",
                        "name": "Portfolio Operations",
                    },
                ],
            ),
            (
                GroupMembership,
                [
                    {"organization_id": org, "group_id": investment, "principal_id": alex},
                    {"organization_id": org, "group_id": operations, "principal_id": cortex},
                ],
            ),
            (
                AccessPolicy,
                [
                    {"id": org_wide, "organization_id": org, "name": "Northstar organization-wide"},
                    {"id": deal_team, "organization_id": org, "name": "Investment team only"},
                ],
            ),
            (
                AccessPolicyGroup,
                [{"organization_id": org, "access_policy_id": deal_team, "group_id": investment}],
            ),
            (
                Folder,
                [
                    {
                        "id": people_folder,
                        "organization_id": org,
                        "kind": "page",
                        "slug": "people",
                        "name": "People",
                        "access_policy_id": org_wide,
                        "position": 10,
                        "steward_id": alex,
                        "created_by_id": cortex,
                        "updated_by_id": cortex,
                    },
                    {
                        "id": portfolio_folder,
                        "organization_id": org,
                        "kind": "page",
                        "slug": "portfolio",
                        "name": "Portfolio",
                        "access_policy_id": deal_team,
                        "position": 20,
                        "steward_id": alex,
                        "created_by_id": cortex,
                        "updated_by_id": cortex,
                    },
                ],
            ),
            (
                Source,
                [
                    {
                        "id": memo_source,
                        "organization_id": org,
                        "source_type": "investment-memo",
                        "title": "Project Orion investment memo",
                        "canonical_uri": "northstar://orion/memo",
                        "external_id": "orion-memo-2026",
                        "status": "active",
                        "access_policy_id": deal_team,
                        "metadata": {"format": "synthetic-markdown"},
                        "provenance": {"retrieved_by": "cortex", "fictional": True},
                        "created_by_id": cortex,
                        "updated_by_id": cortex,
                        "steward_id": alex,
                    },
                    {
                        "id": update_source,
                        "organization_id": org,
                        "source_type": "portfolio-update",
                        "title": "Project Orion operating update",
                        "canonical_uri": "northstar://orion/update",
                        "external_id": "orion-update-q3-2026",
                        "status": "active",
                        "access_policy_id": org_wide,
                        "metadata": {"quarter": "Q3"},
                        "provenance": {"retrieved_by": "cortex", "fictional": True},
                        "created_by_id": cortex,
                        "updated_by_id": cortex,
                        "steward_id": alex,
                    },
                    {
                        "id": restricted_source,
                        "organization_id": org,
                        "source_type": "committee-notes",
                        "title": "Orion committee notes",
                        "canonical_uri": None,
                        "external_id": "orion-ic-2026",
                        "status": "active",
                        "access_policy_id": deal_team,
                        "metadata": {},
                        "provenance": {"fictional": True},
                        "created_by_id": cortex,
                        "updated_by_id": cortex,
                        "steward_id": alex,
                    },
                ],
            ),
        ]
        for model, values in rows:
            session.execute(insert(model_table(model)).values(values).on_conflict_do_nothing())

        page_specs = [
            (
                "alex-rowan",
                "Alex Rowan",
                people_folder,
                org_wide,
                "# Alex Rowan\n\nOperating Partner at Northstar.",
            ),
            (
                "investment-team",
                "Investment Team",
                people_folder,
                org_wide,
                "# Investment Team\n\nEvaluates fictional investment opportunities.",
            ),
            (
                "operating-partner",
                "Operating Partner",
                people_folder,
                org_wide,
                "# Operating Partner\n\nSupports portfolio company value creation.",
            ),
            (
                "project-orion",
                "Project Orion",
                portfolio_folder,
                deal_team,
                "# Project Orion\n\nRevenue was reported as £42m in the initial memo.",
            ),
        ]
        for slug, title, folder_id, policy_id, markdown in page_specs:
            page_id = northstar_id(f"page:{slug}")
            first_version_id = northstar_id(f"page:{slug}:version:1")
            session.execute(
                insert(model_table(Page))
                .values(
                    id=page_id,
                    organization_id=org,
                    folder_id=folder_id,
                    slug=slug,
                    title=title,
                    access_policy_id=policy_id,
                    position=0,
                    steward_id=alex,
                    created_by_id=cortex,
                    updated_by_id=cortex,
                )
                .on_conflict_do_nothing()
            )
            session.execute(
                insert(model_table(PageVersion))
                .values(
                    id=first_version_id,
                    organization_id=org,
                    page_id=page_id,
                    version=1,
                    content_markdown=markdown,
                    content_hash=sha256(markdown.encode()).hexdigest(),
                    created_by_id=cortex,
                )
                .on_conflict_do_nothing()
            )
            current_version_id = first_version_id
            if slug == "project-orion":
                revised = (
                    "# Project Orion\n\nRevenue is £45m; the earlier £42m figure is superseded."
                )
                second_version_id = northstar_id("page:project-orion:version:2")
                session.execute(
                    insert(model_table(PageVersion))
                    .values(
                        id=second_version_id,
                        organization_id=org,
                        page_id=page_id,
                        version=2,
                        content_markdown=revised,
                        content_hash=sha256(revised.encode()).hexdigest(),
                        created_by_id=cortex,
                    )
                    .on_conflict_do_nothing()
                )
                provenance_rows: list[dict[str, object]] = [
                    {
                        "organization_id": org,
                        "page_version_id": first_version_id,
                        "source_id": memo_source,
                        "relationship": "derived_from",
                        "metadata": {"fact": "revenue"},
                    },
                    {
                        "organization_id": org,
                        "page_version_id": second_version_id,
                        "source_id": update_source,
                        "relationship": "derived_from",
                        "metadata": {"supersedes": "£42m"},
                    },
                    {
                        "organization_id": org,
                        "page_version_id": second_version_id,
                        "source_id": restricted_source,
                        "relationship": "corroborated_by",
                        "metadata": {},
                    },
                ]
                session.execute(
                    insert(model_table(PageVersionSource))
                    .values(provenance_rows)
                    .on_conflict_do_nothing()
                )
                current_version_id = second_version_id
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
