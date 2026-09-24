# Serving Quantum in production

> `PRODUCTION_READINESS.md` Phase 5. Short on purpose: there are four things, and
> each one exists because its absence caused a real problem measured in this
> audit.

---

## 1. `quantum start` is not a production server

It runs Flask's **development** server: one process, no hardening, and since
this session's fix bound to `127.0.0.1` by default. Use it while you write the
app, not to serve it.

The production path is a real WSGI server:

```bash
pip install gunicorn                      # not bundled; it is your choice
gunicorn 'quantum.runtime.web_server:create_app()' \
    --bind 0.0.0.0:8080 \
    --workers 4
```

> The `create_app` docstring said `gunicorn 'src.runtime.web_server:...'`
> — the layout that stopped existing when `src/` became the `quantum/` package.
> The only documented production entry point **did not import**. Fixed.

On Windows, `gunicorn` does not run; use `waitress`:

```bash
pip install waitress
waitress-serve --listen=0.0.0.0:8080 --call quantum.runtime.web_server:create_app
```

## 2. Set the session key, or users get logged out at random

Without `QUANTUM_SECRET_KEY` (or `security.secret_key` in the config), **each worker
generates its own random key on import**. A cookie signed by one worker is
rejected by the next, and the user is logged out with no apparent pattern — the
kind of bug people chase for days.

```bash
export QUANTUM_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
```

`create_app()` warns in the log when neither of the two is set.

## 3. What to leave in `quantum.config.yaml`

```yaml
server:
  host: 0.0.0.0     # behind gunicorn/container; the real bind is gunicorn's
  debug: false      # ALWAYS. Werkzeug's debugger is an eval console.
  reload: false     # reload is for development

security:
  python_scripting: false   # it is the DEFAULT; only turn it on if the app uses q:python
```

The server **refuses** to run the debugger outside loopback even if the config
asks for it, because that would be remote code execution for anyone who reaches
the port. But do not count on that safety net: leave `debug: false`.

An invalid config now **fails at boot** instead of silently falling back to defaults
— before, a broken YAML discarded your datasources, host and security and
served with the defaults, with a single warning as notice.

## 4. If you serve Quantum Admin

It is a separate application, with its own rules. In production:

```bash
export QUANTUM_ADMIN_ENV=production            # refuses to start misconfigured
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export ADMIN_PASSWORD="<a real password>"
export QUANTUM_ADMIN_CORS_ORIGINS="https://admin.your-domain"
```

Without `QUANTUM_ADMIN_ENV=production` the admin **starts anyway**, with a
random key and password per process (the password is printed at boot). That is
good for development and bad for serving: each worker signs with a different
key, so users get logged out. In production, set both.

Before this session the key and the password had defaults published in this
repository — you could forge an admin token without ever seeing the login
screen. If you have an old installation, generate new values.

`GITHUB_WEBHOOK_SECRET` / `GITLAB_WEBHOOK_TOKEN` are required if you use
the webhooks: without them the routes **refuse** every call (before they accepted
any, and an unsigned push triggers a deploy).

## 5. Messaging

The default broker is **sqlite**: durable, serverless, one file
(`quantum_messages.db` by default, next to `quantum_jobs.db`).

```bash
export QUANTUM_MQ_PATH=/var/lib/quantum/messages.db   # optional
```

It used to be `memory`, which lives inside one interpreter: under gunicorn with
four workers, four private queues, and everything enqueued dies on restart.
Silent data loss as the default.

Where sqlite is bad, so you can decide with information: consumers *poll*
(there is latency), there is no cluster, and sqlite accepts one writer at a
time — under heavy write concurrency it chokes. Then it is `MESSAGE_BROKER_TYPE`
with `redis` or `rabbitmq`. `memory` remains available and legitimate for a
single-process app that wants no file at all.

## 6. Health check

`GET /health` responds 200. Use it as the container's readiness probe.

```bash
curl -fsS http://localhost:8080/health || exit 1
```

---

## Checklist before exposing it

- [ ] `gunicorn`/`waitress` in front, not `quantum start`
- [ ] `QUANTUM_SECRET_KEY` set and stable across workers
- [ ] `server.debug: false`
- [ ] `security.python_scripting` **off** — it is the default now; if your
      app turns it on, confirm that every `.q` it executes was written by
      you. Without a sandbox, it is arbitrary Python in the process (`SECURITY.md`)
- [ ] `paths.uploads` pointing at a dedicated directory; `q:file` is
      confined to it
- [ ] Secrets via environment variables, never in the versioned YAML
- [ ] `/health` wired to the orchestrator
- [ ] Read `PRODUCTION_READINESS.md` — there are known open criticals, and
      exposing this publicly today would be premature

## What does not exist yet

Being direct, because a deploy document that leaves this out is worse than none:

- **There is no official Docker image or manifest** — the recipe above is what there is.
- **`q:websocket` needs an extra**: the transport is the `websockets`
  library (`pip install quantum[websocket]`). Without it the tag records the
  connection and **opens nothing** — and says so in the log and in the result's
  `transport`, instead of pretending. It is a client: `url=` points to another
  server; Quantum does not *serve* websockets.
- **Metrics and tracing** do not exist beyond the log.
