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
