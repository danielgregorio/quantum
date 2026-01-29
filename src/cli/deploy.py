"""
Quantum CLI Deploy Command

Deploy Quantum applications to remote servers.
Usage: quantum deploy ./my-app --name my-app --target forge
"""

import os
import sys
import tarfile
import tempfile
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, List
import yaml

# Try to import requests, provide helpful error if missing
try:
    import requests
except ImportError:
    print("Error: 'requests' package is required for deploy functionality.")
    print("Install it with: pip install requests")
    sys.exit(1)


class DeployError(Exception):
    """Deployment error."""
    pass


class QuantumDeployer:
    """Handles Quantum application deployments."""

    # Files/directories to exclude from deployment
    EXCLUDE_PATTERNS = [
        '.git',
        '.gitignore',
        '__pycache__',
        '*.pyc',
        '*.pyo',
        '.env',
        '.env.local',
        '.env.*.local',
        'node_modules',
        '.venv',
        'venv',
        '*.log',
        '.DS_Store',
        'Thumbs.db',
        '.idea',
        '.vscode',
        '*.sqlite',
        '*.db',
        'tests',
        'test_*.py',
        '*_test.py',
    ]

    def __init__(self, config_path: str = 'quantum.config.yaml'):
        """Initialize deployer with configuration."""
        self.config = self._load_config(config_path)
        self.targets = self.config.get('deploy', {}).get('targets', {})

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from file."""
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file) as f:
                return yaml.safe_load(f) or {}
        return {}

    def deploy(
        self,
        path: str,
        name: Optional[str] = None,
        target: str = 'forge',
        env_vars: Optional[Dict[str, str]] = None,
        force: bool = False,
        verbose: bool = False
    ) -> Dict:
        """
        Deploy a Quantum application.

        Args:
            path: Path to the application directory
            name: Application name (default: directory name)
            target: Deployment target (default: forge)
            env_vars: Environment variables to set
            force: Overwrite existing deployment
            verbose: Show detailed output

        Returns:
            Deployment result dictionary
        """
        app_path = Path(path).resolve()

        # Validate path
        if not app_path.exists():
            raise DeployError(f"Path does not exist: {app_path}")

        if not app_path.is_dir():
            raise DeployError(f"Path is not a directory: {app_path}")

        # Validate it's a Quantum app
        if not self._is_quantum_app(app_path):
            raise DeployError(
                f"Not a valid Quantum app: {app_path}\n"
                "Must contain .q files or quantum.config.yaml"
            )

        # Determine app name
        if not name:
            name = app_path.name.lower().replace('_', '-').replace(' ', '-')

        # Validate name
        if not self._validate_name(name):
            raise DeployError(
                f"Invalid app name: {name}\n"
                "Use only lowercase letters, numbers, and hyphens. "
                "Must start with a letter (3-50 chars)."
            )

        # Get target configuration
        target_config = self._get_target_config(target)

        if verbose:
            print(f"[INFO] Deploying {name} to {target}")
            print(f"[INFO] Source: {app_path}")
            print(f"[INFO] Target URL: {target_config['url']}")

        # Create tarball
        print(f"[PACK] Creating deployment package...")
        tarball_path = self._create_tarball(app_path, name, verbose)

        if verbose:
            size_mb = tarball_path.stat().st_size / (1024 * 1024)
            print(f"[INFO] Package size: {size_mb:.2f} MB")

        try:
            # Upload and deploy
            print(f"[UPLOAD] Uploading to {target}...")
            result = self._upload_deploy(
                tarball_path=tarball_path,
                name=name,
                target_config=target_config,
                env_vars=env_vars,
                force=force,
                verbose=verbose
            )

            print(f"[SUCCESS] Deployed successfully!")
            print(f"[URL] {result.get('url', 'N/A')}")

            return result

        finally:
            # Cleanup tarball
            if tarball_path.exists():
                tarball_path.unlink()

    def _is_quantum_app(self, path: Path) -> bool:
        """Check if path contains a Quantum application."""
        # Check for .q files
        q_files = list(path.glob('**/*.q'))
        if q_files:
            return True

        # Check for quantum.config.yaml
        if (path / 'quantum.config.yaml').exists():
            return True

        # Check for components directory with .q files
        components_dir = path / 'components'
        if components_dir.exists():
            q_files = list(components_dir.glob('**/*.q'))
            if q_files:
                return True

        return False

    def _validate_name(self, name: str) -> bool:
        """Validate application name."""
        import re
        pattern = r'^[a-z][a-z0-9-]{2,49}$'
        return bool(re.match(pattern, name))

    def _get_target_config(self, target: str) -> Dict:
        """Get configuration for deployment target."""
        # Check configured targets
        if target in self.targets:
            config = self.targets[target]
            return {
                'url': config.get('url'),
                'api_key': config.get('api_key') or os.environ.get('QUANTUM_API_KEY'),
            }

        # Check environment variable
        env_url = os.environ.get(f'QUANTUM_DEPLOY_{target.upper()}_URL')
        if env_url:
            return {
                'url': env_url,
                'api_key': os.environ.get(f'QUANTUM_DEPLOY_{target.upper()}_KEY') or
                          os.environ.get('QUANTUM_API_KEY'),
            }

        # Default forge configuration
        if target == 'forge':
            return {
                'url': os.environ.get('QUANTUM_FORGE_URL', 'http://forge:9000'),
                'api_key': os.environ.get('QUANTUM_API_KEY'),
            }

        raise DeployError(
            f"Unknown deployment target: {target}\n"
            "Configure targets in quantum.config.yaml or set environment variables:\n"
            f"  QUANTUM_DEPLOY_{target.upper()}_URL\n"
            f"  QUANTUM_DEPLOY_{target.upper()}_KEY"
        )

    def _create_tarball(self, app_path: Path, name: str, verbose: bool = False) -> Path:
        """Create deployment tarball."""
        # Create temp file
        fd, tarball_path = tempfile.mkstemp(suffix='.tar.gz', prefix=f'quantum-{name}-')
        os.close(fd)
        tarball_path = Path(tarball_path)

        def should_exclude(path: Path) -> bool:
            """Check if path should be excluded."""
            name = path.name
            for pattern in self.EXCLUDE_PATTERNS:
                if pattern.startswith('*') and pattern.endswith('*'):
                    if pattern[1:-1] in name:
                        return True
                elif pattern.startswith('*.'):
                    if name.endswith(pattern[1:]):
                        return True
                elif pattern.endswith('*'):
                    if name.startswith(pattern[:-1]):
                        return True
                elif name == pattern:
                    return True
            return False

        with tarfile.open(tarball_path, 'w:gz') as tar:
            # Add app files
            for item in app_path.rglob('*'):
                # Skip excluded items
                if any(should_exclude(p) for p in [item] + list(item.parents)):
                    if verbose:
                        print(f"  [SKIP] {item.relative_to(app_path)}")
                    continue

                # Get relative path
                rel_path = item.relative_to(app_path)

                if item.is_file():
                    if verbose:
                        print(f"  [ADD] {rel_path}")
                    tar.add(item, arcname=str(rel_path))

            # Include quantum src/ if --include-runtime flag is used or if src/ doesn't exist in app
            # This ensures the latest runtime code is deployed
            include_runtime = self.config.get('deploy', {}).get('include_runtime', True)
            app_has_src = (app_path / 'src').exists()

            if include_runtime and not app_has_src:
                # Find the quantum src directory
                quantum_src = self._find_quantum_src()
                if quantum_src and quantum_src.exists():
                    if verbose:
                        print(f"  [INFO] Including quantum runtime from {quantum_src}")
                    for item in quantum_src.rglob('*'):
                        if should_exclude(item):
                            continue
                        if item.is_file():
                            rel_path = item.relative_to(quantum_src)
                            arcname = f'src/{rel_path}'
                            if verbose:
                                print(f"  [ADD] {arcname}")
                            tar.add(item, arcname=arcname)

            # Add cache bust file to invalidate Docker build cache
            import time
            cache_bust_content = f"deploy_timestamp={time.time()}\n".encode('utf-8')
            import io
            cache_info = tarfile.TarInfo(name='src/.cache_bust')
            cache_info.size = len(cache_bust_content)
            tar.addfile(cache_info, io.BytesIO(cache_bust_content))

        return tarball_path

    def _find_quantum_src(self) -> Optional[Path]:
        """Find the quantum src directory."""
        # Check relative to this file (in case running from installed package)
        cli_dir = Path(__file__).parent
        quantum_src = cli_dir.parent  # src/
        if (quantum_src / 'runtime').exists():
            return quantum_src

        # Check current working directory structure
        cwd = Path.cwd()
        for candidate in [cwd / 'src', cwd.parent / 'src', cwd.parent.parent / 'src']:
            if candidate.exists() and (candidate / 'runtime').exists():
                return candidate

        return None

    def _upload_deploy(
        self,
        tarball_path: Path,
        name: str,
        target_config: Dict,
        env_vars: Optional[Dict[str, str]] = None,
        force: bool = False,
        verbose: bool = False
    ) -> Dict:
        """Upload tarball and trigger deployment."""
        url = f"{target_config['url'].rstrip('/')}/api/deploy"

        # Prepare headers
        headers = {}
        if target_config.get('api_key'):
            headers['X-API-Key'] = target_config['api_key']

        # Prepare form data
        data = {
            'name': name,
            'force': str(force).lower(),
        }

        if env_vars:
            data['env_vars'] = json.dumps(env_vars)

        # Upload file
        with open(tarball_path, 'rb') as f:
            files = {'file': (f'{name}.tar.gz', f, 'application/gzip')}

            try:
                response = requests.post(
                    url,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=300  # 5 minute timeout for large deploys
                )

                if response.status_code == 401:
                    raise DeployError(
                        "Authentication failed. Check your API key.\n"
                        "Set QUANTUM_API_KEY environment variable or configure in quantum.config.yaml"
                    )

                if response.status_code == 409:
                    raise DeployError(
                        f"App '{name}' already exists. Use --force to overwrite."
                    )

                if not response.ok:
                    try:
                        error = response.json().get('detail', response.text)
                    except Exception:
                        error = response.text
                    raise DeployError(f"Deployment failed: {error}")

                return response.json()

            except requests.exceptions.ConnectionError:
                raise DeployError(
                    f"Could not connect to {target_config['url']}\n"
                    "Ensure the deploy service is running and accessible."
                )
            except requests.exceptions.Timeout:
                raise DeployError("Deployment timed out. The server may be busy.")


class QuantumAppsManager:
    """Manages deployed Quantum applications."""

    def __init__(self, config_path: str = 'quantum.config.yaml'):
        """Initialize apps manager."""
        self.deployer = QuantumDeployer(config_path)

    def list_apps(self, target: str = 'forge', verbose: bool = False) -> List[Dict]:
        """List deployed applications."""
        target_config = self.deployer._get_target_config(target)
        url = f"{target_config['url'].rstrip('/')}/api/apps"

        headers = {}
        if target_config.get('api_key'):
            headers['X-API-Key'] = target_config['api_key']

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json().get('apps', [])
        except requests.exceptions.RequestException as e:
            raise DeployError(f"Failed to list apps: {e}")

    def get_status(self, name: str, target: str = 'forge') -> Dict:
        """Get application status."""
        target_config = self.deployer._get_target_config(target)
        url = f"{target_config['url'].rstrip('/')}/api/apps/{name}"

        headers = {}
        if target_config.get('api_key'):
            headers['X-API-Key'] = target_config['api_key']

        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 404:
                raise DeployError(f"App '{name}' not found")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise DeployError(f"Failed to get status: {e}")

    def get_logs(
        self,
        name: str,
        target: str = 'forge',
        lines: int = 100
    ) -> str:
        """Get application logs."""
        target_config = self.deployer._get_target_config(target)
        url = f"{target_config['url'].rstrip('/')}/api/apps/{name}/logs"

        headers = {}
        if target_config.get('api_key'):
            headers['X-API-Key'] = target_config['api_key']

        params = {'lines': lines}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 404:
                raise DeployError(f"App '{name}' not found")
            response.raise_for_status()
            return response.json().get('logs', '')
        except requests.exceptions.RequestException as e:
            raise DeployError(f"Failed to get logs: {e}")

    def restart(self, name: str, target: str = 'forge') -> Dict:
        """Restart an application."""
        target_config = self.deployer._get_target_config(target)
        url = f"{target_config['url'].rstrip('/')}/api/apps/{name}/restart"

        headers = {}
        if target_config.get('api_key'):
            headers['X-API-Key'] = target_config['api_key']

        try:
            response = requests.post(url, headers=headers, timeout=60)
            if response.status_code == 404:
                raise DeployError(f"App '{name}' not found")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise DeployError(f"Failed to restart app: {e}")

    def stop(self, name: str, target: str = 'forge') -> Dict:
        """Stop an application."""
        target_config = self.deployer._get_target_config(target)
        url = f"{target_config['url'].rstrip('/')}/api/apps/{name}/stop"

        headers = {}
        if target_config.get('api_key'):
            headers['X-API-Key'] = target_config['api_key']

        try:
            response = requests.post(url, headers=headers, timeout=60)
            if response.status_code == 404:
                raise DeployError(f"App '{name}' not found")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise DeployError(f"Failed to stop app: {e}")

    def start(self, name: str, target: str = 'forge') -> Dict:
        """Start a stopped application."""
        target_config = self.deployer._get_target_config(target)
        url = f"{target_config['url'].rstrip('/')}/api/apps/{name}/start"

        headers = {}
        if target_config.get('api_key'):
            headers['X-API-Key'] = target_config['api_key']

        try:
            response = requests.post(url, headers=headers, timeout=60)
            if response.status_code == 404:
                raise DeployError(f"App '{name}' not found")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise DeployError(f"Failed to start app: {e}")

    def remove(self, name: str, target: str = 'forge', keep_data: bool = False) -> Dict:
        """Remove an application."""
        target_config = self.deployer._get_target_config(target)
        url = f"{target_config['url'].rstrip('/')}/api/apps/{name}"

        headers = {}
        if target_config.get('api_key'):
            headers['X-API-Key'] = target_config['api_key']

        params = {'keep_data': str(keep_data).lower()}

        try:
            response = requests.delete(url, headers=headers, params=params, timeout=60)
            if response.status_code == 404:
                raise DeployError(f"App '{name}' not found")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise DeployError(f"Failed to remove app: {e}")


def create_deploy_parser(subparsers) -> argparse.ArgumentParser:
    """Create deploy subcommand parser."""
    deploy_parser = subparsers.add_parser(
        'deploy',
        help='Deploy a Quantum application',
        description='Deploy a Quantum application to a remote server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  quantum deploy .                           # Deploy current directory
  quantum deploy ./my-app --name my-app      # Deploy with custom name
  quantum deploy . --target forge --force    # Force redeploy to forge
  quantum deploy . --env DB_HOST=postgres    # Set environment variables
        """
    )

    deploy_parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Path to the application directory (default: current directory)'
    )

    deploy_parser.add_argument(
        '--name', '-n',
        help='Application name (default: directory name)'
    )

    deploy_parser.add_argument(
        '--target', '-t',
        default='forge',
        help='Deployment target (default: forge)'
    )

    deploy_parser.add_argument(
        '--env', '-e',
        action='append',
        dest='env_vars',
        metavar='KEY=VALUE',
        help='Environment variable (can be used multiple times)'
    )

    deploy_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Overwrite existing deployment'
    )

    deploy_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output'
    )

    return deploy_parser


def create_apps_parser(subparsers) -> argparse.ArgumentParser:
    """Create apps subcommand parser."""
    apps_parser = subparsers.add_parser(
        'apps',
        help='Manage deployed applications',
        description='List and manage deployed Quantum applications',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  quantum apps                    # List all apps
  quantum apps status my-app      # Get app status
  quantum apps logs my-app        # View app logs
  quantum apps restart my-app     # Restart app
  quantum apps stop my-app        # Stop app
  quantum apps start my-app       # Start stopped app
  quantum apps remove my-app      # Remove app
        """
    )

    apps_subparsers = apps_parser.add_subparsers(dest='apps_command')

    # List (default)
    list_parser = apps_subparsers.add_parser('list', help='List deployed apps')
    list_parser.add_argument('--target', '-t', default='forge', help='Target server')

    # Status
    status_parser = apps_subparsers.add_parser('status', help='Get app status')
    status_parser.add_argument('name', help='Application name')
    status_parser.add_argument('--target', '-t', default='forge', help='Target server')

    # Logs
    logs_parser = apps_subparsers.add_parser('logs', help='View app logs')
    logs_parser.add_argument('name', help='Application name')
    logs_parser.add_argument('--lines', '-n', type=int, default=100, help='Number of lines')
    logs_parser.add_argument('--target', '-t', default='forge', help='Target server')

    # Restart
    restart_parser = apps_subparsers.add_parser('restart', help='Restart app')
    restart_parser.add_argument('name', help='Application name')
    restart_parser.add_argument('--target', '-t', default='forge', help='Target server')

    # Stop
    stop_parser = apps_subparsers.add_parser('stop', help='Stop app')
    stop_parser.add_argument('name', help='Application name')
    stop_parser.add_argument('--target', '-t', default='forge', help='Target server')

    # Start
    start_parser = apps_subparsers.add_parser('start', help='Start stopped app')
    start_parser.add_argument('name', help='Application name')
    start_parser.add_argument('--target', '-t', default='forge', help='Target server')

    # Remove
    remove_parser = apps_subparsers.add_parser('remove', help='Remove app')
    remove_parser.add_argument('name', help='Application name')
    remove_parser.add_argument('--keep-data', action='store_true', help='Keep app data files')
    remove_parser.add_argument('--target', '-t', default='forge', help='Target server')

    return apps_parser


def handle_deploy(args) -> int:
    """Handle deploy command."""
    try:
        deployer = QuantumDeployer()

        # Parse environment variables
        env_vars = None
        if args.env_vars:
            env_vars = {}
            for env in args.env_vars:
                if '=' not in env:
                    print(f"[ERROR] Invalid env var format: {env}")
                    print("Use: --env KEY=VALUE")
                    return 1
                key, value = env.split('=', 1)
                env_vars[key] = value

        deployer.deploy(
            path=args.path,
            name=args.name,
            target=args.target,
            env_vars=env_vars,
            force=args.force,
            verbose=args.verbose
        )
        return 0

    except DeployError as e:
        print(f"[ERROR] {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return 1


def handle_apps(args) -> int:
    """Handle apps command."""
    try:
        manager = QuantumAppsManager()
        target = getattr(args, 'target', 'forge')

        # Default to list if no subcommand
        command = args.apps_command or 'list'

        if command == 'list':
            apps = manager.list_apps(target)
            if not apps:
                print("No apps deployed.")
                return 0

            print(f"{'NAME':<20} {'STATUS':<10} {'VERSION':<8} {'URL'}")
            print('-' * 70)
            for app in apps:
                print(f"{app['name']:<20} {app['status']:<10} v{app['version']:<6} {app['url']}")

        elif command == 'status':
            status = manager.get_status(args.name, target)
            print(f"Name:       {status['name']}")
            print(f"Status:     {status['status']}")
            print(f"Container:  {status.get('container_id', 'N/A')}")
            print(f"Version:    v{status['version']}")
            print(f"URL:        {status['url']}")
            if status.get('health'):
                print(f"Health:     {status['health'].get('status', 'N/A')}")
            if status.get('resources'):
                res = status['resources']
                print(f"CPU:        {res.get('cpu_percent', 0):.1f}%")
                print(f"Memory:     {res.get('memory_usage_mb', 0):.1f} MB ({res.get('memory_percent', 0):.1f}%)")

        elif command == 'logs':
            logs = manager.get_logs(args.name, target, args.lines)
            print(logs)

        elif command == 'restart':
            result = manager.restart(args.name, target)
            print(f"[SUCCESS] {result.get('message', 'App restarted')}")

        elif command == 'stop':
            result = manager.stop(args.name, target)
            print(f"[SUCCESS] {result.get('message', 'App stopped')}")

        elif command == 'start':
            result = manager.start(args.name, target)
            print(f"[SUCCESS] {result.get('message', 'App started')}")

        elif command == 'remove':
            result = manager.remove(args.name, target, getattr(args, 'keep_data', False))
            print(f"[SUCCESS] {result.get('message', 'App removed')}")

        return 0

    except DeployError as e:
        print(f"[ERROR] {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    # For standalone testing
    parser = argparse.ArgumentParser(description='Quantum Deploy CLI')
    subparsers = parser.add_subparsers(dest='command')

    create_deploy_parser(subparsers)
    create_apps_parser(subparsers)

    args = parser.parse_args()

    if args.command == 'deploy':
        sys.exit(handle_deploy(args))
    elif args.command == 'apps':
        sys.exit(handle_apps(args))
    else:
        parser.print_help()
        sys.exit(1)
