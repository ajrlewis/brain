from pathlib import Path
from shutil import copytree

import pytest
import yaml

from brain_db.defaults import load_default_bundle
from brain_db.seed import load_northstar_bundle
from brain_schemas import InvalidSkillDocument, parse_skill_document


def valid_document(frontmatter: str = "") -> str:
    return f"""---
name: test
description: Test document.
inputs: {{}}
outputs: {{}}
tools: []
{frontmatter}---

# Test
"""


def test_default_bundle_is_complete_reachable_and_uses_available_tools() -> None:
    bundle = load_default_bundle()

    assert [skill.slug for skill in bundle] == ["index", "ingest", "retrieve", "update", "lint"]
    assert all(len(skill.content_hash) == 64 for skill in bundle)
    assert [skill.content_hash for skill in bundle] == [
        "234854efe3158ebe8a670ba370ee13d034cad4bceda998744f9a2643a65791a5",
        "638608dba2408f8a1072bbabfff7b83d3d724cfabf27145dfdced18259260e4a",
        "46a98b2ea6c597841b9c37bea9d847b728ecacff2cb42435ea1ad7f8e80a9c6a",
        "2e9d15d279747b0d497d67ae3a320e31ba1a848a82452e135446be74031a843d",
        "8ae0fe88c45e3afc1179c8ae51eaea7516f26c81d9fa3642cda4537ebb038f7b",
    ]
    assert [reference.path for reference in bundle[0].references] == [
        "skills/index/references/governance.md"
    ]
    assert len(bundle[0].references[0].content_hash) == 64


@pytest.mark.parametrize(
    "markdown, message",
    [
        ("# Missing", "start"),
        ("---\nname: test", "not closed"),
        ("---\n---\n# Empty", "frontmatter and Markdown body"),
        ("---\nname: [\n---\n# Bad", "not valid YAML"),
        (valid_document().replace("description: Test document.\n", ""), "description"),
        (valid_document().replace("inputs: {}", "inputs: []"), "inputs"),
        (valid_document().replace("outputs: {}", "outputs:\n  result: {}"), "declare a type"),
        (valid_document().replace("tools: []", "tools: [1]"), "list of names"),
    ],
)
def test_skill_document_validation_rejects_broken_contracts(markdown: str, message: str) -> None:
    with pytest.raises(InvalidSkillDocument, match=message):
        parse_skill_document(markdown)


def test_default_bundle_rejects_manifest_outside_bundle(tmp_path: Path) -> None:
    (tmp_path / "skills" / "index").mkdir(parents=True)
    (tmp_path / "manifest.yaml").write_text(
        "bundle: brain-default-skills\nversion: 1\nskills:\n"
        "  - slug: index\n    name: Index\n"
        "    file: skills/index/SKILL.md\n    position: 1\n"
    )
    (tmp_path.parent / "outside.md").write_text(valid_document())
    (tmp_path / "skills" / "index" / "SKILL.md").symlink_to(tmp_path.parent / "outside.md")

    with pytest.raises(ValueError, match="within the bundle"):
        load_default_bundle(tmp_path)


def test_default_bundle_rejects_broken_tool_and_route_contracts(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "content" / "default"
    broken_tool = tmp_path / "broken-tool"
    copytree(source, broken_tool)
    ingest = broken_tool / "skills" / "ingest" / "SKILL.md"
    ingest.write_text(ingest.read_text().replace("  - create_source", "  - unavailable_tool"))
    with pytest.raises(ValueError, match="unavailable tools"):
        load_default_bundle(broken_tool)

    broken_route = tmp_path / "broken-route"
    copytree(source, broken_route)
    index = broken_route / "skills" / "index" / "SKILL.md"
    index.write_text(index.read_text().replace("inputs: [source, pages]", "inputs: [source]"))
    with pytest.raises(ValueError, match="inputs do not match"):
        load_default_bundle(broken_route)


def test_default_bundle_rejects_malformed_manifest_and_undeclared_traversal(
    tmp_path: Path,
) -> None:
    malformed = tmp_path / "malformed"
    malformed.mkdir()
    (malformed / "manifest.yaml").write_text("skills: [\n")
    with pytest.raises(ValueError, match="valid YAML"):
        load_default_bundle(malformed)

    source = Path(__file__).resolve().parents[2] / "content" / "default"
    traversed = tmp_path / "traversed"
    copytree(source, traversed)
    (traversed / "skills" / "index" / "undeclared.md").write_text("# Undeclared\n")
    with pytest.raises(ValueError, match="undeclared"):
        load_default_bundle(traversed)


def test_northstar_bundle_resolves_reviewable_text_and_rejects_bad_references(
    tmp_path: Path,
) -> None:
    bundle = load_northstar_bundle()

    assert len(bundle.documents) == 6
    assert "£42m" in bundle.documents["documents/portfolio/orion-investment-memo.md"]
    assert "superseded" in bundle.documents["documents/portfolio/orion-operating-update.md"]

    source = Path(__file__).resolve().parents[2] / "examples" / "northstar"
    broken = tmp_path / "northstar"
    copytree(source, broken)
    manifest = broken / "seed" / "manifest.yaml"
    manifest.write_text(manifest.read_text().replace("folder:people", "folder:missing", 1))
    with pytest.raises(ValueError, match="does not resolve"):
        load_northstar_bundle(broken)


def test_dummy_fixture_is_content_only_and_provider_neutral() -> None:
    root = Path(__file__).resolve().parents[1] / "fixtures" / "dummy"
    loaded = yaml.safe_load((root / "manifest.yaml").read_text())

    assert loaded["bundle"] == "brain-dummy-test-content"
    assert set(path.suffix for path in root.rglob("*") if path.is_file()) <= {"", ".md", ".yaml"}
    skill = (root / loaded["skills"][0]["file"]).read_text()
    assert parse_skill_document(skill)["name"] == "sample-skill"
    all_content = "\n".join(path.read_text() for path in root.rglob("*") if path.is_file())
    assert "Northstar" not in all_content
