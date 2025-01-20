from abc import ABC, abstractmethod
import os
import sys
from typing import Optional, Union, List, TypedDict, Tuple
from packaging.version import Version
from collections.abc import Callable
from ._pypi import PackageData, GetPackageInfoError, get_package_info
import subprocess
import psutil
import asyncio
import subprocess_monitor
from pathlib import Path


class PackageListEntry(TypedDict):
    """
    Dictionary type representing a single package entry.

    Attributes:
        name: Name of the package.
        version: Version of the package.
    """

    name: str
    version: Version


class BaseVenvManager(ABC):
    """
    A manager for handling operations within a Python virtual environment,
    such as installing packages, retrieving installed packages, and checking for updates.
    """

    def __init__(self, env_path: Union[str, Path]):
        """
        Initialize an VenvManager instance with the specified virtual environment path.

        Args:
            env_path (str): Path to the virtual environment.
        """
        self.env_path = (
            Path(env_path) if not isinstance(env_path, Path) else env_path
        ).absolute()
        self.python_exe = self.get_python_executable()

    @abstractmethod
    def get_python_executable(self) -> Path:
        """
        Return the path to the Python executable in the virtual environment.

        Returns:
            str: Path to the Python executable.

        Raises:
            FileNotFoundError: If the Python executable is not found.
        """

    @classmethod
    def from_current_runtime(cls):
        """
        Create an VenvManager instance from the current Python runtime.

        Returns:
            VenvManager: An VenvManager instance.
        """
        env_path = Path(sys.executable).parent.parent
        return cls(env_path)

    @abstractmethod
    def install_package(
        self,
        package_name: str,
        version: Optional[Union[Version, str]] = None,
        upgrade: bool = False,
        stdout_callback: Optional[Callable[[str], None]] = None,
        stderr_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        Install a package in the virtual environment.

        Args:
            package_name (str): The name of the package to install.
            version (Optional[str]): Specific version or version specifier.
            upgrade (bool): Whether to upgrade the package.
            stdout_callback (Optional[Callable[[str], None]]): Callback function for stdout.
            stderr_callback (Optional[Callable[[str], None]]): Callback function for stderr.

        Returns:
            bool: True if installation was successful, False otherwise.
        """

    @abstractmethod
    def all_packages(self) -> List[PackageListEntry]:
        """
        Return a list of all packages installed in the virtual environment.

        Returns:
            List[PackageListEntry]: List of installed packages.

        Raises:
            ValueError: If listing or parsing packages fails.
        """

    @abstractmethod
    def remove_package(self, package_name: str):
        """
        Remove a package from the virtual environment.

        Args:
            package_name (str): The name of the package to remove.
        """
        try:
            subprocess.check_call(
                [str(self.python_exe), "-m", "pip", "uninstall", "-y", package_name]
            )
        except subprocess.CalledProcessError as exc:
            raise ValueError("Failed to uninstall package.") from exc

    def get_local_package(self, package_name: str) -> Optional[PackageListEntry]:
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

    def get_package_version(self, package_name: str) -> Optional[Version]:
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

    def get_remote_package(self, package_name: str) -> Optional[PackageData]:
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

    def package_is_installed(self, package_name: str) -> bool:
        """
        Check if a package is installed in the virtual environment.

        Args:
            package_name (str): The name of the package.

        Returns:
            bool: True if installed, False otherwise.
        """
        version = self.get_package_version(package_name)
        return version is not None

    def package_update_available(
        self, package_name: str
    ) -> Tuple[bool, Optional[Version], Optional[Version]]:
        """
        Check if an update is available for the specified package.

        Args:
            package_name (str): The name of the package to check.

        Returns:
            Tuple[bool, Optional[Version], Optional[Version]]:
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

        latest_version = Version(remote_data["info"]["version"])
        if latest_version is None:
            raise ValueError("Invalid package data.")

        return latest_version > local_version, latest_version, local_version

    def run_module(
        self, module_name: str, args: List[str] = [], block: bool = True, **kwargs
    ) -> Union[subprocess.CompletedProcess, subprocess.Popen, psutil.Process, None]:
        """
        Run a module within the virtual environment.

        Args:
            module_name (str): The name of the module to run.
            args (List[str]): List of arguments to pass to the module.
        """
        cmd = [str(self.python_exe), "-m", module_name, *args]

        if block:
            return subprocess.run(cmd, **kwargs)
        else:
            if os.environ.get("SUBPROCESS_MONITOR_PORT", None) is not None:
                res = asyncio.run(
                    subprocess_monitor.send_spawn_request(
                        args[0],
                        args[1:],
                        env={},
                        port=os.environ["SUBPROCESS_MONITOR_PORT"],
                    )
                )
                pid = res["pid"]

                def on_death():
                    try:
                        psutil.Process(pid).kill()
                    except psutil.NoSuchProcess:
                        pass

                subprocess_monitor.call_on_manager_death(on_death)
                # get the process from the pid
                try:
                    return psutil.Process(pid)
                except psutil.NoSuchProcess:
                    return None
            else:
                return subprocess.Popen(cmd, **kwargs)
