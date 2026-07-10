"""POSIX resource limits for submitted-code subprocesses.

This limits runaway submissions (memory bombs, disk fills, CPU spins that
dodge the wall-clock timeout by sleeping); it is *not* full isolation — there
is no network or filesystem namespace separation. Imported problems should
still be reviewed before running.

Limits are applied by a tiny shim process that sets rlimits and then execs
the real command. This deliberately avoids ``preexec_fn``: that mechanism
runs Python code in the forked child of a potentially multi-threaded parent,
which CPython documents as unsafe and which manifests as silent child hangs
(empty output until the wall-clock timeout).
"""

from __future__ import annotations

import json
import sys

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

# Runs in a fresh, single-threaded interpreter: set limits, then exec.
_SHIM = (
    "import json, os, resource, sys\n"
    "for name, value in json.loads(sys.argv[1]).items():\n"
    "    rid = getattr(resource, name, None)\n"
    "    if rid is None:\n"
    "        continue\n"
    "    try:\n"
    "        _, hard = resource.getrlimit(rid)\n"
    "        if hard != resource.RLIM_INFINITY:\n"
    "            value = min(value, hard)\n"
    "        resource.setrlimit(rid, (value, value))\n"
    "    except (ValueError, OSError):\n"
    "        pass\n"
    "os.execvp(sys.argv[2], sys.argv[2:])\n"
)


def limit_spec(language: str, timeout: int) -> dict[str, int]:
    """The rlimits to apply for a language, keyed by resource constant name."""
    spec: dict[str, int] = {
        "RLIMIT_CPU": max(1, int(timeout)),
        "RLIMIT_FSIZE": FILE_SIZE_LIMITS.get(language, FILE_SIZE_LIMITS["python"]),
        "RLIMIT_CORE": 0,
    }
    address_space = ADDRESS_SPACE_LIMITS.get(language, ADDRESS_SPACE_LIMITS["python"])
    if address_space is not None:
        spec["RLIMIT_AS"] = address_space
    return spec


def wrap_with_limits(cmd: list[str], language: str, timeout: int) -> list[str]:
    """Prefix ``cmd`` with the rlimit shim (no-op where rlimits don't exist)."""
    if resource is None:
        return cmd
    spec = json.dumps(limit_spec(language, timeout))
    # -I: isolated mode — ignore env/site so the shim starts fast and clean.
    return [sys.executable, "-I", "-c", _SHIM, spec] + cmd
