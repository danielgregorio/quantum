"""
Quantum Package Manager CLI

CLI commands for package management:
- quantum pkg init [path] - Initialize a new package
- quantum pkg publish [path] - Create publishable archive
- quantum pkg install <source> - Install package from path/URL
- quantum pkg remove <name> - Remove installed package
- quantum pkg list - List installed packages
- quantum pkg search <query> - Search packages
- quantum pkg info <name> - Show package details
"""

import argparse
import sys
from pathlib import Path
from typing import Optional


def create_pkg_parser(subparsers: argparse._SubParsersAction) -> None:
    """Create the 'pkg' subparser with all package commands."""
    pkg_parser = subparsers.add_parser(
        'pkg',
        help='Package management commands',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Quantum Package Manager - Share and reuse components',
        epilog="""
Examples:
  quantum pkg init ./my-component          # Create new package
  quantum pkg init -n my-ui -a "Me"        # Create with name and author
  quantum pkg install ./other-package      # Install from local path
  quantum pkg install https://github.com/user/pkg.git  # Install from git
  quantum pkg remove my-component          # Remove package
  quantum pkg list                         # List all packages
  quantum pkg search button                # Search for packages
  quantum pkg info my-component            # Show package details
  quantum pkg publish ./my-component       # Create archive for sharing
        """
    )

    pkg_subparsers = pkg_parser.add_subparsers(dest='pkg_command', help='Package command')

    # init command
    init_parser = pkg_subparsers.add_parser(
        'init',
        help='Initialize a new package'
    )
    init_parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Directory to initialize (default: current directory)'
    )
    init_parser.add_argument(
        '-n', '--name',
        help='Package name (default: directory name)'
    )
    init_parser.add_argument(
        '-d', '--description',
        default='',
        help='Package description'
    )
    init_parser.add_argument(
        '-a', '--author',
        default='',
        help='Package author'
    )
    init_parser.add_argument(
        '-l', '--license',
        default='MIT',
        help='License identifier (default: MIT)'
    )

    # publish command
    publish_parser = pkg_subparsers.add_parser(
        'publish',
        help='Create publishable package archive'
    )
    publish_parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Package directory (default: current directory)'
    )

    # install command
    install_parser = pkg_subparsers.add_parser(
        'install',
        help='Install a package'
    )
    install_parser.add_argument(
        'source',
        help='Package source (local path or git URL)'
    )
    install_parser.add_argument(
        '-v', '--version',
        help='Specific version to install'
    )
    install_parser.add_argument(
        '--no-deps',
        action='store_true',
        help='Skip dependency resolution'
    )

    # remove command
    remove_parser = pkg_subparsers.add_parser(
        'remove',
        help='Remove an installed package'
    )
    remove_parser.add_argument(
        'name',
        help='Package name to remove'
    )
    remove_parser.add_argument(
        '-v', '--version',
        help='Specific version to remove (default: all versions)'
    )

    # list command
    pkg_subparsers.add_parser(
        'list',
        help='List installed packages'
    )

    # search command
    search_parser = pkg_subparsers.add_parser(
        'search',
        help='Search installed packages'
    )
    search_parser.add_argument(
        'query',
        help='Search query'
    )

    # info command
    info_parser = pkg_subparsers.add_parser(
        'info',
        help='Show package details'
    )
    info_parser.add_argument(
        'name',
        help='Package name'
    )
    info_parser.add_argument(
        '-v', '--version',
        help='Specific version'
    )


def handle_pkg(args: argparse.Namespace) -> int:
    """Handle pkg command and subcommands."""
    # Lazy import to avoid circular imports
    try:
        from packages import PackageManager, PackageError
    except ImportError:
        # Try relative import
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from packages import PackageManager, PackageError

    if not args.pkg_command:
        print("[ERROR] No package command specified")
        print("Usage: quantum pkg <command> [options]")
        print("Commands: init, publish, install, remove, list, search, info")
        return 1

    pm = PackageManager()

    try:
        if args.pkg_command == 'init':
            return _handle_init(pm, args)
        elif args.pkg_command == 'publish':
            return _handle_publish(pm, args)
        elif args.pkg_command == 'install':
            return _handle_install(pm, args)
        elif args.pkg_command == 'remove':
            return _handle_remove(pm, args)
        elif args.pkg_command == 'list':
            return _handle_list(pm, args)
        elif args.pkg_command == 'search':
            return _handle_search(pm, args)
        elif args.pkg_command == 'info':
            return _handle_info(pm, args)
        else:
            print(f"[ERROR] Unknown package command: {args.pkg_command}")
            return 1

    except PackageError as e:
        print(f"[ERROR] {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return 1


def _handle_init(pm, args: argparse.Namespace) -> int:
    """Handle 'pkg init' command."""
    path = Path(args.path).resolve()

    print(f"[INFO] Initializing package in {path}")

    manifest = pm.init(
        path=str(path),
        name=args.name,
        description=args.description,
        author=args.author,
        license_id=args.license
    )

    print(f"[SUCCESS] Package '{manifest.name}' initialized!")
    print(f"   Version: {manifest.version}")
    print(f"   Main: {manifest.main}")
    print()
    print("Created files:")
    print("   quantum.yaml")
    print("   src/index.q")
    print("   examples/demo.q")
    print("   README.md")
    print()
    print("Next steps:")
    print(f"   1. Edit src/index.q to create your component")
    print(f"   2. Update quantum.yaml with description and keywords")
    print(f"   3. Run 'quantum pkg publish {args.path}' to create archive")

    return 0


def _handle_publish(pm, args: argparse.Namespace) -> int:
    """Handle 'pkg publish' command."""
    path = Path(args.path).resolve()

    print(f"[INFO] Publishing package from {path}")

    archive_path = pm.publish(str(path))

    print(f"[SUCCESS] Package archive created!")
    print(f"   Archive: {archive_path}")
    print()
    print("Share this archive or upload to a registry.")

    return 0


def _handle_install(pm, args: argparse.Namespace) -> int:
    """Handle 'pkg install' command."""
    source = args.source
    resolve_deps = not getattr(args, 'no_deps', False)

    print(f"[INFO] Installing package from {source}")

    installed = pm.install(
        source=source,
        version=args.version,
        resolve_deps=resolve_deps
    )

    if not installed:
        print("[WARN] No packages installed")
        return 0

    print(f"[SUCCESS] Installed {len(installed)} package(s):")
    for manifest in installed:
        print(f"   {manifest.name}@{manifest.version}")

    return 0


def _handle_remove(pm, args: argparse.Namespace) -> int:
    """Handle 'pkg remove' command."""
    name = args.name
    version = args.version

    if version:
        print(f"[INFO] Removing {name}@{version}")
    else:
        print(f"[INFO] Removing {name} (all versions)")

    removed = pm.remove(name, version)

    if removed:
        print(f"[SUCCESS] Package '{name}' removed")
        return 0
    else:
        print(f"[WARN] Package '{name}' not found")
        return 1


def _handle_list(pm, args: argparse.Namespace) -> int:
    """Handle 'pkg list' command."""
    packages = pm.list_packages()

    if not packages:
        print("[INFO] No packages installed")
        print()
        print("Install packages with:")
        print("   quantum pkg install <path-or-url>")
        return 0

    print(f"[INFO] Installed packages ({len(packages)}):")
    print()

    for pkg in packages:
        name = pkg['name']
        latest = pkg.get('latest', 'unknown')
        description = pkg.get('description', '')[:50]
        versions = pkg.get('versions', [])

        print(f"   {name}@{latest}")
        if description:
            print(f"      {description}")
        if len(versions) > 1:
            print(f"      Versions: {', '.join(versions)}")
        print()

    return 0


def _handle_search(pm, args: argparse.Namespace) -> int:
    """Handle 'pkg search' command."""
    query = args.query

    print(f"[INFO] Searching for '{query}'...")

    results = pm.search(query)

    if not results:
        print(f"[INFO] No packages found matching '{query}'")
        return 0

    print(f"[INFO] Found {len(results)} package(s):")
    print()

    for pkg in results:
        name = pkg['name']
        latest = pkg.get('latest', 'unknown')
        description = pkg.get('description', '')[:50]
        keywords = pkg.get('keywords', [])

        print(f"   {name}@{latest}")
        if description:
            print(f"      {description}")
        if keywords:
            print(f"      Keywords: {', '.join(keywords[:5])}")
        print()

    return 0


def _handle_info(pm, args: argparse.Namespace) -> int:
    """Handle 'pkg info' command."""
    name = args.name
    version = args.version

    manifest = pm.get_package(name, version)

    if not manifest:
        print(f"[ERROR] Package '{name}' not found")
        return 1

    pkg_path = pm.get_package_path(name, version)

    print(f"[INFO] Package: {manifest.name}")
    print()
    print(f"   Version:     {manifest.version}")
    print(f"   Description: {manifest.description or '(none)'}")
    print(f"   Author:      {manifest.author or '(none)'}")
    print(f"   License:     {manifest.license}")
    print(f"   Main:        {manifest.main}")
    print(f"   Path:        {pkg_path}")

    if manifest.keywords:
        print(f"   Keywords:    {', '.join(manifest.keywords)}")

    if manifest.dependencies:
        print()
        print("   Dependencies:")
        for dep_name, dep_version in manifest.dependencies.items():
            print(f"      {dep_name}: {dep_version}")

    if manifest.exports:
        print()
        print("   Exports:")
        for export in manifest.exports:
            print(f"      {export}")

    # Show available versions
    all_versions = pm.registry.get_all_versions(name)
    if len(all_versions) > 1:
        print()
        print(f"   All versions: {', '.join(all_versions)}")

    return 0
