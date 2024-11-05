# __main__.py

import argparse
from pathlib import Path
from . import create_virtual_env, get_or_create_virtual_env


def main():
    parser = argparse.ArgumentParser(
        description="Manage Python virtual environments and packages"
    )
    parser.add_argument(
        "--env", type=str, required=True, help="Path to the virtual environment"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Create environment
    subparsers.add_parser(
        "create", help="Create a new virtual environment at the specified path"
    )

    # Install package
    install_parser = subparsers.add_parser(
        "install", help="Install a package in the virtual environment"
    )
    install_parser.add_argument(
        "package", type=str, help="Name of the package to install"
    )
    install_parser.add_argument(
        "--version", type=str, help="Version of the package to install"
    )
    install_parser.add_argument(
        "--upgrade",
        action="store_true",
        help="Upgrade the package if already installed",
    )

    # List packages
    subparsers.add_parser(
        "list", help="List all packages installed in the virtual environment"
    )

    # Check for package update
    update_parser = subparsers.add_parser(
        "update-check", help="Check if a package has an update available"
    )
    update_parser.add_argument(
        "package", type=str, help="Name of the package to check for updates"
    )

    args = parser.parse_args()
    env_path = Path(args.env).expanduser()

    if args.command == "create":
        create_virtual_env(env_path)
        print(f"Virtual environment created at {env_path}")

    else:
        env_manager, new = get_or_create_virtual_env(env_path)

        if args.command == "install":
            package = args.package
            version = args.version
            upgrade = args.upgrade
            try:
                env_manager.install_package(package, version=version, upgrade=upgrade)
                print(f"Package '{package}' installed successfully.")
            except ValueError as e:
                print(f"Error: {e}")

        elif args.command == "list":
            packages = env_manager.all_packages()
            for pkg in packages:
                print(f"{pkg['name']}=={pkg['version']}")

        elif args.command == "update-check":
            package = args.package
            (
                update_available,
                latest_version,
                current_version,
            ) = env_manager.package_update_available(package)
            if update_available:
                print(
                    f"Update available for {package}: {current_version} -> {latest_version}"
                )
            else:
                print(f"{package} is up-to-date (version {current_version})")


if __name__ == "__main__":
    main()
