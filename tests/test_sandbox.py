"""Tests for submitted-code resource limits."""

from __future__ import annotations

import sys

import pytest

from codepractice.utils.code_runner import run_code
from codepractice.utils.sandbox import (
    ADDRESS_SPACE_LIMITS,
    FILE_SIZE_LIMITS,
    MB,
    limit_spec,
    wrap_with_limits,
)

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX rlimits only")


class TestLimitSpec:
    def test_python_spec_includes_all_limits(self):
        spec = limit_spec("python", 10)
        assert spec["RLIMIT_CPU"] == 10
        assert spec["RLIMIT_FSIZE"] == 8 * MB
        assert spec["RLIMIT_CORE"] == 0
        assert spec["RLIMIT_AS"] == 1024 * MB

    def test_go_has_no_address_space_cap(self):
        assert ADDRESS_SPACE_LIMITS["go"] is None
        assert "RLIMIT_AS" not in limit_spec("go", 10)

    def test_js_cap_larger_than_python(self):
        assert ADDRESS_SPACE_LIMITS["javascript"] > ADDRESS_SPACE_LIMITS["python"]

    def test_go_gets_toolchain_headroom(self):
        # `go run` compiles first; the compiler writes package archives far
        # beyond the interpreter-language cap (regression: CI "file too large").
        assert FILE_SIZE_LIMITS["go"] > FILE_SIZE_LIMITS["python"]

    def test_interpreted_languages_keep_tight_cap(self):
        assert FILE_SIZE_LIMITS["python"] == 8 * MB
        assert FILE_SIZE_LIMITS["javascript"] == 8 * MB


class TestWrapWithLimits:
    def test_wraps_command_with_shim_on_posix(self):
        if sys.platform == "win32":
            assert wrap_with_limits(["echo", "hi"], "python", 10) == ["echo", "hi"]
        else:
            wrapped = wrap_with_limits(["echo", "hi"], "python", 10)
            assert wrapped[0] == sys.executable
            assert wrapped[-2:] == ["echo", "hi"]

    def test_no_preexec_fn_used(self):
        """The runner must not use preexec_fn — it runs Python in the forked
        child of a multi-threaded parent and can deadlock (CI: silent 10s
        hangs with empty output). Limits go through the exec shim instead."""
        import inspect

        from codepractice.utils import code_runner
        assert "preexec_fn" not in inspect.getsource(code_runner)


@posix_only
class TestLimitsEnforced:
    def test_normal_code_unaffected(self):
        result = run_code("print(sum(range(1000)))")
        assert result.passed is True
        assert "499500" in result.stdout

    def test_memory_bomb_killed(self):
        # Tries to allocate ~2 GB — above the 1 GB python address-space cap.
        result = run_code("x = bytearray(2 * 1024 * 1024 * 1024); print(len(x))")
        assert result.passed is False

    def test_cpu_spin_killed_by_rlimit(self):
        # Killed by RLIMIT_CPU (SIGXCPU) or the wall-clock timeout backstop.
        result = run_code("while True: pass", timeout=1)
        assert result.passed is False

    def test_giant_file_write_blocked(self):
        code = (
            "import tempfile\n"
            "f = tempfile.TemporaryFile()\n"
            "f.write(b'x' * (32 * 1024 * 1024))\n"
            "print('wrote')\n"
        )
        result = run_code(code)
        assert result.passed is False
        assert "wrote" not in result.stdout

    def test_runs_reliably_from_threads(self):
        """Regression for the CI flake: spawning sandboxed runs from worker
        threads must never hang. With preexec_fn this deadlocked
        intermittently; the exec shim has no fork/Python interaction."""
        from concurrent.futures import ThreadPoolExecutor

        def one_run(i: int) -> str:
            return run_code(f"print({i} * 2)", timeout=10).stdout.strip()

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(one_run, range(24)))
        assert results == [str(i * 2) for i in range(24)]
