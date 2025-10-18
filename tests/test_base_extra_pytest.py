import asyncio
import multiprocessing
import os
import socket
import sys
import time
from pathlib import Path

import psutil
import pytest
from packaging.version import Version

from venvmngr._base import BaseVenvManager
from venvmngr._pypi import GetPackageInfoError, get_package_info


class StubManager(BaseVenvManager):
    """Minimal concrete manager for exercising BaseVenvManager behaviour."""

    def __init__(self, env_path: Path, packages=None):
        self._packages = packages or []
        super().__init__(env_path)

    @classmethod
    def create_virtual_env(cls, env_path: Path, **_):
        return cls(env_path)

    @classmethod
    def get_or_create_virtual_env(cls, env_path: Path, **_):
        return cls(env_path), True

    @classmethod
    def get_virtual_env(cls, env_path: Path, **_):
        return cls(env_path)

    def get_python_executable(self) -> Path:
        return Path(sys.executable)

    def install_package(
        self,
        package_name: str,
        version: Version | str | None = None,
        upgrade: bool = False,
        stdout_callback=None,
        stderr_callback=None,
    ):
        ver = Version(str(version or "0"))
        for pkg in self._packages:
            if pkg["name"].lower() == package_name.lower():
                pkg["version"] = ver
                break
        else:
            self._packages.append({"name": package_name, "version": ver})

    def all_packages(self):
        return list(self._packages)

    def remove_package(self, package_name: str):
        self._packages = [
            pkg for pkg in self._packages if pkg["name"].lower() != package_name.lower()
        ]


class NullRemoteManager(StubManager):
    def get_remote_package(self, package_name: str):
        return None


class BadInfoManager(StubManager):
    def __init__(self, env_path: Path, payload, **kwargs):
        super().__init__(env_path, **kwargs)
        self._payload = payload

    def get_remote_package(self, package_name: str):
        return self._payload


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _run_monitor(port: int):
    import asyncio
    from subprocess_monitor import run_subprocess_monitor

    asyncio.run(run_subprocess_monitor(port=port))


def test_base_from_runtime_and_async_wrappers(tmp_path):
    manager = StubManager.from_current_runtime()

    async def exercise():
        await manager.ainstall_package("demo", version="1.2.3")
        packages = await manager.aall_packages()
        assert packages[0]["version"] == Version("1.2.3")
        await manager.arun_module("timeit", ["-n", "1", "pass"])
        await manager.aremove_package("demo")
        assert manager.all_packages() == []

    asyncio.run(exercise())


def test_base_async_class_convenience(tmp_path):
    async def exercise():
        env_a = tmp_path / "async-a"
        created = await StubManager.acreate_virtual_env(env_a)
        assert isinstance(created, StubManager)

        env_b = tmp_path / "async-b"
        manager, created_flag = await StubManager.aget_or_create_virtual_env(env_b)
        assert created_flag is True and isinstance(manager, StubManager)

        existing = await StubManager.aget_virtual_env(env_a)
        assert isinstance(existing, StubManager)

    asyncio.run(exercise())


def test_base_run_module_non_block():
    manager = StubManager(Path.cwd())
    proc = manager.run_module("timeit", ["-n", "1", "pass"], block=False)
    try:
        assert proc is not None
        proc.wait(timeout=10)
    finally:
        if proc and proc.poll() is None:
            proc.terminate()


def test_base_run_module_with_subprocess_monitor():
    port = _free_port()
    proc = multiprocessing.Process(target=_run_monitor, args=(port,), daemon=True)
    proc.start()
    try:
        time.sleep(0.5)
        os.environ["SUBPROCESS_MONITOR_PORT"] = str(port)
        os.environ["SUBPROCESS_MONITOR_PID"] = str(os.getpid())
        manager = StubManager(Path.cwd())
        ps_proc = manager.run_module("timeit", ["-n", "1", "pass"], block=False)
        assert ps_proc is None or isinstance(ps_proc, psutil.Process)
        if ps_proc is not None:
            ps_proc.wait(timeout=10)
        else:
            time.sleep(0.5)
    finally:
        os.environ.pop("SUBPROCESS_MONITOR_PORT", None)
        os.environ.pop("SUBPROCESS_MONITOR_PID", None)
        if proc.is_alive():
            proc.terminate()
        proc.join(timeout=5)


def test_base_package_update_variants(tmp_path):
    env = tmp_path / "env"
    manager = StubManager(env, [{"name": "local", "version": Version("1.0.0")}])

    missing = manager.package_update_available("absent")
    assert missing == (False, None, None)

    null_remote = NullRemoteManager(
        env, [{"name": "local", "version": Version("1.0.0")}]
    )
    no_remote = null_remote.package_update_available("local")
    assert no_remote == (False, None, Version("1.0.0"))

    with pytest.raises(ValueError):
        BadInfoManager(
            env, {}, packages=[{"name": "local", "version": Version("1.0.0")}]
        ).package_update_available("local")

    with pytest.raises(ValueError):
        BadInfoManager(
            env, {"info": {}}, packages=[{"name": "local", "version": Version("1.0.0")}]
        ).package_update_available("local")

    bad_version = BadInfoManager(
        env,
        {"info": {"version": "not-a-version"}},
        packages=[{"name": "local", "version": Version("1.0.0")}],
    ).package_update_available
    with pytest.raises(ValueError):
        bad_version("local")


def test_base_get_remote_package_handles_missing_package():
    manager = StubManager(Path.cwd())
    result = manager.get_remote_package("package-that-cannot-exist-404")
    assert result is None


def test_get_package_info_error_path():
    with pytest.raises(GetPackageInfoError):
        get_package_info("package-that-cannot-exist-404")
