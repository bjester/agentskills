"""Tests for parser module."""

from pathlib import Path

import pytest

from skills_ref.parser import (
    ParseError,
    ReferenceStatus,
    ValidationError,
    find_skill_md,
    is_path_referenced,
    parse_frontmatter,
    read_properties,
    scan_skill_files,
)


def test_valid_frontmatter():
    content = """---
name: my-skill
description: A test skill
---
# My Skill

Instructions here.
"""
    metadata, body = parse_frontmatter(content)
    assert metadata["name"] == "my-skill"
    assert metadata["description"] == "A test skill"
    assert "# My Skill" in body


def test_missing_frontmatter():
    content = "# No frontmatter here"
    with pytest.raises(ParseError, match="must start with YAML frontmatter"):
        parse_frontmatter(content)


def test_unclosed_frontmatter():
    content = """---
name: my-skill
description: A test skill
"""
    with pytest.raises(ParseError, match="not properly closed"):
        parse_frontmatter(content)


def test_invalid_yaml():
    content = """---
name: [invalid
description: broken
---
Body here
"""
    with pytest.raises(ParseError, match="Invalid YAML"):
        parse_frontmatter(content)


def test_non_dict_frontmatter():
    content = """---
- just
- a
- list
---
Body
"""
    with pytest.raises(ParseError, match="must be a YAML mapping"):
        parse_frontmatter(content)


def test_read_valid_skill(tmp_path):
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: A test skill
license: MIT
---
# My Skill
""")
    props = read_properties(skill_dir)
    assert props.name == "my-skill"
    assert props.description == "A test skill"
    assert props.license == "MIT"


def test_read_with_metadata(tmp_path):
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: A test skill
metadata:
  author: Test Author
  version: 1.0
---
Body
""")
    props = read_properties(skill_dir)
    assert props.metadata == {"author": "Test Author", "version": "1.0"}


def test_missing_skill_md(tmp_path):
    with pytest.raises(ParseError, match="SKILL.md not found"):
        read_properties(tmp_path)


def test_missing_name(tmp_path):
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
description: A test skill
---
Body
""")
    with pytest.raises(ValidationError, match="Missing required field.*name"):
        read_properties(skill_dir)


def test_missing_description(tmp_path):
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
---
Body
""")
    with pytest.raises(ValidationError, match="Missing required field.*description"):
        read_properties(skill_dir)


def test_find_skill_md_prefers_uppercase(tmp_path):
    """SKILL.md should be preferred over skill.md when both exist."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("uppercase")
    (skill_dir / "skill.md").write_text("lowercase")
    result = find_skill_md(skill_dir)
    assert result is not None
    assert result.name == "SKILL.md"


def test_find_skill_md_accepts_lowercase(tmp_path):
    """skill.md should be accepted when SKILL.md doesn't exist."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "skill.md").write_text("lowercase")
    result = find_skill_md(skill_dir)
    assert result is not None
    # Check case-insensitively since some filesystems are case-insensitive
    assert result.name.lower() == "skill.md"


def test_find_skill_md_returns_none_when_missing(tmp_path):
    """find_skill_md should return None when no skill.md exists."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    result = find_skill_md(skill_dir)
    assert result is None


def test_read_properties_with_lowercase_skill_md(tmp_path):
    """read_properties should work with lowercase skill.md."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "skill.md").write_text("""---
name: my-skill
description: A test skill
---
# My Skill
""")
    props = read_properties(skill_dir)
    assert props.name == "my-skill"
    assert props.description == "A test skill"


def test_read_with_allowed_tools(tmp_path):
    """allowed-tools should be parsed into SkillProperties."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: A test skill
allowed-tools: Bash(jq:*) Bash(git:*)
---
Body
""")
    props = read_properties(skill_dir)
    assert props.allowed_tools == "Bash(jq:*) Bash(git:*)"
    # Verify to_dict outputs as "allowed-tools" (hyphenated)
    d = props.to_dict()
    assert d["allowed-tools"] == "Bash(jq:*) Bash(git:*)"


def test_scan_skill_files_finds_all_files(tmp_path):
    """scan_skill_files should find all files in skill directory."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    refs_dir = skill_dir / "references"
    refs_dir.mkdir()
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir()

    (refs_dir / "GUIDE.md").write_text("# Guide")
    (refs_dir / "FORMS.md").write_text("# Forms")
    (scripts_dir / "run.py").write_text("# Script")
    (skill_dir / "SKILL.md").write_text("# Skill")

    files = scan_skill_files(skill_dir)

    assert len(files) == 3
    assert Path("references/GUIDE.md") in files
    assert Path("references/FORMS.md") in files
    assert Path("scripts/run.py") in files


def test_scan_skill_files_excludes_skill_md(tmp_path):
    """scan_skill_files should exclude SKILL.md files."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Skill")
    (skill_dir / "skill.md").write_text("# Skill lowercase")

    files = scan_skill_files(skill_dir)

    assert len(files) == 0


def test_scan_skill_files_excludes_hidden_files(tmp_path):
    """scan_skill_files should exclude hidden files."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / ".hidden").write_text("hidden")
    (skill_dir / "visible.txt").write_text("visible")

    files = scan_skill_files(skill_dir)

    assert len(files) == 1
    assert Path("visible.txt") in files


def test_scan_skill_files_excludes_venv(tmp_path):
    """scan_skill_files should exclude virtual environment directories."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    venv_dir = skill_dir / ".venv"
    venv_dir.mkdir()
    (venv_dir / "site-packages.py").write_text("venv file")
    (skill_dir / "script.py").write_text("skill file")

    files = scan_skill_files(skill_dir)

    assert len(files) == 1
    assert Path("script.py") in files


def test_scan_skill_files_empty_dir(tmp_path):
    """scan_skill_files should return empty list for empty directory."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()

    files = scan_skill_files(skill_dir)

    assert files == []


def test_is_path_referenced_markdown_link():
    """is_path_referenced should find paths in markdown links."""
    body = "See [the guide](references/GUIDE.md) for details."
    assert (
        is_path_referenced(body, Path("references/GUIDE.md")) == ReferenceStatus.found
    )


def test_is_path_referenced_inline_code():
    """is_path_referenced should find paths in inline code."""
    body = "Run `scripts/run.py` to execute."
    assert is_path_referenced(body, Path("scripts/run.py")) == ReferenceStatus.found


def test_is_path_referenced_bare_text():
    """is_path_referenced should find paths as bare text."""
    body = "Run scripts/run.py to execute."
    assert is_path_referenced(body, Path("scripts/run.py")) == ReferenceStatus.found


def test_is_path_referenced_nested_path_bare_text():
    """is_path_referenced should find nested paths in bare text."""
    body = "See docs/sub/GUIDE.md for details."
    assert is_path_referenced(body, Path("docs/sub/GUIDE.md")) == ReferenceStatus.found


def test_is_path_referenced_nested_path_markdown_link():
    """is_path_referenced should find nested paths in markdown links."""
    body = "See [the guide](docs/sub/GUIDE.md) for details."
    assert is_path_referenced(body, Path("docs/sub/GUIDE.md")) == ReferenceStatus.found


def test_is_path_referenced_not_found():
    """is_path_referenced should return orphaned for missing paths."""
    body = "This body has no file references."
    assert (
        is_path_referenced(body, Path("references/GUIDE.md"))
        == ReferenceStatus.orphaned
    )


def test_is_path_referenced_partial_match_not_found():
    """is_path_referenced should return orphaned for partial path matches."""
    body = "Run scripts/other.py instead."
    assert is_path_referenced(body, Path("scripts/run.py")) == ReferenceStatus.orphaned


def test_is_path_referenced_windows_path_separator():
    """is_path_referenced should handle Windows-style path separators."""
    # Body uses backslashes, search uses forward slashes
    body = "See [guide](references\\GUIDE.md) for details."
    assert (
        is_path_referenced(body, Path("references/GUIDE.md")) == ReferenceStatus.found
    )


def test_is_path_referenced_broken_path():
    """is_path_referenced should return broken_path for mismatched paths."""
    # Path exists but body has different path with same basename
    body = "See [guide](docs/GUIDE.md) for details."
    assert (
        is_path_referenced(body, Path("references/GUIDE.md"))
        == ReferenceStatus.broken_path
    )


def test_is_path_referenced_relocated():
    """is_path_referenced should return broken_path for possibly relocated paths."""
    # Path exists but body has different path with same basename
    body = "See [guide](docs/GUIDE.md) for details."
    assert is_path_referenced(body, Path("GUIDE.md")) == ReferenceStatus.broken_path
    body = "See docs/GUIDE.md for details."
    assert is_path_referenced(body, Path("GUIDE.md")) == ReferenceStatus.broken_path


def test_is_path_referenced_relocated2():
    """is_path_referenced should return broken_path for possibly relocated paths."""
    # Path exists but body has different path with same basename
    body = "See [guide](GUIDE.md) for details."
    assert (
        is_path_referenced(body, Path("docs/GUIDE.md")) == ReferenceStatus.broken_path
    )
    body = "See GUIDE.md for details."
    assert (
        is_path_referenced(body, Path("docs/GUIDE.md")) == ReferenceStatus.broken_path
    )
