from typing import cast

import yaml


class InvalidSkillDocument(ValueError):
    """Raised when a Skill document does not have a valid execution contract."""


def parse_skill_document(markdown: str) -> dict[str, object]:
    """Validate and return a Skill document's YAML frontmatter."""
    lines = markdown.splitlines()
    if not lines or lines[0] != "---":
        raise InvalidSkillDocument("Skill content must start with YAML frontmatter")
    try:
        closing = lines.index("---", 1)
    except ValueError as error:
        raise InvalidSkillDocument("Skill frontmatter is not closed") from error
    if closing == 1 or not any(line.strip() for line in lines[closing + 1 :]):
        raise InvalidSkillDocument("Skill frontmatter and Markdown body are required")
    try:
        loaded: object = yaml.safe_load("\n".join(lines[1:closing]))
    except yaml.YAMLError as error:
        raise InvalidSkillDocument("Skill frontmatter is not valid YAML") from error
    if not isinstance(loaded, dict):
        raise InvalidSkillDocument("Skill frontmatter must be a string-keyed mapping")
    raw_frontmatter = cast(dict[object, object], loaded)
    if not all(isinstance(key, str) for key in raw_frontmatter):
        raise InvalidSkillDocument("Skill frontmatter must be a string-keyed mapping")
    frontmatter = cast(dict[str, object], raw_frontmatter)
    for field in ("name", "description"):
        value = frontmatter.get(field)
        if not isinstance(value, str) or not value.strip():
            raise InvalidSkillDocument(f"Skill frontmatter field '{field}' must be non-blank")
    for field in ("inputs", "outputs"):
        value = frontmatter.get(field)
        if not isinstance(value, dict):
            raise InvalidSkillDocument(f"Skill frontmatter field '{field}' must be a mapping")
        raw_definitions = cast(dict[object, object], value)
        if not all(
            isinstance(key, str) and isinstance(definition, dict)
            for key, definition in raw_definitions.items()
        ):
            raise InvalidSkillDocument(f"Skill frontmatter field '{field}' must be a mapping")
        for raw_definition in raw_definitions.values():
            definition = cast(dict[object, object], raw_definition)
            type_name = definition.get("type")
            if not isinstance(type_name, str) or not type_name.strip():
                raise InvalidSkillDocument(f"Every '{field}' entry must declare a type")
            if "required" in definition and not isinstance(definition["required"], bool):
                raise InvalidSkillDocument("Skill input/output 'required' values must be booleans")
    tools = frontmatter.get("tools")
    if not isinstance(tools, list):
        raise InvalidSkillDocument("Skill frontmatter field 'tools' must be a list of names")
    raw_tools = cast(list[object], tools)
    if not all(isinstance(tool, str) and tool.strip() for tool in raw_tools):
        raise InvalidSkillDocument("Skill frontmatter field 'tools' must be a list of names")
    return frontmatter
