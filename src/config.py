"""Configuration: project paths, model, .env loading, reading prompts and the CV."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Repository root — one level above src/
ROOT = Path(__file__).resolve().parent.parent
SRC = Path(__file__).resolve().parent

CV_PATH = ROOT / "docs" / "cv.txt"
REPORTS_DIR = ROOT / "reports"
PROMPTS_DIR = SRC / "prompts"

# Default Claude model — override via ANTHROPIC_CHAT_MODEL.
CHAT_MODEL = os.getenv("ANTHROPIC_CHAT_MODEL", "claude-sonnet-4-5-20250929")


def load_prompt(name: str) -> str:
    """Read a role's system prompt from src/prompts/<name>.md."""
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def read_cv() -> str:
    """Read the candidate's CV — the source of truth about the profile (as in the Claude Code version)."""
    if not CV_PATH.exists():
        raise FileNotFoundError(
            f"CV not found: {CV_PATH}. Put your resume in docs/cv.txt"
        )
    return CV_PATH.read_text(encoding="utf-8")
