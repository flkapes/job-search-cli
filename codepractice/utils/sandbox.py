"""POSIX resource limits for submitted-code subprocesses.

This limits runaway submissions (memory bombs, fork-adjacent disk fills,
CPU spins that dodge the wall-clock timeout by sleeping); it is *not* full
isolation — there is no network or filesystem namespace separation. Imported
problems should still be reviewed before running.
"""

from __future__ import annotations

from typing import Callable

try:
    import resource
except ImportError:  # non-POSIX (Windows)
    resource = None  # type: ignore[assignment]

MB = 1024 * 1024

# Address-space caps must respect each runtime's virtual-memory behavior:
# V8 reserves multi-GB virtual regions at startup and the Go runtime reserves
# an enormous virtual arena, so a Python-sized cap would break them outright.
ADDRESS_SPACE_LIMITS: dict[str, int | None] = {
    "python": 1024 * MB,
    "javascript": 4096 * MB,
    "go": None,  # Go's runtime arena is incompatible with RLIMIT_AS
}

# File-size caps are language-aware too: `go run` compiles first, and with a
# cold build cache the compiler writes package archives well beyond 8 MB
# ("compile: ... file too large" under RLIMIT_FSIZE). The Go cap still bounds
# a runaway disk-filler, just with toolchain headroom.
FILE_SIZE_LIMITS: dict[str, int] = {
    "python": 8 * MB,
    "javascript": 8 * MB,
    "go": 512 * MB,
}


def make_preexec(language: str, timeout: int) -> Callable[[], None] | None:
    """Build a preexec_fn applying resource limits, or None when unsupported."""
    if resource is None:
        return None

    address_space = ADDRESS_SPACE_LIMITS.get(language, ADDRESS_SPACE_LIMITS["python"])
    max_file_bytes = FILE_SIZE_LIMITS.get(language, FILE_SIZE_LIMITS["python"])
    cpu_seconds = max(1, int(timeout))

    def _apply_limits() -> None:
        # Runs in the forked child just before exec.
        def _set(limit_id: int, value: int) -> None:
            try:
                _, hard = resource.getrlimit(limit_id)
                if hard != resource.RLIM_INFINITY:
                    value = min(value, hard)
                resource.setrlimit(limit_id, (value, value))
            except (ValueError, OSError):
                pass  # never block execution because a limit couldn't apply

        _set(resource.RLIMIT_CPU, cpu_seconds)
        _set(resource.RLIMIT_FSIZE, max_file_bytes)
        _set(resource.RLIMIT_CORE, 0)
        if address_space is not None:
            _set(resource.RLIMIT_AS, address_space)

    return _apply_limits
