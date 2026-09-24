# Quantum Admin

The admin is a Quantum application that manages the applications in a folder:
it lists and creates them, starts and stops their servers, edits their
configuration and connectors, browses their components and runs their tests.
Its screens are `.q` files over [declared services](/guide/services).

## Install and start

```bash
pip install "quantum-framework[admin]"
cd my-workspace
quantum admin
```

Open `http://127.0.0.1:8090/admin` and sign in as `admin`. Without
`ADMIN_PASSWORD`, a password is generated and printed when the admin starts;
it changes on every restart. Set it to keep a stable login:

```bash
ADMIN_PASSWORD="a long password" quantum admin
```

The admin listens on `127.0.0.1` only.

## Where the data goes

| Option | Default | What it is |
|--------|---------|------------|
| `--data` | `./.quantum-admin` | The admin database, its settings (connectors, global settings, process PIDs), the session keys and the generated `quantum.config.yaml` |
| `--root` | the current folder | The folder application paths are relative to; **Sync** registers each folder under `<root>/projects` |
| `--port` | `8090` | |

The generated config is rewritten on every start; change the options, not the
file. Keep the data folder out of version control: it holds secrets.

Without the `[admin]` extra the command stops and says what to install.
