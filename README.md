venvmngr — Manage Python virtual environments (venv and uv)

venvmngr is a tiny, pragmatic toolkit for creating and managing Python virtual environments from code or a simple CLI. It currently supports two backends:

- Standard library venv + pip (simple, zero extra tools)
- uv-backed workflow (pyproject.toml + uv add/remove/lock/sync)

It’s designed to be embedded in other apps or automation, with streaming callbacks for subprocess output and a straightforward API.


Highlights

- Two backends: built-in venv/pip and uv/pyproject
- Clean Python API with sensible defaults
- Simple CLI for common tasks (create, install, list, update-check)
- Streaming stdout/stderr callbacks for progress reporting
- Utilities to locate system Python interpreters
- Optional integration with subprocess-monitor for non-blocking module runs


Installation

- pip: `pip install venvmngr`
- uv: `uv add venvmngr`

Requirements

- Python >= 3.9
- Runtime deps: requests, packaging, uv (for uv workflow), subprocess-monitor (optional), psutil (optional)
  - psutil and subprocess-monitor are only used when you opt into non-blocking process runs via `SUBPROCESS_MONITOR_PORT`.


Quickstart

CLI (venv/pip backend)

The CLI manages a specific environment directory and uses the standard venv + pip flow.

Examples:

- Create an environment:
  - `python -m venvmngr --env .venv create`
  - or, after installing: `venvmngr --env .venv create`

- Install a package:
  - `venvmngr --env .venv install requests`
  - with a version: `venvmngr --env .venv install requests --version 2.32.3`
  - upgrade: `venvmngr --env .venv install requests --upgrade`

- List packages:
  - `venvmngr --env .venv list`

- Check for updates of a specific package:
  - `venvmngr --env .venv update-check requests`

Python API (venv/pip backend)

Use the `VenvManager` to create and manage a venv-driven environment:

```python
from venvmngr import VenvManager

# Create or open an environment
mngr, created = VenvManager.get_or_create_virtual_env(".venv")

# Install packages (supports exact pins and specifiers)
mngr.install_package("requests", version=">=2.31")

# List packages
for pkg in mngr.all_packages():
    print(pkg["name"], pkg["version"])  # version is a packaging.version.Version

# Check for updates (compares to PyPI)
update, latest, current = mngr.package_update_available("requests")
if update:
    print(f"Update available: {current} -> {latest}")

# Run a module inside the venv
mngr.run_module("pip", ["--version"])  # blocks by default
```

uv Workflow (pyproject + uv)

Use `UVVenvManager` when a project uses `pyproject.toml` and the uv tool:

```python
from pathlib import Path
from venvmngr import UVVenvManager

project = Path("/path/to/project")
toml = project / "pyproject.toml"

# Create or open a uv environment
uv_mngr, created = UVVenvManager.get_or_create_virtual_env(toml)

# Install a dependency via `uv add` and sync the environment
uv_mngr.install_package("httpx", version=">=0.27")

# Remove a dependency
uv_mngr.remove_package("httpx")

# List packages (delegates to pip inside the created venv)
for pkg in uv_mngr.all_packages():
    print(pkg)
```

Notes:

- `UVVenvManager` runs uv commands in the project directory that contains `pyproject.toml`.
- By default the environment directory is `.venv` (can be overridden with `UV_PROJECT_ENVIRONMENT`).


Key Concepts and API

Public imports from `venvmngr`:

- `VenvManager` — venv/pip manager
- `UVVenvManager` — uv-backed manager
- `create_virtual_env(path, ...)` — alias to `VenvManager.create_virtual_env`
- `get_or_create_virtual_env(path, ...)` — alias to `VenvManager.get_or_create_virtual_env`
- `get_virtual_env(path)` — alias to `VenvManager.get_virtual_env`
- `locate_system_pythons()` — discover system Python interpreters
- `get_python_executable()` — robust Python path resolution (PyInstaller-aware)

VenvManager

- `create_virtual_env(env_path, min_python=None, max_python=None, use="default", python_executable=None, stdout_callback=None, stderr_callback=None) -> VenvManager`
  - Creates a venv with the chosen interpreter.
  - If `python_executable` is not provided, probes system interpreters with `locate_system_pythons()` and optionally filters by version range.
  - `use="latest"` chooses the highest compatible version.

- `get_or_create_virtual_env(env_path, **kwargs) -> (VenvManager, bool)`
  - Returns a manager and a flag indicating whether the env was created.

- `get_virtual_env(env_path) -> VenvManager`
  - Opens an existing environment. Raises if invalid.

- `install_package(name, version=None, upgrade=False, stdout_callback=None, stderr_callback=None)`
  - Installs via `pip install`. `version` can be exact (e.g. `"2.2.0"`, becomes `name==2.2.0`) or a specifier (e.g. `">=2.2.0"`).
  - Underscores in names are normalized to hyphens.

- `all_packages() -> list[dict]`
  - Returns `[{"name": str, "version": Version}, ...]` using `pip list --format=json`.

- `remove_package(name)`
  - Uninstalls via `pip uninstall -y`.

- `package_is_installed(name) -> bool`, `get_package_version(name) -> Version | None`

- `package_update_available(name) -> (bool, Version | None, Version | None)`
  - Compares local version to PyPI’s latest (via the PyPI JSON API).

- `run_module(module, args: list[str] = [], block: bool = True, **kwargs)`
  - Executes `python -m <module>` inside the env. If `block=True`, returns `subprocess.CompletedProcess`.
  - If `block=False` and `SUBPROCESS_MONITOR_PORT` is set, integrates with `subprocess-monitor` and returns a `psutil.Process` (kills the process if the manager dies). Otherwise returns a `subprocess.Popen`.

UVVenvManager (inherits VenvManager)

- `create_virtual_env(toml_path, python=None, description=None, stdout_callback=None, stderr_callback=None) -> UVVenvManager`
  - Ensures `pyproject.toml` exists (creates a minimal one with `uv init` if missing) and creates a uv-managed venv (`uv venv`).
  - Installs/updates `pip` inside the env.

- `get_or_create_virtual_env(toml_path, **kwargs) -> (UVVenvManager, bool)`
  - Uses `pyproject.toml` and the default venv directory (usually `.venv`).

- `get_virtual_env(path) -> UVVenvManager`
  - Accepts either an env directory or a `pyproject.toml` path.

- `install_package(name, version=None, upgrade=False, stdout_callback=None, stderr_callback=None)`
  - Uses `uv add`, optionally `uv lock --upgrade-package <name>`, then `uv sync`.

- `remove_package(name)`
  - Uses `uv remove` and `uv sync`.

- `get_default_venv_name() -> str`
  - Defaults to `.venv`, overridable via `UV_PROJECT_ENVIRONMENT`.


Utilities

- `locate_system_pythons()`
  - Uses `where` (Windows) or `which` (POSIX) to find `python` executables and probes them for versions.

- `run_subprocess_with_streams(args, stdout_callback=None, stderr_callback=None)`
  - Runs a subprocess and streams lines to the provided callbacks, raising on non-zero exit.

- `get_python_executable()`
  - Returns a robust Python interpreter path; handles PyInstaller contexts by falling back to a system Python.


Callbacks and Streaming Output

Package installation, uv operations, and environment creation can stream progress lines via `stdout_callback` and `stderr_callback` callables:

```python
def on_out(line: str):
    print(line, end="")

def on_err(line: str):
    print(line, end="")

mngr.install_package("pip", upgrade=True, stdout_callback=on_out, stderr_callback=on_err)
```


Choosing a Python Version (venv backend)

When creating an environment with `VenvManager.create_virtual_env(...)`, you can:

- Provide an explicit interpreter: `python_executable="/usr/bin/python3.12"`
- Constrain versions and let venvmngr choose from discovered interpreters:
  - `min_python="3.11"`, `max_python="3.12"`, `use="latest"`

Example:

```python
VenvManager.create_virtual_env(
    ".venv",
    min_python="3.11",
    max_python="3.12",
    use="latest",
)
```


CLI Reference

Base invocation: `venvmngr --env <path> <command> [options]`

- `create` — Create a new environment at `--env`.
- `install <package> [--version <ver>] [--upgrade]` — Install a package (exact pin or specifier).
- `list` — List installed packages.
- `update-check <package>` — Compare installed version to PyPI.

Note: The CLI targets the venv/pip backend. The uv manager is currently exposed via the Python API.


Development

- Use uv for dev setup:
  - `uv sync --dev`
  - `uv run pytest -q`
- Lint/format via pre-commit (ruff, flake8):
  - `uv run pre-commit run -a`
- Project configuration: see `pyproject.toml`

License

MIT — see LICENCE for details.
