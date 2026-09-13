from pathlib import Path
from shutil import copytree

import pytest

from brain_db.defaults import load_default_bundle
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
    (tmp_path / "manifest.yaml").write_text(
        "version: 1\nskills:\n  - slug: index\n    name: Index\n"
        "    file: ../outside.md\n    position: 1\n"
    )
    (tmp_path.parent / "outside.md").write_text(valid_document())

    with pytest.raises(ValueError, match="within the bundle"):
        load_default_bundle(tmp_path)


def test_default_bundle_rejects_broken_tool_and_route_contracts(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "content" / "default"
    broken_tool = tmp_path / "broken-tool"
    copytree(source, broken_tool)
    ingest = broken_tool / "skills" / "ingest.md"
    ingest.write_text(ingest.read_text().replace("  - create_source", "  - unavailable_tool"))
    with pytest.raises(ValueError, match="unavailable tools"):
        load_default_bundle(broken_tool)

    broken_route = tmp_path / "broken-route"
    copytree(source, broken_route)
    index = broken_route / "skills" / "index.md"
    index.write_text(index.read_text().replace("inputs: [source, pages]", "inputs: [source]"))
    with pytest.raises(ValueError, match="inputs do not match"):
        load_default_bundle(broken_route)
