from __future__ import annotations
import platform
import json
from pathlib import Path
import subprocess
from typing import List, Optional, Union, Literal, Tuple
from collections.abc import Callable
from packaging.version import Version
from ._base import BaseVenvManager, PackageListEntry
from .utils import locate_system_pythons, run_subprocess_with_streams


class VenvManager(BaseVenvManager):
    """
    A manager for handling operations within a Python virtual environment,
    such as installing packages, retrieving installed packages, and checking for updates.
    """

    def get_python_executable(self) -> Path:
        """
        Return the path to the Python executable in the virtual environment.

        Returns:
            str: Path to the Python executable.

        Raises:
            FileNotFoundError: If the Python executable is not found.
        """
        if platform.system() == "Windows":
            python_exe = self.env_path / "Scripts" / "python.exe"
        else:
            python_exe = self.env_path / "bin" / "python"
        if not python_exe.is_file():
            raise FileNotFoundError(
                f"Python executable not found in virtual environment at {python_exe}"
            )
        return python_exe

    def package_name_cleaner(
        self, package_name: str, version: Optional[Union[Version, str]] = None
    ) -> str:
        if isinstance(version, Version):
            version = str(version)

        package_name = package_name.strip()
        if version:
            version = version.strip()

        if not package_name:
            raise ValueError("Package name cannot be empty.")

        if " " in package_name:
            raise ValueError("Package name cannot contain spaces.")

        # Replace underscores with hyphens for packages that use underscores
        package_name = package_name.replace("_", "-")

        if version:
            if version[0] in ("<", ">", "="):
                return f"{package_name}{version}"
            else:
                return f"{package_name}=={version}"

        return package_name

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
        install_cmd = [str(self.python_exe), "-m", "pip", "install"]

        package_version = self.package_name_cleaner(package_name, version)

        install_cmd.append(package_version)

        if upgrade:
            install_cmd.append("--upgrade")

        run_subprocess_with_streams(install_cmd, stdout_callback, stderr_callback)

    def all_packages(self) -> List[PackageListEntry]:
        """
        Return a list of all packages installed in the virtual environment.

        Returns:
            List[PackageListEntry]: List of installed packages.

        Raises:
            ValueError: If listing or parsing packages fails.
        """
        list_cmd = [str(self.python_exe), "-m", "pip", "list", "--format=json"]
        try:
            result = subprocess.check_output(list_cmd, universal_newlines=True)
        except subprocess.CalledProcessError as exc:
            raise ValueError("Failed to list packages.") from exc
        try:
            packages = json.loads(result)
        except json.JSONDecodeError as exc:
            raise ValueError("Failed to parse pip output.") from exc

        return [
            {**pkg, "name": pkg["name"], "version": Version(pkg["version"])}
            for pkg in packages
        ]

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

    @classmethod
    def create_virtual_env(
        cls,
        env_path: Union[str, Path],
        min_python: Optional[Union[str, Version]] = None,
        max_python: Optional[Union[str, Version]] = None,
        use: Literal["default", "latest"] = "default",
        python_executable: Optional[str] = None,
        stdout_callback: Optional[Callable[[str], None]] = None,
        stderr_callback: Optional[Callable[[str], None]] = None,
    ) -> VenvManager:
        """
        Create a virtual environment at the specified path.

        Args:
            env_path ( Union[str, Path]): Path where the virtual environment will be created.
            min_python (Optional[Union[str, Version]]): Minimum Python version.
                Ignored if `python_executable` is provided.
            max_python (Optional[Union[str, Version]]): Maximum Python version.
                Ignored if `python_executable` is provided.
            use (Literal["default", "latest"]): Strategy for selecting Python version.
                Ignored if `python_executable` is provided.
            python_executable (Optional[str]): Path to the Python executable to use.
                If not provided, the appropriate system Python will be used.
            stdout_callback (Optional[Callable[[str], None]]): Callback function for stdout.
            stderr_callback (Optional[Callable[[str], None]]): Callback function for stderr.

        Returns:
            VenvManager: An VenvManager instance managing the new environment.
        """
        if not isinstance(env_path, Path):
            env_path = Path(env_path)

        if not python_executable:
            pythons = locate_system_pythons()

            if not pythons:
                raise ValueError("No suitable system Python found.")

            # filter first
            if min_python:
                if isinstance(min_python, str):
                    min_python = Version(min_python)

                pythons = [p for p in pythons if p["version"] >= min_python]

            if max_python:
                if isinstance(max_python, str):
                    max_python = Version(max_python)

                pythons = [p for p in pythons if p["version"] <= max_python]

            if not pythons:
                raise ValueError(
                    f"No suitable system Python found within version range {min_python} - {max_python}."
                )

            if use == "latest":
                python_mv = max(pythons, key=lambda x: x["version"])["version"]
                pythons = [p for p in pythons if p["version"] == python_mv]
            elif use == "default":
                pass

            python_executable = pythons[0]["executable"]

        # Create the virtual environment
        # Use Popen to create the virtual environment and stream output
        run_subprocess_with_streams(
            [python_executable, "-m", "venv", str(env_path)],
            stdout_callback,
            stderr_callback,
        )

        return cls(env_path)

    @classmethod
    def get_or_create_virtual_env(
        cls, env_path: Union[str, Path], **create_kwargs
    ) -> Tuple[VenvManager, bool]:
        """
        Return an VenvManager instance, creating the environment if necessary.

        Args:
            env_path (Union[str,Path]): Path to the virtual environment.

        Returns:
            VenvManager: An instance of VenvManager.
            bool: True if the environment was created, False if it already existed.

        Raises:
            ValueError: If the specified directory does not contain a valid environment.
        """
        if not isinstance(env_path, Path):
            env_path = Path(env_path)

        if not env_path.exists():
            return cls.create_virtual_env(env_path, **create_kwargs), True
        try:
            return VenvManager(env_path), False
        except FileNotFoundError as exc:
            raise ValueError(
                f"Directory {env_path} does not contain a valid virtual environment."
            ) from exc

    @classmethod
    def get_virtual_env(
        cls,
        env_path: Union[str, Path],
    ) -> VenvManager:
        """
        Return an VenvManager instance for an existing virtual environment.

        Args:
            env_path (Union[str, Path]): Path to the virtual environment.

        Returns:
            VenvManager: An instance of VenvManager.

        Raises:
            ValueError: If the specified directory does not contain a valid environment.
        """  #
        if not isinstance(env_path, Path):
            env_path = Path(env_path)
        try:
            return cls(env_path)
        except FileNotFoundError as exc:
            raise ValueError(
                f"Directory {env_path} does not contain a valid virtual environment."
            ) from exc
