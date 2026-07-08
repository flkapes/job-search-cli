"""Language registry: run commands, availability checks, and editor metadata."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class LanguageSpec:
    id: str
    name: str
    file_name: str          # display name in the editor header
    editor_language: str    # Textual TextArea syntax id
    code_fence: str         # markdown fence tag for prompts


LANGUAGES: dict[str, LanguageSpec] = {
    "python": LanguageSpec("python", "Python", "solution.py", "python", "python"),
    "javascript": LanguageSpec("javascript", "JavaScript", "solution.js", "javascript", "javascript"),
    "go": LanguageSpec("go", "Go", "main.go", "go", "go"),
}

DEFAULT_LANGUAGE = "python"


def get_language(language_id: str) -> LanguageSpec:
    return LANGUAGES.get(language_id, LANGUAGES[DEFAULT_LANGUAGE])


def is_language_available(language_id: str) -> bool:
    """Whether the interpreter/toolchain for a language is installed."""
    if language_id == "python":
        return True
    if language_id == "javascript":
        return shutil.which("node") is not None
    if language_id == "go":
        return shutil.which("go") is not None
    return False


def available_languages() -> list[LanguageSpec]:
    return [spec for lang_id, spec in LANGUAGES.items() if is_language_available(lang_id)]


def build_run_command(code: str, language: str) -> tuple[list[str], Callable[[], None]]:
    """Build the subprocess command to execute ``code`` in ``language``.

    Returns (command, cleanup). ``cleanup`` removes any temp files created and
    must be called after the subprocess finishes. Raises ValueError when the
    language is unknown or its toolchain is not installed.
    """
    if language == "python":
        return [sys.executable, "-c", code], _noop

    if language == "javascript":
        node = shutil.which("node")
        if not node:
            raise ValueError("Node.js is not installed — cannot run JavaScript")
        path = _write_temp(code, ".js")
        return [node, path], _remover(path)

    if language == "go":
        go = shutil.which("go")
        if not go:
            raise ValueError("Go is not installed — cannot run Go")
        # `go run` requires a real .go file on disk.
        tmpdir = tempfile.mkdtemp(prefix="codepractice_go_")
        path = os.path.join(tmpdir, "main.go")
        with open(path, "w") as f:
            f.write(code)
        return [go, "run", path], _tree_remover(tmpdir)

    raise ValueError(f"Unsupported language: {language}")


def _write_temp(code: str, suffix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix, prefix="codepractice_")
    with os.fdopen(fd, "w") as f:
        f.write(code)
    return path


def _noop() -> None:
    return None


def _remover(path: str) -> Callable[[], None]:
    def _clean() -> None:
        try:
            os.unlink(path)
        except OSError:
            pass
    return _clean


def _tree_remover(path: str) -> Callable[[], None]:
    def _clean() -> None:
        shutil.rmtree(path, ignore_errors=True)
    return _clean
