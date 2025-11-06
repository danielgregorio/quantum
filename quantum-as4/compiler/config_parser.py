"""
Application Configuration Parser

Parses application.yaml and validates configuration
"""

import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path
from enum import Enum


class TargetPlatform(Enum):
    """Target platform types"""
    WEB = "web"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    CLI = "cli"


@dataclass
class WebConfig:
    """Web-specific configuration"""
    title: str
    favicon: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    pwa: Dict[str, Any] = field(default_factory=dict)
    optimize: bool = False
    source_maps: bool = True


@dataclass
class MobileConfig:
    """Mobile-specific configuration"""
    type: str = "react-native"  # or "flutter"
    bundle_id: str = "com.example.app"
    app_name: str = "App"
    icon: Optional[str] = None
    splash_screen: Optional[str] = None
    orientation: str = "portrait"
    platforms: List[str] = field(default_factory=lambda: ["android", "ios"])
    android: Dict[str, Any] = field(default_factory=dict)
    ios: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DesktopConfig:
    """Desktop-specific configuration"""
    type: str = "tauri"  # or "electron"
    name: str = "App"
    identifier: str = "com.example.app"
    icon: Optional[str] = None
    window: Dict[str, Any] = field(default_factory=dict)
    system_tray: Dict[str, Any] = field(default_factory=dict)
    platforms: List[str] = field(default_factory=lambda: ["windows", "macos", "linux"])


@dataclass
class CLIConfig:
    """CLI-specific configuration"""
    type: str = "rich"  # or "rust-tui"
    name: str = "app"
    executable: bool = True
    colors: bool = True
    mouse: bool = True
    keyboard_shortcuts: Dict[str, str] = field(default_factory=dict)


@dataclass
class TargetConfig:
    """Configuration for a specific target platform"""
    platform: TargetPlatform
    enabled: bool
    output: str
    config: Any  # WebConfig, MobileConfig, DesktopConfig, or CLIConfig


@dataclass
class BuildConfig:
    """Build configuration"""
    mode: str = "development"  # or "production"
    source_maps: bool = True
    hot_reload: bool = True
    watch: bool = True
    optimize: Dict[str, bool] = field(default_factory=dict)
    type_checking: Dict[str, bool] = field(default_factory=dict)


@dataclass
class ApplicationConfig:
    """Complete application configuration from application.yaml"""
    # Application metadata
    name: str
    version: str
    description: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None
    homepage: Optional[str] = None

    # Entry point
    entry_mxml: str = "src/Main.mxml"
    assets_dir: Optional[str] = None

    # Target platforms
    targets: List[TargetConfig] = field(default_factory=list)

    # Build configuration
    build: BuildConfig = field(default_factory=BuildConfig)

    # Assets
    assets: Dict[str, List[str]] = field(default_factory=dict)

    # Dependencies
    dependencies: List[str] = field(default_factory=list)

    # Platform-specific overrides
    overrides: Dict[str, Any] = field(default_factory=dict)

    # Deployment
    deploy: Dict[str, Any] = field(default_factory=dict)


class ConfigParser:
    """Parse and validate application.yaml"""

    def parse(self, config_file: str) -> ApplicationConfig:
        """
        Parse application.yaml file

        Args:
            config_file: Path to application.yaml

        Returns:
            ApplicationConfig object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If configuration is invalid
        """
        config_path = Path(config_file)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        # Load YAML
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)

        # Parse application section
        app_data = data.get('application', {})
        if not app_data:
            raise ValueError("Missing 'application' section in configuration")

        name = app_data.get('name')
        version = app_data.get('version')

        if not name:
            raise ValueError("Application name is required")
        if not version:
            raise ValueError("Application version is required")

        # Parse entry point
        entry_data = data.get('entry', {})
        entry_mxml = entry_data.get('mxml', 'src/Main.mxml')
        assets_dir = entry_data.get('assets')

        # Parse targets
        targets_data = data.get('targets', {})
        targets = self._parse_targets(targets_data)

        if not any(t.enabled for t in targets):
            raise ValueError("At least one target must be enabled")

        # Parse build config
        build_data = data.get('build', {})
        build = self._parse_build_config(build_data)

        # Parse assets
        assets = data.get('assets', {})

        # Parse dependencies
        dependencies = data.get('dependencies', [])

        # Parse overrides
        overrides = data.get('overrides', {})

        # Parse deploy
        deploy = data.get('deploy', {})

        return ApplicationConfig(
            name=name,
            version=version,
            description=app_data.get('description'),
            author=app_data.get('author'),
            license=app_data.get('license'),
            homepage=app_data.get('homepage'),
            entry_mxml=entry_mxml,
            assets_dir=assets_dir,
            targets=targets,
            build=build,
            assets=assets,
            dependencies=dependencies,
            overrides=overrides,
            deploy=deploy
        )

    def _parse_targets(self, targets_data: Dict) -> List[TargetConfig]:
        """Parse targets section"""
        targets = []

        # Web target
        if 'web' in targets_data:
            web_data = targets_data['web']
            if web_data.get('enabled', False):
                targets.append(TargetConfig(
                    platform=TargetPlatform.WEB,
                    enabled=True,
                    output=web_data.get('output', 'dist/web'),
                    config=self._parse_web_config(web_data.get('config', {}))
                ))

        # Mobile target
        if 'mobile' in targets_data:
            mobile_data = targets_data['mobile']
            if mobile_data.get('enabled', False):
                targets.append(TargetConfig(
                    platform=TargetPlatform.MOBILE,
                    enabled=True,
                    output=mobile_data.get('output', 'dist/mobile'),
                    config=self._parse_mobile_config(mobile_data.get('config', {}))
                ))

        # Desktop target
        if 'desktop' in targets_data:
            desktop_data = targets_data['desktop']
            if desktop_data.get('enabled', False):
                targets.append(TargetConfig(
                    platform=TargetPlatform.DESKTOP,
                    enabled=True,
                    output=desktop_data.get('output', 'dist/desktop'),
                    config=self._parse_desktop_config(desktop_data.get('config', {}))
                ))

        # CLI target
        if 'cli' in targets_data:
            cli_data = targets_data['cli']
            if cli_data.get('enabled', False):
                targets.append(TargetConfig(
                    platform=TargetPlatform.CLI,
                    enabled=True,
                    output=cli_data.get('output', 'dist/cli'),
                    config=self._parse_cli_config(cli_data.get('config', {}))
                ))

        return targets

    def _parse_web_config(self, config_data: Dict) -> WebConfig:
        """Parse web-specific configuration"""
        return WebConfig(
            title=config_data.get('title', 'Quantum App'),
            favicon=config_data.get('favicon'),
            meta=config_data.get('meta', {}),
            pwa=config_data.get('pwa', {}),
            optimize=config_data.get('optimize', False),
            source_maps=config_data.get('source_maps', True)
        )

    def _parse_mobile_config(self, config_data: Dict) -> MobileConfig:
        """Parse mobile-specific configuration"""
        return MobileConfig(
            type=config_data.get('type', 'react-native'),
            bundle_id=config_data.get('bundle_id', 'com.example.app'),
            app_name=config_data.get('app_name', 'App'),
            icon=config_data.get('icon'),
            splash_screen=config_data.get('splash_screen'),
            orientation=config_data.get('orientation', 'portrait'),
            platforms=config_data.get('platforms', ['android', 'ios']),
            android=config_data.get('android', {}),
            ios=config_data.get('ios', {})
        )

    def _parse_desktop_config(self, config_data: Dict) -> DesktopConfig:
        """Parse desktop-specific configuration"""
        return DesktopConfig(
            type=config_data.get('type', 'tauri'),
            name=config_data.get('name', 'App'),
            identifier=config_data.get('identifier', 'com.example.app'),
            icon=config_data.get('icon'),
            window=config_data.get('window', {}),
            system_tray=config_data.get('system_tray', {}),
            platforms=config_data.get('platforms', ['windows', 'macos', 'linux'])
        )

    def _parse_cli_config(self, config_data: Dict) -> CLIConfig:
        """Parse CLI-specific configuration"""
        return CLIConfig(
            type=config_data.get('type', 'rich'),
            name=config_data.get('name', 'app'),
            executable=config_data.get('executable', True),
            colors=config_data.get('colors', True),
            mouse=config_data.get('mouse', True),
            keyboard_shortcuts=config_data.get('keyboard_shortcuts', {})
        )

    def _parse_build_config(self, build_data: Dict) -> BuildConfig:
        """Parse build configuration"""
        return BuildConfig(
            mode=build_data.get('mode', 'development'),
            source_maps=build_data.get('source_maps', True),
            hot_reload=build_data.get('hot_reload', True),
            watch=build_data.get('watch', True),
            optimize=build_data.get('optimize', {}),
            type_checking=build_data.get('type_checking', {})
        )


# Example usage
if __name__ == '__main__':
    parser = ConfigParser()

    # Create example config
    example_yaml = """
application:
  name: "Example App"
  version: "1.0.0"
  description: "A test application"

entry:
  mxml: "src/Main.mxml"

targets:
  web:
    enabled: true
    output: "dist/web"
    config:
      title: "Example App"
      favicon: "assets/favicon.ico"

  mobile:
    enabled: false

build:
  mode: "development"
  source_maps: true
"""

    # Write to temp file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(example_yaml)
        temp_file = f.name

    try:
        config = parser.parse(temp_file)
        print(f"Parsed config: {config.name} v{config.version}")
        print(f"Enabled targets: {[t.platform.value for t in config.targets if t.enabled]}")
    finally:
        import os
        os.unlink(temp_file)
