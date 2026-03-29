"""YAML frontmatter parsing for SKILL.md files."""

from enum import Enum
import re
from pathlib import Path
from typing import Optional

import strictyaml

from .errors import ParseError, ValidationError
from .models import SkillProperties


EXCLUDED_REFERENCE_DIRS = ("venv", "__pycache__", "node_modules")


def find_skill_md(skill_dir: Path) -> Optional[Path]:
    """Find the SKILL.md file in a skill directory.

    Prefers SKILL.md (uppercase) but accepts skill.md (lowercase).

    Args:
        skill_dir: Path to the skill directory

    Returns:
        Path to the SKILL.md file, or None if not found
    """
    for name in ("SKILL.md", "skill.md"):
        path = skill_dir / name
        if path.exists():
            return path
    return None


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from SKILL.md content.

    Args:
        content: Raw content of SKILL.md file

    Returns:
        Tuple of (metadata dict, markdown body)

    Raises:
        ParseError: If frontmatter is missing or invalid
    """
    if not content.startswith("---"):
        raise ParseError("SKILL.md must start with YAML frontmatter (---)")

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ParseError("SKILL.md frontmatter not properly closed with ---")

    frontmatter_str = parts[1]
    body = parts[2].strip()

    try:
        parsed = strictyaml.load(frontmatter_str)
        metadata = parsed.data
    except strictyaml.YAMLError as e:
        raise ParseError(f"Invalid YAML in frontmatter: {e}")

    if not isinstance(metadata, dict):
        raise ParseError("SKILL.md frontmatter must be a YAML mapping")

    if "metadata" in metadata and isinstance(metadata["metadata"], dict):
        metadata["metadata"] = {str(k): str(v) for k, v in metadata["metadata"].items()}

    return metadata, body


def read_properties(skill_dir: Path) -> SkillProperties:
    """Read skill properties from SKILL.md frontmatter.

    This function parses the frontmatter and returns properties.
    It does NOT perform full validation. Use validate() for that.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        SkillProperties with parsed metadata

    Raises:
        ParseError: If SKILL.md is missing or has invalid YAML
        ValidationError: If required fields (name, description) are missing
    """
    skill_dir = Path(skill_dir)
    skill_md = find_skill_md(skill_dir)

    if skill_md is None:
        raise ParseError(f"SKILL.md not found in {skill_dir}")

    content = skill_md.read_text()
    metadata, _ = parse_frontmatter(content)

    if "name" not in metadata:
        raise ValidationError("Missing required field in frontmatter: name")
    if "description" not in metadata:
        raise ValidationError("Missing required field in frontmatter: description")

    name = metadata["name"]
    description = metadata["description"]

    if not isinstance(name, str) or not name.strip():
        raise ValidationError("Field 'name' must be a non-empty string")
    if not isinstance(description, str) or not description.strip():
        raise ValidationError("Field 'description' must be a non-empty string")

    return SkillProperties(
        name=name.strip(),
        description=description.strip(),
        license=metadata.get("license"),
        compatibility=metadata.get("compatibility"),
        allowed_tools=metadata.get("allowed-tools"),
        metadata=metadata.get("metadata"),
    )


def _recurse_scan_skill_files(target_path: Path, relative_to: Path) -> list[Path]:
    """Recursively scan skill directory for all files (excluding SKILL.md).

    Returns relative paths from `relative_to`. Does not use `rglob` or `walk` to avoid unnecessary
    traversal of directories that would be excluded.

    Excludes:
    - SKILL.md / skill.md (the main instruction file)
    - Directories (only files)
    - Hidden files/directories (starting with .)
    - Symlinks

    Args:
        target_path: Path to the skill directory
        relative_to: The directory path to format paths relative to
    Returns:
        List of relative file paths (as Path objects)
    """
    files = []

    for path in target_path.glob("*"):
        # Skip files either hidden, underneath a hidden directory, or in excluded directories
        if path.name.startswith(".") or path.name.startswith(EXCLUDED_REFERENCE_DIRS):
            continue

        if path.is_symlink():
            continue

        rel_path = path.relative_to(relative_to)

        if path.is_dir():
            files.extend(_recurse_scan_skill_files(path, relative_to))
            continue

        # SKILL.md don't require references
        if path.name.lower() == "skill.md":
            continue

        files.append(rel_path)

    return files


def scan_skill_files(skill_dir: Path) -> list[Path]:
    """Scan skill directory for all files (excluding SKILL.md).

    Returns relative paths from skill root, e.g., ['references/GUIDE.md', 'scripts/run.py'].

    See also _recurse_scan_skill_files.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        List of relative file paths (as Path objects)
    """
    files = _recurse_scan_skill_files(skill_dir, skill_dir)
    return sorted(files, key=lambda p: str(p))


class ReferenceStatus(Enum):
    found = 0
    orphaned = 1
    broken_path = 2


def is_path_referenced(body: str, rel_path: Path) -> ReferenceStatus:
    """Check if a file path is referenced in the SKILL.md body.

    Searches for the path in multiple formats:
    - Markdown links: [text](path/to/file)
    - Inline code: `path/to/file`
    - Bare text: path/to/file (as standalone text)

    Normalizes Windows-style backslashes to forward slashes for comparison.

    Args:
        body: Markdown body content from SKILL.md
        rel_path: Relative path to search for (e.g., Path('references/GUIDE.md'))

    Returns:
        ReferenceStatus:
        - found: All references to this file use the correct path
        - broken_path: At least one reference uses a wrong path (e.g., docs/X.md vs references/X.md)
        - orphaned: File is not referenced at all
    """
    path_str_posix = rel_path.as_posix()
    path_str_basename = rel_path.name

    # Normalize body: replace backslashes with forward slashes
    normalized_body = body.replace("\\", "/")

    # Match path-like tokens ending in the basename.
    # Supports:
    # - basename only: GUIDE.md
    # - one or more parent dirs: docs/GUIDE.md, docs/sub/GUIDE.md
    token_pattern = re.compile(
        rf"(?<![A-Za-z0-9._/-])"
        rf"(?P<path>(?:[A-Za-z0-9._-]+/)*{re.escape(path_str_basename)})"
        rf"(?=$|[^A-Za-z0-9._/-])"
    )

    found_correct = False

    for match in token_pattern.finditer(normalized_body):
        candidate = match.group("path")
        if candidate == path_str_posix:
            found_correct = True
        else:
            # Same basename at a different relative path indicates a broken path.
            return ReferenceStatus.broken_path

    if found_correct:
        return ReferenceStatus.found
    else:
        return ReferenceStatus.orphaned
