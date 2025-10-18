import runpy
import subprocess
import sys
from typing import Iterable

from venvmngr.__main__ import main as cli_main

PKG = "urllib3"
OLD_VERSION = "1.26.18"
MAIN_PKG = "idna"
MAIN_VERSION = "3.7"


def run_cli(args, cwd=None):
    result = subprocess.run(
        [sys.executable, "-m", "venvmngr", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result.returncode, result.stdout, result.stderr


def test_cli_end_to_end(tmp_path):
    env_dir = tmp_path / "env"

    code, out, err = run_cli(["--env", str(env_dir), "create"])
    assert code == 0
    assert env_dir.exists()

    code, out, err = run_cli(
        ["--env", str(env_dir), "install", PKG, "--version", OLD_VERSION]
    )
    assert code == 0

    code, out, err = run_cli(["--env", str(env_dir), "list"])
    assert code == 0
    assert f"{PKG}=={OLD_VERSION}" in out

    code, out, err = run_cli(["--env", str(env_dir), "update-check", PKG])
    assert code == 0
    assert PKG in out


def invoke_cli_main(args: Iterable[str]):
    original = list(sys.argv)
    sys.argv = ["venvmngr", *args]
    try:
        cli_main()
    finally:
        sys.argv = original


def test_cli_main_direct_invocation(tmp_path, capsys):
    env_dir = tmp_path / "direct"

    invoke_cli_main(["--env", str(env_dir), "create"])
    assert env_dir.exists()
    capsys.readouterr()

    invoke_cli_main(
        ["--env", str(env_dir), "install", MAIN_PKG, "--version", MAIN_VERSION]
    )
    install_out = capsys.readouterr().out
    assert "installed successfully" in install_out

    invoke_cli_main(["--env", str(env_dir), "list"])
    list_out = capsys.readouterr().out
    assert f"{MAIN_PKG}=={MAIN_VERSION}" in list_out

    invoke_cli_main(["--env", str(env_dir), "update-check", MAIN_PKG])
    update_out = capsys.readouterr().out
    assert MAIN_PKG in update_out

    invoke_cli_main(["--env", str(env_dir), "install", "bad name", "--version", "??"])
    error_out = capsys.readouterr().out
    assert "Error:" in error_out

    invoke_cli_main(["--env", str(env_dir), "update-check", "surely-missing"])
    missing_out = capsys.readouterr().out
    assert "up-to-date" in missing_out


def test_cli_entrypoint_via_run_module(tmp_path):
    env_dir = tmp_path / "module"
    original = list(sys.argv)
    sys.argv = ["venvmngr", "--env", str(env_dir), "create"]
    try:
        runpy.run_module("venvmngr.__main__", run_name="__main__")
    finally:
        sys.argv = original
    assert env_dir.exists()
