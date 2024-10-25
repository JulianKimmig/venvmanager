import os
import sys
import subprocess
import platform
import json
from typing import List, Dict, TypedDict, Optional
import requests
import venv
from ._pypi import PackageData, GetPackageInfoError, get_package_info


class PackageListEntry(TypedDict):
    name: str
    version: str


class EnvManager:
    def __init__(self, env_path):
        """
        Initialize an EnvManager instance with the specified virtual environment path.

        Args:
            env_path (str): Path to the virtual environment.
        """

        self.env_path = env_path
        self.python_exe = self.get_python_executable()

    def get_python_executable(self):
        """
        Return the path to the Python executable in the virtual environment.

        Returns:
            str: Path to the Python executable.

        Raises:
            FileNotFoundError: If the Python executable is not found.
        """
        if platform.system() == "Windows":
            python_exe = os.path.join(self.env_path, "Scripts", "python.exe")
        else:
            python_exe = os.path.join(self.env_path, "bin", "python")
        if not os.path.isfile(python_exe):
            raise FileNotFoundError(
                f"Python executable not found in virtual environment at {self.env_path}"
            )
        return python_exe

    @classmethod
    def from_current_runtime(cls):
        """
        Create an EnvManager instance from the current Python runtime.

        Returns:
            EnvManager: An EnvManager instance.
        """
        env_path = os.path.dirname(os.path.dirname(sys.executable))
        return cls(env_path)

    def install_package(self, package_name, version=None, upgrade=False):
        """
        Install a package in the virtual environment.

        Args:
            package_name (str): The name of the package to install.
            version (Optional[str]): Specific version or version specifier.
            upgrade (bool): Whether to upgrade the package.

        Returns:
            bool: True if installation was successful, False otherwise.
        """
        install_cmd = [self.python_exe, "-m", "pip", "install", package_name]

        # If a specific version is requested, modify the install command
        if version:
            # check if the version starts with a version specifier
            if version[0] in ("<", ">", "="):
                install_cmd[-1] = f'"{package_name}{version}"'
            else:
                install_cmd[-1] = f'"{package_name}=={version}"'

        if upgrade:
            install_cmd.append("--upgrade")

        try:
            subprocess.check_call(install_cmd)
            return True
        except subprocess.CalledProcessError:
            return False

    def all_packages(self) -> List[PackageListEntry]:
        """
        Return a list of all packages installed in the virtual environment.

        Returns:
            List[PackageListEntry]: List of installed packages.

        Raises:
            ValueError: If listing or parsing packages fails.
        """
        list_cmd = [self.python_exe, "-m", "pip", "list", "--format=json"]
        try:
            result = subprocess.check_output(list_cmd, universal_newlines=True)
        except subprocess.CalledProcessError as exc:
            raise ValueError("Failed to list packages.") from exc
        try:
            packages = json.loads(result)
            return packages
        except json.JSONDecodeError as exc:
            raise ValueError("Failed to parse pip output.") from exc

    def get_local_package(self, package_name) -> Optional[PackageListEntry]:
        """
        Return the package entry for the specified package installed in the virtual environment.

        Args:
            package_name (str): The name of the package.

        Returns:
            Optional[PackageListEntry]: Package entry if found, None otherwise.
        """
        for pkg in self.all_packages():
            if pkg["name"].lower() == package_name.lower():
                return pkg
        return None

    def get_package_version(self, package_name) -> Optional[str]:
        """
        Return the version of the specified package if installed.

        Args:
            package_name (str): The name of the package.

        Returns:
            Optional[str]: Version of the package if installed, None otherwise.
        """

        listentry = self.get_local_package(package_name)
        if listentry:
            return listentry["version"]
        return None

    def get_remote_package(self, package_name) -> Optional[PackageData]:
        """
        Fetch package data from PyPI for the specified package.

        Args:
            package_name (str): The name of the package.

        Returns:
            Optional[PackageData]: Package data from PyPI if available, None otherwise.

        Raises:
            ValueError: If package data cannot be retrieved.
        """

        try:
            return get_package_info(package_name)
        except GetPackageInfoError:
            return None

    def package_is_installed(self, package_name):
        """
        Check if a package is installed in the virtual environment.

        Args:
            package_name (str): The name of the package.

        Returns:
            bool: True if installed, False otherwise.
        """
        version = self.get_package_version(package_name)
        return version is not None

    def package_update_available(self, package_name):
        """
        Check if an update is available for the specified package.

        Args:
            package_name (str): The name of the package to check.

        Returns:
            Tuple[bool, Optional[str], Optional[str]]:
                - True if an update is available, False otherwise.
                - The latest version of the package.
                - The currently installed version.
        """
        local_version = self.get_package_version(package_name)
        if local_version is None:
            return False, None, None

        remote_data = self.get_remote_package(package_name)
        if remote_data is None:
            return False, None, local_version

        if "info" not in remote_data:
            raise ValueError("Invalid package data.")
        if "version" not in remote_data["info"]:
            raise ValueError("Invalid package data.")

        latest_version = remote_data["info"]["version"]
        if latest_version is None:
            raise ValueError("Invalid package data.")

        return latest_version != local_version, latest_version, local_version


def create_virtual_env(env_path) -> EnvManager:
    """
    Create a virtual environment at the specified path.

    Args:
        env_path (str): Path where the virtual environment will be created.

    Returns:
        str: Path to the
    """

    print(f"Creating virtual environment at {env_path}...")
    builder = venv.EnvBuilder(with_pip=True)
    builder.create(env_path)
    print("Virtual environment created.")
    return EnvManager(env_path)


def get_or_create_virtual_env(env_path):
    """
    Return an EnvManager instance, creating the environment if necessary.

    Args:
        env_path (str): Path to the virtual environment.

    Returns:
        EnvManager: An instance of EnvManager.

    Raises:
        ValueError: If the specified directory does not contain a valid environment.
    """
    if not os.path.isdir(env_path):
        return create_virtual_env(env_path)
    try:
        return EnvManager(env_path)
    except FileNotFoundError:
        raise ValueError(
            f"Directory {env_path} does not contain a valid virtual environment."
        )


if __name__ == "__main__":
    ev = EnvManager.from_current_runtime()
    # ev.install_package("requests")
    print(ev.package_is_installed("asaf"))
    print(ev.package_update_available("requests"))
    print(ev.package_update_available("funcnodes"))
    print(ev.get_package_version("requests"))
