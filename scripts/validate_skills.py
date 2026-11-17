from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / ".agents" / "skills"
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def skill_frontmatter(path: Path) -> tuple[dict[str, object] | None, list[str]]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None, [f"{path.relative_to(ROOT)}: missing YAML frontmatter opener"]
    parts = text.split("---", 2)
    if len(parts) != 3:
        return None, [f"{path.relative_to(ROOT)}: missing YAML frontmatter closer"]
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        return None, [f"{path.relative_to(ROOT)}: invalid YAML frontmatter ({exc})"]
    if not isinstance(data, dict):
        return None, [f"{path.relative_to(ROOT)}: frontmatter must be a mapping"]
    return data, []


def markdown_links(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [target for _, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text)]


def validate() -> list[str]:
    issues: list[str] = []
    skill_files = sorted(SKILLS_ROOT.glob("*/SKILL.md"))
    if not skill_files:
        return ["No project-local SKILL.md files found"]

    names: dict[str, Path] = {}
    for skill_file in skill_files:
        metadata, errors = skill_frontmatter(skill_file)
        issues.extend(errors)
        if metadata is None:
            continue
        name = metadata.get("name")
        description = metadata.get("description")
        relative = skill_file.relative_to(ROOT)
        if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
            issues.append(f"{relative}: name must be lowercase kebab-case")
        else:
            if name != skill_file.parent.name:
                issues.append(f"{relative}: skill name does not match its directory")
            if name in names:
                issues.append(f"{relative}: duplicate skill name also used by {names[name].relative_to(ROOT)}")
            names[name] = skill_file
        if not isinstance(description, str) or not description.strip():
            issues.append(f"{relative}: description must be a non-empty string")

        for markdown_file in sorted(skill_file.parent.rglob("*.md")):
            for target in markdown_links(markdown_file):
                parsed = urlsplit(target)
                if parsed.scheme or target.startswith("#"):
                    continue
                destination = (markdown_file.parent / parsed.path).resolve()
                if parsed.path and not destination.is_file():
                    issues.append(
                        f"{markdown_file.relative_to(ROOT)}: broken local link {target}"
                    )

    return issues


def main() -> int:
    issues = validate()
    count = len(list(SKILLS_ROOT.glob("*/SKILL.md")))
    if issues:
        print("Skill validation failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print(f"Validated {count} project-local skills: unique names and local Markdown links are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
