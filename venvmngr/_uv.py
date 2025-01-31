from __future__ import annotations
from pathlib import Path
from typing import Union, Tuple, Optional
import os
from collections.abc import Callable
import subprocess
from packaging.version import Version
from ._venv import VenvManager
from .utils import run_subprocess_with_streams, get_python_executable


PYEXE = get_python_executable()


class UVVenvManager(VenvManager):
    def __init__(self, toml_path, env_path, **kwargs):
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
            _install = [PYEXE, "-m", "uv", "add", package_version]

            run_subprocess_with_streams(
                _install,
                stdout_callback,
                stderr_callback,
            )

            if upgrade:
                _upgrade = [
                    PYEXE,
                    "-m",
                    "uv",
                    "lock",
                    "--upgrade-package",
                    package_name,
                ]
                run_subprocess_with_streams(
                    _upgrade,
                    stdout_callback,
                    stderr_callback,
                )
            run_subprocess_with_streams(
                [PYEXE, "-m", "uv", "sync"], stdout_callback, stderr_callback
            )

    def remove_package(self, package_name: str):
        """
        Remove a package from the virtual environment.

        Args:
            package_name (str): The name of the package to remove.
        """
        with self:
            try:
                subprocess.check_call([PYEXE, "-m", "uv", "remove", package_name])
            except subprocess.CalledProcessError as exc:
                raise ValueError("Failed to uninstall package.") from exc
            run_subprocess_with_streams(
                [PYEXE, "-m", "uv", "sync"],
            )

    @classmethod
    def create_virtual_env(
        cls,
        toml_path: Union[str, Path],
        python: Optional[Union[str, Version]] = None,
        description: Optional[str] = None,
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
                init_cmd = [
                    PYEXE,
                    "-m",
                    "uv",
                    "init",
                    "--no-workspace",
                    "--no-pin-python",
                    "--no-readme",
                ]
                if python:
                    init_cmd.extend(["--python", str(python)])
                if description:
                    init_cmd.extend(["--description", description])
                subprocess.run(init_cmd)

            # Create the virtual environment
            # Use Popen to create the virtual environment and stream output
            _env_init = [PYEXE, "-m", "uv", "venv"]
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
        if not toml_path.parent.exists():
            raise ValueError("Invalid toml path.")
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
        if not env_path.exists():
            raise ValueError("Invalid environment path.")
        if env_path.name == "pyproject.toml":
            tomlpath = cls.check_toml_path(env_path)
            if not tomlpath.exists():
                raise ValueError("Invalid toml path.")
            env_path = env_path.parent / ".venv"
            if not env_path.exists():
                raise ValueError("Invalid environment path.")
            return UVVenvManager(tomlpath, env_path)

        return UVVenvManager(env_path.parent / "pyproject.toml", env_path)
