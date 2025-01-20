from __future__ import annotations
from pathlib import Path
from typing import Union, Tuple, Optional
import os
from collections.abc import Callable
import subprocess
from packaging.version import Version
from ._venv import VenvManager
from .utils import run_subprocess_with_streams


class UVVenvManager(VenvManager):
    def __init__(self, toml_path, env_path):
        self.toml_path = toml_path
        self._enterpath = None
        super().__init__(env_path)

    def __enter__(self):
        self._enterpath = os.getcwd()
        os.chdir(self.toml_path.parent)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._enterpath:
            os.chdir(self._enterpath)
            self._enterpath = None

    def install_package(
        self,
        package_name: str,
        version: Optional[Union[Version, str]] = None,
        upgrade: bool = False,
        stdout_callback: Optional[Callable[[str], None]] = None,
        stderr_callback: Optional[Callable[[str], None]] = None,
    ):
        package_version = self.package_name_cleaner(package_name, version)
        with self:
            # if ">" in package_version or "<" in package_version:
            # package_version = f'"{package_version}"'
            _install = ["uv", "add", package_version]

            run_subprocess_with_streams(
                _install,
                stdout_callback,
                stderr_callback,
            )

            if upgrade:
                _upgrade = ["uv", "lock", "--upgrade-package", package_name]
                run_subprocess_with_streams(
                    _upgrade,
                    stdout_callback,
                    stderr_callback,
                )
            run_subprocess_with_streams(
                ["uv", "sync"], stdout_callback, stderr_callback
            )

    def remove_package(self, package_name: str):
        """
        Remove a package from the virtual environment.

        Args:
            package_name (str): The name of the package to remove.
        """
        with self:
            try:
                subprocess.check_call(["uv", "remove", package_name])
            except subprocess.CalledProcessError as exc:
                raise ValueError("Failed to uninstall package.") from exc
            run_subprocess_with_streams(
                ["uv", "sync"],
            )

    @classmethod
    def create_virtual_env(
        cls,
        toml_path: Union[str, Path],
        python: Optional[Union[str, Version]] = None,
        stdout_callback: Optional[Callable[[str], None]] = None,
        stderr_callback: Optional[Callable[[str], None]] = None,
    ) -> UVVenvManager:
        """
        Create a new virtual environment at the specified path.

        Args:
            toml_path (str): Path to the environment toml.
            **kwargs: Additional keyword arguments to pass to the VenvManager constructor.

        Returns:
            VenvManager: A new VenvManager instance.
        """
        toml_path = cls.check_toml_path(toml_path, create_path=True)
        enterpath = os.getcwd()
        try:
            os.chdir(toml_path.parent)
            if not toml_path.exists():
                subprocess.run(["uv", "init", "--no-workspace"])

            # Create the virtual environment
            # Use Popen to create the virtual environment and stream output
            _env_init = ["uv", "venv"]
            if python:
                _env_init.extend(["--python", str(python)])

            run_subprocess_with_streams(
                _env_init,
                stdout_callback,
                stderr_callback,
            )

            env_path = toml_path.parent / ".venv"
            mng = cls(toml_path, env_path)
            mng.install_package("pip", upgrade=True)
        finally:
            os.chdir(enterpath)
        return mng

    @staticmethod
    def check_toml_path(toml_path: Union[str, Path], create_path=False) -> bool:
        """
        Check if the specified path is a valid toml file.

        Args:
            toml_path (str): Path to the toml file.

        Returns:
            bool: True if the path is a valid toml file, False otherwise.
        """
        toml_path = Path(toml_path) if not isinstance(toml_path, Path) else toml_path
        if toml_path.name != "pyproject.toml":
            raise ValueError("Invalid toml file.")
        if create_path:
            if not toml_path.parent.exists():
                toml_path.parent.mkdir(parents=True)
        return toml_path.absolute()

    @classmethod
    def get_or_create_virtual_env(
        cls, toml_path: Union[str, Path], **kwargs
    ) -> Tuple[UVVenvManager, bool]:
        """
        Get or create a virtual environment at the specified path.

        Args:
            toml_path (str): Path to the environment toml.
            **kwargs: Additional keyword arguments to pass to the VenvManager constructor.

        Returns:
            Tuple[VenvManager, bool]: A tuple containing the VenvManager instance and a boolean
            indicating if the environment was created.
        """
        toml_path = cls.check_toml_path(toml_path)
        env_path = toml_path.parent / ".venv"
        if toml_path.exists() and env_path.exists():
            return cls(toml_path, env_path, **kwargs), False
        return cls.create_virtual_env(toml_path, **kwargs), True
