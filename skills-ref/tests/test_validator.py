"""Tests for validator module."""

from skills_ref.validator import validate


def test_valid_skill(tmp_path):
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: A test skill
---
# My Skill
""")
    warnings, errors = validate(skill_dir)
    assert warnings == []
    assert errors == []


def test_nonexistent_path(tmp_path):
    warnings, errors = validate(tmp_path / "nonexistent")
    assert len(errors) == 1
    assert warnings == []
    assert "does not exist" in errors[0]


def test_not_a_directory(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("test")
    warnings, errors = validate(file_path)
    assert len(errors) == 1
    assert warnings == []
    assert "Not a directory" in errors[0]


def test_missing_skill_md(tmp_path):
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    warnings, errors = validate(skill_dir)
    assert len(errors) == 1
    assert warnings == []
    assert "Missing required file: SKILL.md" in errors[0]


def test_invalid_name_uppercase(tmp_path):
    skill_dir = tmp_path / "MySkill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: MySkill
description: A test skill
---
Body
""")
    warnings, errors = validate(skill_dir)
    assert any("lowercase" in e for e in errors)


def test_name_too_long(tmp_path):
    long_name = "a" * 70  # Exceeds 64 char limit
    skill_dir = tmp_path / long_name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(f"""---
name: {long_name}
description: A test skill
---
Body
""")
    warnings, errors = validate(skill_dir)
    assert any("exceeds" in e and "character limit" in e for e in errors)


def test_name_leading_hyphen(tmp_path):
    skill_dir = tmp_path / "-my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: -my-skill
description: A test skill
---
Body
""")
    warnings, errors = validate(skill_dir)
    assert any("cannot start or end with a hyphen" in e for e in errors)


def test_name_consecutive_hyphens(tmp_path):
    skill_dir = tmp_path / "my--skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: my--skill
description: A test skill
---
Body
""")
    warnings, errors = validate(skill_dir)
    assert any("consecutive hyphens" in e for e in errors)


def test_name_invalid_characters(tmp_path):
    skill_dir = tmp_path / "my_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: my_skill
description: A test skill
---
Body
""")
    warnings, errors = validate(skill_dir)
    assert any("invalid characters" in e for e in errors)


def test_name_directory_mismatch(tmp_path):
    skill_dir = tmp_path / "wrong-name"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: correct-name
description: A test skill
---
Body
""")
    warnings, errors = validate(skill_dir)
    assert any("must match skill name" in e for e in errors)


def test_unexpected_fields(tmp_path):
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: A test skill
unknown_field: should not be here
---
Body
""")
    warnings, errors = validate(skill_dir)
    assert any("Unexpected fields" in e for e in errors)


def test_valid_with_all_fields(tmp_path):
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: A test skill
license: MIT
metadata:
  author: Test
---
Body
""")
    warnings, errors = validate(skill_dir)
    assert warnings == []
    assert errors == []


def test_allowed_tools_accepted(tmp_path):
    """allowed-tools is accepted (experimental feature)."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: A test skill
allowed-tools: Bash(jq:*) Bash(git:*)
---
Body
""")
    warnings, errors = validate(skill_dir)
    assert warnings == []
    assert errors == []


def test_i18n_chinese_name(tmp_path):
    """Chinese characters are allowed in skill names."""
    skill_dir = tmp_path / "技能"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: 技能
description: A skill with Chinese name
---
Body
""")
    warnings, errors = validate(skill_dir)
    assert warnings == []
    assert errors == []


def test_i18n_russian_name_with_hyphens(tmp_path):
    """Russian names with hyphens are allowed."""
    skill_dir = tmp_path / "мой-навык"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: мой-навык
description: A skill with Russian name
---
Body
""")
    warnings, errors = validate(skill_dir)
    assert warnings == []
    assert errors == []


def test_i18n_russian_lowercase_valid(tmp_path):
    """Russian lowercase names should be accepted."""
    skill_dir = tmp_path / "навык"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: навык
description: A skill with Russian lowercase name
---
Body
""")
    warnings, errors = validate(skill_dir)
    assert warnings == []
    assert errors == []


def test_i18n_russian_uppercase_rejected(tmp_path):
    """Russian uppercase names should be rejected."""
    skill_dir = tmp_path / "НАВЫК"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: НАВЫК
description: A skill with Russian uppercase name
---
Body
""")
    warnings, errors = validate(skill_dir)
    assert any("lowercase" in e for e in errors)


def test_description_too_long(tmp_path):
    """Description exceeding 1024 chars should fail."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    long_desc = "x" * 1100
    (skill_dir / "SKILL.md").write_text(f"""---
name: my-skill
description: {long_desc}
---
Body
""")
    warnings, errors = validate(skill_dir)
    assert any("exceeds" in e and "1024" in e for e in errors)


def test_valid_compatibility(tmp_path):
    """Valid compatibility field should be accepted."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: A test skill
compatibility: Requires Python 3.11+
---
Body
""")
    warnings, errors = validate(skill_dir)
    assert warnings == []
    assert errors == []


def test_compatibility_too_long(tmp_path):
    """Compatibility exceeding 500 chars should fail."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    long_compat = "x" * 550
    (skill_dir / "SKILL.md").write_text(f"""---
name: my-skill
description: A test skill
compatibility: {long_compat}
---
Body
""")
    warnings, errors = validate(skill_dir)
    assert any("exceeds" in e and "500" in e for e in errors)


def test_nfkc_normalization(tmp_path):
    """Skill names are NFKC normalized before validation.

    The name 'café' can be represented two ways:
    - Precomposed: 'café' (4 chars, 'é' is U+00E9)
    - Decomposed: 'café' (5 chars, 'e' + combining acute U+0301)

    NFKC normalizes both to the precomposed form.
    """
    # Use decomposed form: 'cafe' + combining acute accent (U+0301)
    decomposed_name = "cafe\u0301"  # 'café' with combining accent
    composed_name = "café"  # precomposed form

    # Directory uses composed form, SKILL.md uses decomposed - should match after normalization
    skill_dir = tmp_path / composed_name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(f"""---
name: {decomposed_name}
description: A test skill
---
Body
""")
    warnings, errors = validate(skill_dir)
    assert warnings == []
    assert errors == [], f"Expected no errors, got: {errors}"


def test_all_files_referenced(tmp_path):
    """All files in skill directory should be referenced."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    refs_dir = skill_dir / "references"
    refs_dir.mkdir()
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir()

    (refs_dir / "GUIDE.md").write_text("# Guide")
    (scripts_dir / "run.py").write_text("# Script")

    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: A test skill
---
See [the guide](references/GUIDE.md) and run `scripts/run.py`.
""")
    warnings, errors = validate(skill_dir)
    assert warnings == []
    assert errors == []


def test_orphaned_file_warning(tmp_path):
    """Unreferenced files should generate warnings."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    refs_dir = skill_dir / "references"
    refs_dir.mkdir()

    (refs_dir / "GUIDE.md").write_text("# Guide")
    (refs_dir / "UNUSED.md").write_text("# Unused")

    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: A test skill
---
See [the guide](references/GUIDE.md) for details.
""")
    warnings, errors = validate(skill_dir)
    assert len(warnings) == 1
    assert "Orphaned file" in warnings[0]
    assert "references/UNUSED.md" in warnings[0]


def test_multiple_orphaned_files(tmp_path):
    """Multiple orphaned files should all be reported."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    refs_dir = skill_dir / "references"
    refs_dir.mkdir()
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir()

    (refs_dir / "UNUSED1.md").write_text("# Unused 1")
    (refs_dir / "UNUSED2.md").write_text("# Unused 2")
    (scripts_dir / "orphan.py").write_text("# Orphan")

    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: A test skill
---
No file references here.
""")
    warnings, errors = validate(skill_dir)
    assert len(warnings) == 3
    assert any("UNUSED1.md" in w for w in warnings)
    assert any("UNUSED2.md" in w for w in warnings)
    assert any("orphan.py" in w for w in warnings)


def test_example_paths_not_flagged(tmp_path):
    """Example paths in skill body should not cause false positives."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()

    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: A test skill
---
Example usage:

```
python scripts/example.py --input data/file.txt
```

This is just an example, the files don't need to exist.
""")
    warnings, errors = validate(skill_dir)
    assert warnings == []
    assert errors == []


def test_hidden_files_ignored(tmp_path):
    """Hidden files should be ignored in validation."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / ".hidden").write_text("hidden content")
    (skill_dir / ".gitignore").write_text("*.pyc")

    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: A test skill
---
No file references.
""")
    warnings, errors = validate(skill_dir)
    assert warnings == []
    assert errors == []


def test_deep_hidden_files_ignored(tmp_path):
    """Deeply hidden or excluded files should be ignored in validation."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    ref_dir = skill_dir / "references"
    ref_dir.mkdir()
    (ref_dir / ".hidden").write_text("hidden content")
    (ref_dir / ".gitignore").write_text("*.pyc")
    deep_dir = ref_dir / "node_modules"
    deep_dir.mkdir()
    (deep_dir / "todo").write_text("excluded content")

    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: A test skill
---
No file references.
""")
    warnings, errors = validate(skill_dir)
    assert warnings == []
    assert errors == []


def test_venv_files_ignored(tmp_path):
    """Virtual environment files should be ignored."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    venv_dir = skill_dir / "venv"
    venv_dir.mkdir()
    (venv_dir / "script.py").write_text("# venv script")

    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: A test skill
---
No file references.
""")
    warnings, errors = validate(skill_dir)
    assert warnings == []
    assert errors == []


def test_file_referenced_in_other_skill_file(tmp_path):
    """File orphaned in SKILL.md but referenced in another skill file should not warn."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    refs_dir = skill_dir / "references"
    refs_dir.mkdir()
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir()

    # Create a reference file
    (refs_dir / "GUIDE.md").write_text("# Guide")
    # Create a script that references the guide
    (scripts_dir / "run.py").write_text("# Script\n# See references/GUIDE.md")
    # Orphan file not referenced anywhere
    (refs_dir / "UNUSED.md").write_text("# Unused")

    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: A test skill
---
Run `scripts/run.py` to execute.
""")
    warnings, errors = validate(skill_dir)
    # GUIDE.md is referenced in run.py, so should NOT be orphaned
    # UNUSED.md is truly orphaned
    assert len(warnings) == 1
    assert "UNUSED.md" in warnings[0]
    assert "GUIDE.md" not in warnings[0]
