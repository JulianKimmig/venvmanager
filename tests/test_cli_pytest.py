import subprocess
import sys

PKG = "urllib3"
OLD_VERSION = "1.26.18"


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

    code, out, err = run_cli(["--env", str(env_dir), "install", PKG, "--version", OLD_VERSION])
    assert code == 0

    code, out, err = run_cli(["--env", str(env_dir), "list"])
    assert code == 0
    assert f"{PKG}=={OLD_VERSION}" in out

    code, out, err = run_cli(["--env", str(env_dir), "update-check", PKG])
    assert code == 0
    assert PKG in out
