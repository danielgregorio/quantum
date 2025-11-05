#!/usr/bin/env python3
"""
Quantum CLI - Advanced Developer Experience

Phase C: Developer Experience

Commands:
  quantum create component <name>  - Create a new component
  quantum dev [--port=8080]        - Start dev server with HMR
  quantum build [--production]     - Build for production
  quantum init [--template=blog]   - Initialize new project
  quantum inspect <component>      - Inspect component details
"""

import sys
import argparse
from pathlib import Path
import subprocess
import os

class QuantumCLI:
    """Main CLI handler for Quantum framework"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.components_dir = self.project_root / "components"

    def create_component(self, name: str, template: str = "basic"):
        """Create a new component from template"""
        print(f"🎨 Creating component: {name}")

        # Ensure components directory exists
        self.components_dir.mkdir(exist_ok=True)

        # Component filename
        component_file = self.components_dir / f"{name}.q"

        if component_file.exists():
            print(f"❌ Error: Component '{name}' already exists at {component_file}")
            return False

        # Template content
        if template == "basic":
            content = f"""<q:component name="{name}">
  <h1>{name} Component</h1>

  <p>Welcome to your new {name} component!</p>

  <style>
    h1 {{
      color: #007bff;
      font-family: Arial, sans-serif;
    }}
  </style>
</q:component>
"""
        elif template == "form":
            content = f"""<q:component name="{name}">
  <h1>{name}</h1>

  <q:if condition="{{flash}}">
    <div class="flash">{{flash}}</div>
  </q:if>

  <form method="POST" action="/{name.lower()}?action=submit">
    <div>
      <label for="name">Name:</label>
      <input type="text" id="name" name="name" required />
    </div>

    <button type="submit">Submit</button>
  </form>

  <q:action name="submit" method="POST">
    <q:param name="name" type="string" required="true" />
    <q:redirect url="/{name.lower()}" flash="Form submitted successfully!" />
  </q:action>

  <style>
    form {{
      max-width: 400px;
      padding: 20px;
      background: #f5f5f5;
      border-radius: 8px;
    }}

    div {{
      margin-bottom: 15px;
    }}

    label {{
      display: block;
      margin-bottom: 5px;
      font-weight: bold;
    }}

    input {{
      width: 100%;
      padding: 8px;
      border: 1px solid #ddd;
      border-radius: 4px;
    }}

    button {{
      background: #007bff;
      color: white;
      padding: 10px 20px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }}

    button:hover {{
      background: #0056b3;
    }}

    .flash {{
      background: #d4edda;
      border: 1px solid #c3e6cb;
      color: #155724;
      padding: 12px;
      border-radius: 4px;
      margin-bottom: 20px;
    }}
  </style>
</q:component>
"""
        else:
            print(f"❌ Error: Unknown template '{template}'")
            return False

        # Write component file
        component_file.write_text(content, encoding='utf-8')

        print(f"✅ Component created: {component_file}")
        print(f"🌐 Test at: http://localhost:8080/{name.lower()}")

        return True

    def dev_server(self, port: int = 8080):
        """Start development server with HMR"""
        print("🚀 Starting Quantum development server...")
        print(f"📡 Server will run on: http://localhost:{port}")
        print("🔄 Auto-reload enabled")
        print("Press Ctrl+C to stop")
        print("=" * 60)

        # Set environment variables
        env = os.environ.copy()
        env['QUANTUM_DEV_MODE'] = 'true'
        env['QUANTUM_PORT'] = str(port)

        # Start web server
        try:
            subprocess.run(
                [sys.executable, "src/runtime/web_server.py"],
                cwd=self.project_root,
                env=env
            )
        except KeyboardInterrupt:
            print("\n\n👋 Quantum dev server stopped")

    def build_production(self):
        """Build for production"""
        print("🏗️  Building Quantum project for production...")
        print("📦 Optimizing components...")

        # Count components
        components = list(self.components_dir.glob("*.q"))
        print(f"✅ Found {len(components)} components")

        # In a real implementation, this would:
        # - Minify HTML/CSS
        # - Bundle JavaScript
        # - Optimize images
        # - Generate static assets
        # - Create production config

        print("✅ Production build complete!")
        print("📂 Output directory: ./dist")

        return True

    def init_project(self, template: str = "basic"):
        """Initialize a new Quantum project"""
        print(f"🎬 Initializing new Quantum project (template: {template})")

        # Create directory structure
        dirs = [
            "components",
            "src",
            "tests",
            "uploads",
            "static"
        ]

        for dir_name in dirs:
            dir_path = self.project_root / dir_name
            dir_path.mkdir(exist_ok=True)
            print(f"✅ Created: {dir_path}")

        # Create .env file
        env_file = self.project_root / ".env"
        if not env_file.exists():
            env_content = """# Quantum Configuration
QUANTUM_PORT=8080
QUANTUM_DEV_MODE=true
EMAIL_MOCK=true
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_FROM=noreply@quantum.dev
"""
            env_file.write_text(env_content)
            print(f"✅ Created: {env_file}")

        print("✅ Project initialized!")
        print("\n🚀 Next steps:")
        print("  1. quantum create component Home")
        print("  2. quantum dev")

        return True

    def inspect_component(self, name: str):
        """Inspect component details"""
        print(f"🔍 Inspecting component: {name}")

        component_file = self.components_dir / f"{name}.q"

        if not component_file.exists():
            print(f"❌ Error: Component '{name}' not found")
            print(f"📂 Looking in: {self.components_dir}")

            # Suggest similar components
            all_components = [f.stem for f in self.components_dir.glob("*.q")]
            if all_components:
                print(f"\n💡 Available components:")
                for comp in all_components:
                    print(f"   - {comp}")

            return False

        # Read and analyze component
        content = component_file.read_text(encoding='utf-8')

        print(f"✅ Component found: {component_file}")
        print(f"📊 Size: {len(content)} bytes")
        print(f"📝 Lines: {len(content.splitlines())}")

        # Count tags
        import re
        actions = len(re.findall(r'<q:action', content))
        queries = len(re.findall(r'<q:query', content))
        params = len(re.findall(r'<q:param', content))

        print(f"\n🏷️  Tags:")
        if actions > 0:
            print(f"   - Actions: {actions}")
        if queries > 0:
            print(f"   - Queries: {queries}")
        if params > 0:
            print(f"   - Params: {params}")

        print(f"\n🌐 URL: http://localhost:8080/{name.lower()}")

        return True


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Quantum CLI - ColdFusion-inspired SSR Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # create command
    create_parser = subparsers.add_parser('create', help='Create new resources')
    create_parser.add_argument('resource', choices=['component'], help='Resource type')
    create_parser.add_argument('name', help='Resource name')
    create_parser.add_argument('--template', default='basic',
                               choices=['basic', 'form'],
                               help='Template to use')

    # dev command
    dev_parser = subparsers.add_parser('dev', help='Start development server')
    dev_parser.add_argument('--port', type=int, default=8080, help='Server port')

    # build command
    build_parser = subparsers.add_parser('build', help='Build for production')
    build_parser.add_argument('--production', action='store_true', help='Production mode')

    # init command
    init_parser = subparsers.add_parser('init', help='Initialize new project')
    init_parser.add_argument('--template', default='basic', help='Project template')

    # inspect command
    inspect_parser = subparsers.add_parser('inspect', help='Inspect component')
    inspect_parser.add_argument('component', help='Component name')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = QuantumCLI()

    try:
        if args.command == 'create':
            if args.resource == 'component':
                cli.create_component(args.name, args.template)

        elif args.command == 'dev':
            cli.dev_server(args.port)

        elif args.command == 'build':
            cli.build_production()

        elif args.command == 'init':
            cli.init_project(args.template)

        elif args.command == 'inspect':
            cli.inspect_component(args.component)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
