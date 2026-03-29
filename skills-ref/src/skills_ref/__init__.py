"""Reference library for Agent Skills."""

from .errors import ParseError, SkillError, ValidationError
from .models import SkillProperties
from .parser import find_skill_md, is_path_referenced, read_properties, scan_skill_files
from .prompt import to_prompt
from .validator import validate

__all__ = [
    "SkillError",
    "ParseError",
    "ValidationError",
    "SkillProperties",
    "find_skill_md",
    "scan_skill_files",
    "is_path_referenced",
    "validate",
    "read_properties",
    "to_prompt",
]

__version__ = "0.1.0"
