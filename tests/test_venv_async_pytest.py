import asyncio

import pytest
from packaging.version import Version

from venvmngr import VenvManager

PKG = "urllib3"
OLD = Version("1.26.18")


def has_async_api() -> bool:
    required = [
        "acreate_virtual_env",
        "aget_or_create_virtual_env",
        "ainstall_package",
        "aall_packages",
        "aremove_package",
        "arun_module",
    ]
    return all(hasattr(VenvManager, attr) for attr in required)


@pytest.mark.skipif(not has_async_api(), reason="Async API not available in this build")
def test_venv_full_flow_async(tmp_path):
    async def run():
        env_dir = tmp_path / "aenv"
        manager, created = await VenvManager.aget_or_create_virtual_env(env_dir)

        await manager.ainstall_package(PKG, version=str(OLD))
        assert manager.package_is_installed(PKG)
        assert manager.get_package_version(PKG) == OLD

        packages = await manager.aall_packages()
        names = [entry["name"].lower() for entry in packages]
        assert PKG in names

        update_available, latest, current = manager.package_update_available(PKG)
        assert update_available is True and latest > current == OLD

        await manager.ainstall_package(PKG, upgrade=True)
        current_version = manager.get_package_version(PKG)
        assert isinstance(current_version, Version) and current_version > OLD

        return_code = await manager.arun_module("pip", ["--version"])
        assert return_code == 0

        await manager.aremove_package(PKG)
        assert manager.package_is_installed(PKG) is False

    asyncio.run(run())


@pytest.mark.skipif(not has_async_api(), reason="Async API not available in this build")
@pytest.mark.asyncio
async def test_venv_async_create_min_version_failure(tmp_path):
    env_dir = tmp_path / "async-too-new"
    with pytest.raises(ValueError):
        await VenvManager.acreate_virtual_env(env_dir, min_python="99.0")
