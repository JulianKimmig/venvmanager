import sys

import pytest
from packaging.version import Version

from venvmngr import VenvManager, get_or_create_virtual_env

PKG = "urllib3"
OLD = Version("1.26.18")


def test_venv_full_flow_sync(tmp_path):
    env_dir = tmp_path / "env"
    manager, created = get_or_create_virtual_env(env_dir)
    assert isinstance(manager, VenvManager)

    manager.install_package(PKG, version=str(OLD))
    assert manager.package_is_installed(PKG)
    assert manager.get_package_version(PKG) == OLD

    packages = manager.all_packages()
    assert isinstance(packages, list) and len(packages) >= 1
    names = [entry["name"].lower() for entry in packages]
    assert PKG in names
    pkg_entry = next(entry for entry in packages if entry["name"].lower() == PKG)
    assert isinstance(pkg_entry["version"], Version)
    assert pkg_entry["version"] == OLD

    data = manager.get_remote_package(PKG)
    assert data and "info" in data and data["info"]["name"].lower() == PKG

    update_available, latest, current = manager.package_update_available(PKG)
    assert update_available is True
    assert isinstance(latest, Version) and latest > current == OLD

    manager.install_package(PKG, upgrade=True)
    current_version = manager.get_package_version(PKG)
    assert isinstance(current_version, Version) and current_version > OLD

    update_available, latest, current = manager.package_update_available(PKG)
    assert isinstance(latest, Version)
    assert current is not None
    assert (update_available is False and latest == current) or (
        update_available is False and current >= latest
    )

    result = manager.run_module("pip", ["--version"])
    assert result.returncode == 0

    manager.remove_package(PKG)
    assert manager.package_is_installed(PKG) is False


def test_package_name_cleaner_variants():
    manager = VenvManager.__new__(VenvManager)
    cleaned = VenvManager.package_name_cleaner(manager, "sample_pkg", "1.2.3")
    assert cleaned == "sample-pkg==1.2.3"
    spec = VenvManager.package_name_cleaner(manager, "sample", ">=1.0")
    assert spec == "sample>=1.0"


def test_package_name_cleaner_invalid():
    manager = VenvManager.__new__(VenvManager)
    with pytest.raises(ValueError):
        VenvManager.package_name_cleaner(manager, "bad name", "??")


def test_get_python_executable_missing(tmp_path):
    env_dir = tmp_path / "missing"
    env_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        VenvManager(env_dir)


def test_create_virtual_env_with_explicit_python(tmp_path):
    env_dir = tmp_path / "explicit"
    manager = VenvManager.create_virtual_env(env_dir, python_executable=sys.executable)
    assert manager.env_path == env_dir
    assert manager.python_exe.exists()


def test_create_virtual_env_min_version_failure(tmp_path):
    env_dir = tmp_path / "too_new"
    with pytest.raises(ValueError):
        VenvManager.create_virtual_env(env_dir, min_python="99.0")


def test_get_or_create_virtual_env_invalid_dir(tmp_path):
    bad_env = tmp_path / "bad_env"
    bad_env.mkdir()
    with pytest.raises(ValueError):
        VenvManager.get_or_create_virtual_env(bad_env)


def test_get_virtual_env_invalid(tmp_path):
    bad_env = tmp_path / "bad_env2"
    bad_env.mkdir()
    with pytest.raises(ValueError):
        VenvManager.get_virtual_env(bad_env)
