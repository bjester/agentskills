"""Skill validation logic."""

import unicodedata
from pathlib import Path
from typing import Optional

from .errors import ParseError
from .parser import (
    find_skill_md,
    is_path_referenced,
    parse_frontmatter,
    scan_skill_files,
    ReferenceStatus,
)

MAX_SKILL_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500

# Allowed frontmatter fields per Agent Skills Spec
ALLOWED_FIELDS = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}


def _validate_name(name: str, skill_dir: Path) -> list[str]:
    """Validate skill name format and directory match.

    Skill names support i18n characters (Unicode letters) plus hyphens.
    Names must be lowercase and cannot start/end with hyphens.
    """
    errors = []

    if not name or not isinstance(name, str) or not name.strip():
        errors.append("Field 'name' must be a non-empty string")
        return errors

    name = unicodedata.normalize("NFKC", name.strip())

    if len(name) > MAX_SKILL_NAME_LENGTH:
        errors.append(
            f"Skill name '{name}' exceeds {MAX_SKILL_NAME_LENGTH} character limit "
            f"({len(name)} chars)"
        )

    if name != name.lower():
        errors.append(f"Skill name '{name}' must be lowercase")

    if name.startswith("-") or name.endswith("-"):
        errors.append("Skill name cannot start or end with a hyphen")

    if "--" in name:
        errors.append("Skill name cannot contain consecutive hyphens")

    if not all(c.isalnum() or c == "-" for c in name):
        errors.append(
            f"Skill name '{name}' contains invalid characters. "
            "Only letters, digits, and hyphens are allowed."
        )

    if skill_dir:
        dir_name = unicodedata.normalize("NFKC", skill_dir.name)
        if dir_name != name:
            errors.append(
                f"Directory name '{skill_dir.name}' must match skill name '{name}'"
            )

    return errors


def _validate_description(description: str) -> list[str]:
    """Validate description format."""
    errors = []

    if not description or not isinstance(description, str) or not description.strip():
        errors.append("Field 'description' must be a non-empty string")
        return errors

    if len(description) > MAX_DESCRIPTION_LENGTH:
        errors.append(
            f"Description exceeds {MAX_DESCRIPTION_LENGTH} character limit "
            f"({len(description)} chars)"
        )

    return errors


def _validate_compatibility(compatibility: str) -> list[str]:
    """Validate compatibility format."""
    errors = []

    if not isinstance(compatibility, str):
        errors.append("Field 'compatibility' must be a string")
        return errors

    if len(compatibility) > MAX_COMPATIBILITY_LENGTH:
        errors.append(
            f"Compatibility exceeds {MAX_COMPATIBILITY_LENGTH} character limit "
            f"({len(compatibility)} chars)"
        )

    return errors


def _validate_metadata_fields(metadata: dict) -> list[str]:
    """Validate that only allowed fields are present."""
    errors = []

    extra_fields = set(metadata.keys()) - ALLOWED_FIELDS
    if extra_fields:
        errors.append(
            f"Unexpected fields in frontmatter: {', '.join(sorted(extra_fields))}. "
            f"Only {sorted(ALLOWED_FIELDS)} are allowed."
        )

    return errors


def validate_metadata(metadata: dict, skill_dir: Optional[Path] = None) -> list[str]:
    """Validate parsed skill metadata.

    This is the core validation function that works on already-parsed metadata,
    avoiding duplicate file I/O when called from the parser.

    Args:
        metadata: Parsed YAML frontmatter dictionary
        skill_dir: Optional path to skill directory (for name-directory match check)

    Returns:
        List of validation error messages. Empty list means valid.
    """
    errors = []
    errors.extend(_validate_metadata_fields(metadata))

    if "name" not in metadata:
        errors.append("Missing required field in frontmatter: name")
    else:
        errors.extend(_validate_name(metadata["name"], skill_dir))

    if "description" not in metadata:
        errors.append("Missing required field in frontmatter: description")
    else:
        errors.extend(_validate_description(metadata["description"]))

    if "compatibility" in metadata:
        errors.extend(_validate_compatibility(metadata["compatibility"]))

    return errors


def _track_reference_status(
    files: list[Path],
    current_file: Path,
    body: str,
    file_statuses: dict[Path, set[ReferenceStatus]],
    all_errors: list[str],
) -> None:
    """Check references in a body and update tracking dicts.

    Args:
        files: List of skill files to check
        current_file: File currently being checked
        body: Body content of the current file to search for references
        file_statuses: Dict tracking status per file (modified in place)
        all_errors: List of broken path errors (modified in place)
    """
    for rel_path in files:
        if rel_path == current_file:
            continue
        result = is_path_referenced(body, rel_path)
        file_statuses[rel_path].add(result)
        if result == ReferenceStatus.broken_path:
            all_errors.append(
                f"File {current_file} has broken path reference to: {rel_path}"
            )


def validate_skill_references(
    skill_dir: Path, body: str
) -> tuple[list[str], list[str]]:
    """Validate references in SKILL.md and all other skill files.

    Tracks orphaned files across ALL files - a file is only orphaned if it's not
    referenced in ANY skill file (SKILL.md or other referenced files).

    Args:
        skill_dir: Path to the skill directory
        body: Markdown body content from SKILL.md

    Returns:
        Tuple of (warnings, errors):
        - warnings: Files orphaned across all skill files
        - errors: Broken path references from any file
    """
    files = scan_skill_files(skill_dir)

    # Track reference status for each file across all bodies checked
    # Key: rel_path, Value: set of ReferenceStatus seen
    file_statuses: dict[Path, set[ReferenceStatus]] = {f: set() for f in files}

    all_errors: list[str] = []

    # Check main SKILL.md body
    _track_reference_status(files, Path(find_skill_md(skill_dir).name), body, file_statuses, all_errors)

    # Check other skill files for references
    for rel_path in files:
        file_path = skill_dir / rel_path
        try:
            content = file_path.read_text(encoding="utf-8")
            # Check for NULL bytes which might indicate binary
            if "\0" in content:
                continue
            _track_reference_status(files, rel_path, content, file_statuses, all_errors)
        except UnicodeDecodeError:
            continue

    # Collect warnings: files that were orphaned in ALL checks
    all_warnings: list[str] = []
    for rel_path, statuses in file_statuses.items():
        # Only warn if file was never found (always orphaned)
        if (
            ReferenceStatus.found not in statuses
            and ReferenceStatus.broken_path not in statuses
        ):
            all_warnings.append(f"Orphaned file (not referenced): {rel_path}")

    return all_warnings, all_errors


def validate(skill_dir: Path) -> tuple[list[str], list[str]]:
    """Validate a skill directory.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        Tuple of (warnings, errors):
        - warnings: Orphaned files (not referenced in any skill file)
        - errors: Validation errors (invalid metadata, broken paths)
    """
    skill_dir = Path(skill_dir)

    if not skill_dir.exists():
        return [], [f"Path does not exist: {skill_dir}"]

    if not skill_dir.is_dir():
        return [], [f"Not a directory: {skill_dir}"]

    skill_md = find_skill_md(skill_dir)
    if skill_md is None:
        return [], ["Missing required file: SKILL.md"]

    try:
        content = skill_md.read_text()
        metadata, body = parse_frontmatter(content)
    except ParseError as e:
        return [], [str(e)]

    errors = validate_metadata(metadata, skill_dir)

    # Validate file references in SKILL.md and all other skill files
    ref_warnings, ref_errors = validate_skill_references(skill_dir, body)

    return ref_warnings, errors + ref_errors
