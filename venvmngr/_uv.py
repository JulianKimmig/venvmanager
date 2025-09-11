"""uv-backed virtual environment manager.

Implements a `VenvManager` variant that leverages the `uv` CLI and a
`pyproject.toml` to create, sync and manage project virtual environments.
"""

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
    """Venv manager powered by the `uv` tool.

    This manager assumes a `pyproject.toml` and uses `uv` to add/remove
    dependencies and to create/sync the environment.
    """

    @classmethod
    def get_default_venv_name(cls) -> str:
        """Return the default virtual environment directory name.

        Reads `UV_PROJECT_ENVIRONMENT` and falls back to `.venv`.
        """
        return os.environ.get("UV_PROJECT_ENVIRONMENT", ".venv")

    def __init__(self, toml_path: Union[str, Path], env_path: Union[str, Path], **kwargs):
        """Initialize the manager.

        Args:
            toml_path (Path | str): Path to the `pyproject.toml`.
            env_path (Path | str): Path to the environment directory.
            **kwargs: Forwarded to the base manager if applicable.
        """
        self.toml_path = toml_path if isinstance(toml_path, Path) else Path(toml_path)
        self._enterpath = None
        super().__init__(env_path)

    def __enter__(self):
        """Enter the project directory context for uv operations."""
        self._enterpath = os.getcwd()
        os.chdir(self.toml_path.parent)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore previous working directory when leaving the context."""
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
        """Install a dependency using uv.

        Args:
            package_name: Package to install.
            version: Specific version or specifier.
            upgrade: Whether to upgrade the package.
            stdout_callback: Optional callback for stdout lines.
            stderr_callback: Optional callback for stderr lines.
        """
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
        Create a new virtual environment for a project.

        Args:
            toml_path: Path to the project's `pyproject.toml`.
            python: Optional Python version or interpreter path for `uv`.
            description: Optional project description when initializing.
            stdout_callback: Callback receiving stdout lines.
            stderr_callback: Callback receiving stderr lines.

        Returns:
            UVVenvManager: A new manager instance.
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

            env_path = toml_path.parent / cls.get_default_venv_name()
            mng = cls(toml_path, env_path)
            mng.install_package("pip", upgrade=True)
        finally:
            os.chdir(enterpath)
        return mng

    @staticmethod
    def check_toml_path(toml_path: Union[str, Path], create_path: bool = False) -> Path:
        """Validate and normalize a `pyproject.toml` path.

        Ensures the provided path refers to a file named `pyproject.toml`,
        optionally creates the parent directory, and returns the absolute
        path to the file.

        Args:
            toml_path: Path to the `pyproject.toml` file or its string form.
            create_path: When True, create the parent directory if missing.

        Returns:
            Path: Absolute path to the `pyproject.toml` file.

        Raises:
            ValueError: If the filename is not `pyproject.toml` or the parent
                directory does not exist (and `create_path` is False).
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
            Tuple[UVVenvManager, bool]: A tuple containing the manager instance and a boolean
            indicating if the environment was created.
        """
        toml_path = cls.check_toml_path(toml_path)
        env_path = toml_path.parent / cls.get_default_venv_name()
        if toml_path.exists() and env_path.exists():
            return cls(toml_path, env_path, **kwargs), False
        return cls.create_virtual_env(toml_path, **kwargs), True

    @classmethod
    def get_virtual_env(
        cls,
        env_path: Union[str, Path],
    ) -> UVVenvManager:
        """
        Return an VenvManager instance for an existing virtual environment.

        Args:
            env_path (Union[str, Path]): Path to the virtual environment.

        Returns:
            UVVenvManager: An instance managing the environment.

        Raises:
            ValueError: If the specified directory does not contain a valid environment.
        """
        if not isinstance(env_path, Path):
            env_path = Path(env_path)
        if not env_path.exists():
            raise ValueError("Invalid environment path.")
        if env_path.name == "pyproject.toml":
            tomlpath = cls.check_toml_path(env_path)
            if not tomlpath.exists():
                raise ValueError("Invalid toml path.")
            env_path = env_path.parent / cls.get_default_venv_name()
            if not env_path.exists():
                raise ValueError("Invalid environment path.")
            return UVVenvManager(tomlpath, env_path)

        return UVVenvManager(env_path.parent / "pyproject.toml", env_path)
