import asyncio
import os
import sys
from pathlib import Path

import pytest

from venvmngr.utils import (
    arun_subprocess_with_streams,
    alocate_system_pythons,
    get_python_executable,
    locate_system_pythons,
    run_subprocess_with_streams,
)


def test_locate_system_pythons_returns_real_interpreters():
    pythons = locate_system_pythons()
    assert isinstance(pythons, list) and len(pythons) >= 1
    assert os.path.isfile(pythons[0]["executable"])


def test_get_python_executable_points_to_real_python():
    py = get_python_executable()
    assert os.path.isfile(py)


def test_run_subprocess_with_streams_streams_both_streams():
    out_lines: list[str] = []
    err_lines: list[str] = []

    def out_cb(line: str):
        out_lines.append(line)

    def err_cb(line: str):
        err_lines.append(line)

    code = "import sys; print('hello'); print('oops', file=sys.stderr)"
    run_subprocess_with_streams([sys.executable, "-c", code], out_cb, err_cb)

    assert any("hello" in line for line in out_lines)
    assert any("oops" in line for line in err_lines)


def test_run_subprocess_with_streams_raises_on_failure():
    code = "import sys; sys.exit(7)"
    with pytest.raises(ValueError):
        run_subprocess_with_streams([sys.executable, "-c", code])


def test_get_python_executable_pyinstaller_branch():
    original_attr = getattr(sys, "_MEIPASS", None)
    original_path = os.environ.get("PATH")
    try:
        sys._MEIPASS = "fake-meipass"
        os.environ["PATH"] = (
            f"{os.environ.get('PATH', '')}:{os.path.dirname(sys.executable)}"
        )
        py = get_python_executable()
        assert Path(py).exists()
    finally:
        if original_attr is None:
            if hasattr(sys, "_MEIPASS"):
                delattr(sys, "_MEIPASS")
        else:
            sys._MEIPASS = original_attr
        if original_path is None:
            os.environ.pop("PATH", None)
        else:
            os.environ["PATH"] = original_path


def test_get_python_executable_pyinstaller_no_python(tmp_path):
    original_attr = getattr(sys, "_MEIPASS", None)
    original_path = os.environ.get("PATH")
    try:
        sys._MEIPASS = "fake-meipass"
        os.environ["PATH"] = str(tmp_path)
        with pytest.raises(RuntimeError):
            get_python_executable()
    finally:
        if original_attr is None:
            if hasattr(sys, "_MEIPASS"):
                delattr(sys, "_MEIPASS")
        else:
            sys._MEIPASS = original_attr
        if original_path is None:
            os.environ.pop("PATH", None)
        else:
            os.environ["PATH"] = original_path


def test_locate_system_pythons_failure(tmp_path):
    original_path = os.environ.get("PATH")
    try:
        os.environ["PATH"] = str(tmp_path)
        with pytest.raises(ValueError):
            locate_system_pythons()
    finally:
        if original_path is None:
            os.environ.pop("PATH", None)
        else:
            os.environ["PATH"] = original_path


@pytest.mark.asyncio
async def test_arun_subprocess_with_streams_supports_async_callbacks():
    seen: list[str] = []

    async def async_cb(line: str):
        seen.append(line.strip())

    rc, out, err = await arun_subprocess_with_streams(
        [sys.executable, "-c", "print('async-line')"],
        stdout_callback=async_cb,
    )
    assert rc == 0
    assert "async-line" in "".join(seen)
    assert "async-line" in out
    assert err == ""


@pytest.mark.asyncio
async def test_arun_subprocess_with_streams_raises_on_failure():
    with pytest.raises(ValueError):
        await arun_subprocess_with_streams(
            [sys.executable, "-c", "import sys; sys.exit(5)"]
        )


@pytest.mark.asyncio
async def test_alocate_system_pythons_matches_sync():
    async_result = await alocate_system_pythons()
    assert isinstance(async_result, list)
    sync_result = locate_system_pythons()
    assert len(async_result) == len(sync_result)


@pytest.mark.asyncio
async def test_arun_subprocess_with_streams_cancelled_cleanup():
    task = asyncio.create_task(
        arun_subprocess_with_streams(
            [sys.executable, "-c", "import time; time.sleep(5)"]
        )
    )
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
