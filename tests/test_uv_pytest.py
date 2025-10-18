import asyncio
import importlib.util
from pathlib import Path

import pytest
from packaging.version import Version

from venvmngr import UVVenvManager

PKG = "idna"
MIN_SPEC = ">=2.10"


def uv_module_available() -> bool:
    return importlib.util.find_spec("uv") is not None


@pytest.mark.skipif(not uv_module_available(), reason="'uv' Python module not available (need python -m uv)")
def test_uv_full_flow_async(tmp_path):
    async def run():
        project_dir = tmp_path / "proj"
        toml = project_dir / "pyproject.toml"

        manager, created = await UVVenvManager.aget_or_create_virtual_env(toml)
        assert isinstance(manager, UVVenvManager)
        assert toml.exists()
        assert manager.env_path.exists()

        await manager.ainstall_package(PKG, version=MIN_SPEC)
        assert manager.package_is_installed(PKG)
        current_version = manager.get_package_version(PKG)
        assert isinstance(current_version, Version) and current_version >= Version("2.10")

        await manager.ainstall_package(PKG, upgrade=True)
        upgraded_version = manager.get_package_version(PKG)
        assert upgraded_version >= current_version

        packages = await manager.aall_packages()
        assert PKG in [entry["name"].lower() for entry in packages]

        return_code = await manager.arun_module("pip", ["--version"])
        assert return_code == 0

        await manager.aremove_package(PKG)
        assert manager.package_is_installed(PKG) is False

        from_env_dir = UVVenvManager.get_virtual_env(manager.env_path)
        assert isinstance(from_env_dir, UVVenvManager)
        from_toml = UVVenvManager.get_virtual_env(toml)
        assert isinstance(from_toml, UVVenvManager)

    asyncio.run(run())


@pytest.mark.skipif(not uv_module_available(), reason="'uv' Python module not available (need python -m uv)")
def test_check_toml_path_validation(tmp_path):
    bad = tmp_path / "not_pyproject.toml"
    with pytest.raises(ValueError):
        UVVenvManager.check_toml_path(bad)

    good = tmp_path / "pyproject.toml"
    out = UVVenvManager.check_toml_path(good, create_path=True)
    assert out.name == "pyproject.toml" and out.parent.exists()
