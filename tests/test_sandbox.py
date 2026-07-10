"""Tests for submitted-code resource limits."""

from __future__ import annotations

import sys

import pytest

from codepractice.utils.code_runner import run_code
from codepractice.utils.sandbox import ADDRESS_SPACE_LIMITS, make_preexec

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX rlimits only")


class TestMakePreexec:
    def test_returns_callable_on_posix(self):
        if sys.platform == "win32":
            assert make_preexec("python", 10) is None
        else:
            assert callable(make_preexec("python", 10))

    def test_go_has_no_address_space_cap(self):
        assert ADDRESS_SPACE_LIMITS["go"] is None

    def test_js_cap_larger_than_python(self):
        assert ADDRESS_SPACE_LIMITS["javascript"] > ADDRESS_SPACE_LIMITS["python"]


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
        # Busy loop: RLIMIT_CPU (= timeout seconds) kills it via SIGXCPU,
        # and the wall-clock timeout backstops it either way.
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


class TestFileSizeLimits:
    def test_go_gets_toolchain_headroom(self):
        from codepractice.utils.sandbox import FILE_SIZE_LIMITS
        # `go run` compiles first; the compiler writes package archives far
        # beyond the interpreter-language cap (regression: CI "file too large").
        assert FILE_SIZE_LIMITS["go"] > FILE_SIZE_LIMITS["python"]

    def test_interpreted_languages_keep_tight_cap(self):
        from codepractice.utils.sandbox import FILE_SIZE_LIMITS, MB
        assert FILE_SIZE_LIMITS["python"] == 8 * MB
        assert FILE_SIZE_LIMITS["javascript"] == 8 * MB
