import os
import sys

from venvmngr.utils import (
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
