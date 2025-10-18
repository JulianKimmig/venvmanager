"""Standard library venv-based environment manager.

Provides a concrete implementation of `BaseVenvManager` using
the built-in `venv` module and `pip` to manage packages.
"""

from __future__ import annotations
import platform
import json
from pathlib import Path
import subprocess
from typing import List, Optional, Union, Literal, Tuple
from collections.abc import Callable
import asyncio
from packaging.version import Version
from packaging.requirements import Requirement, InvalidRequirement
from ._base import BaseVenvManager, PackageListEntry
from .utils import (
    locate_system_pythons,
    run_subprocess_with_streams,
    arun_subprocess_with_streams,
)


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
        """Normalize and compose a package specifier.

        Ensures a clean package name, replaces underscores with hyphens
        and, if a version is provided, returns either an exact pin
        (``name==X``) or preserves an operator-based specifier
        (e.g. ``name>=X``).

        Args:
            package_name: Raw package name.
            version: Optional version or specifier.

        Returns:
            str: A normalized package specifier suitable for pip/uv.

        Raises:
            ValueError: If the package name is empty or invalid.
        """
        name = package_name.strip().replace("_", "-")
        if isinstance(version, Version):
            version = str(version)
        ver = (version or "").strip()
        spec = (
            f"{name}{ver}"
            if (ver and ver[:1] in "<>!=~=")
            else (f"{name}=={ver}" if ver else name)
        )
        # Validate
        try:
            Requirement(spec)  # raises on invalid
        except InvalidRequirement as e:
            raise ValueError(str(e)) from e  # raises on invalid
        return spec

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

    # Async variants rely on asyncio subprocesses to keep the loop responsive.
    async def ainstall_package(
        self,
        package_name: str,
        version: Optional[Union[Version, str]] = None,
        upgrade: bool = False,
        stdout_callback: Optional[Callable[[str], None]] = None,
        stderr_callback: Optional[Callable[[str], None]] = None,
    ):
        install_cmd = [str(self.python_exe), "-m", "pip", "install"]
        package_version = self.package_name_cleaner(package_name, version)
        install_cmd.append(package_version)
        if upgrade:
            install_cmd.append("--upgrade")
        await arun_subprocess_with_streams(
            install_cmd,
            stdout_callback=stdout_callback,
            stderr_callback=stderr_callback,
        )

    async def aall_packages(self) -> List[PackageListEntry]:
        list_cmd = [str(self.python_exe), "-m", "pip", "list", "--format=json"]
        _, out, _ = await arun_subprocess_with_streams(list_cmd)
        try:
            packages = json.loads(out)
        except json.JSONDecodeError as exc:
            raise ValueError("Failed to parse pip output.") from exc
        return [
            {**pkg, "name": pkg["name"], "version": Version(pkg["version"])}
            for pkg in packages
        ]

    async def aremove_package(self, package_name: str):
        cmd = [str(self.python_exe), "-m", "pip", "uninstall", "-y", package_name]
        await arun_subprocess_with_streams(cmd)

    async def arun_module(
        self,
        module_name: str,
        args: List[str] = [],
        stdout_callback: Optional[Callable[[str], None]] = None,
        stderr_callback: Optional[Callable[[str], None]] = None,
    ) -> int:
        cmd = [str(self.python_exe), "-m", module_name, *args]
        rc, _, _ = await arun_subprocess_with_streams(
            cmd,
            stdout_callback=stdout_callback,
            stderr_callback=stderr_callback,
        )
        return rc

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

        env_path.parent.mkdir(parents=True, exist_ok=True)
        # Create the virtual environment
        # Use Popen to create the virtual environment and stream output
        run_subprocess_with_streams(
            [python_executable, "-m", "venv", str(env_path)],
            stdout_callback,
            stderr_callback,
        )
        mng = cls(env_path)
        mng._bootstrap_pip(stdout_callback, stderr_callback)
        return mng

    @classmethod
    async def acreate_virtual_env(
        cls,
        env_path: Union[str, Path],
        min_python: Optional[Union[str, Version]] = None,
        max_python: Optional[Union[str, Version]] = None,
        use: Literal["default", "latest"] = "default",
        python_executable: Optional[str] = None,
        stdout_callback: Optional[Callable[[str], None]] = None,
        stderr_callback: Optional[Callable[[str], None]] = None,
    ) -> "VenvManager":
        if not isinstance(env_path, Path):
            env_path = Path(env_path)

        if not python_executable:
            pythons = await asyncio.to_thread(locate_system_pythons)

            if not pythons:
                raise ValueError("No suitable system Python found.")

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

            python_executable = pythons[0]["executable"]

        env_path.parent.mkdir(parents=True, exist_ok=True)

        await arun_subprocess_with_streams(
            [python_executable, "-m", "venv", str(env_path)],
            stdout_callback=stdout_callback,
            stderr_callback=stderr_callback,
        )
        mng = cls(env_path)
        await mng._abootstrap_pip(stdout_callback, stderr_callback)
        return mng

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
    async def aget_or_create_virtual_env(
        cls, env_path: Union[str, Path], **create_kwargs
    ) -> Tuple["VenvManager", bool]:
        if not isinstance(env_path, Path):
            env_path = Path(env_path)

        if not env_path.exists():
            return await cls.acreate_virtual_env(env_path, **create_kwargs), True
        try:
            return cls(env_path), False
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

    def _bootstrap_pip(
        self,
        stdout_callback: Optional[Callable[[str], None]] = None,
        stderr_callback: Optional[Callable[[str], None]] = None,
    ):
        run_subprocess_with_streams(
            [str(self.python_exe), "-m", "ensurepip", "--upgrade"],
            stdout_callback,
            stderr_callback,
        )
        self.install_package(
            "pip",
            upgrade=True,
            stdout_callback=stdout_callback,
            stderr_callback=stderr_callback,
        )

    async def _abootstrap_pip(
        self,
        stdout_callback: Optional[Callable[[str], None]] = None,
        stderr_callback: Optional[Callable[[str], None]] = None,
    ):
        await arun_subprocess_with_streams(
            [str(self.python_exe), "-m", "ensurepip", "--upgrade"],
            stdout_callback=stdout_callback,
            stderr_callback=stderr_callback,
        )
        await self.ainstall_package(
            "pip",
            upgrade=True,
            stdout_callback=stdout_callback,
            stderr_callback=stderr_callback,
        )
