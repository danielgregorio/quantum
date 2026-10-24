# The beta's reports

Where the games' beta reports land (`PLAN_PANDAFOOT.md`, "The beta's reports"). A player reports a bug or a
suggestion from inside the game; the game posts it to `/api/reports`; this application, written in Quantum
(`components/api/reports.q`, a `q:endpoint`), keeps it in SQLite and tells the forge:

- the report as an **issue** of the repository, labelled `beta-report`, the game and the kind;
- the **save** the player attached as a file of the repository's branch `beta-reports`
  (`beta-reports/<game>/<number>.json`), since an issue holds 64 KB and a save more.

Which forge, repository and branch is a row of the `settings` table (`danielgregorio/pandafoot` on GitHub, by
the migration). If the forge cannot be reached, the report is kept all the same and its `issue` stays empty.

## On the homelab

1. **A token.** On GitHub, Settings → Developer settings → Fine-grained tokens → Generate new token: the
   repository `danielgregorio/pandafoot` alone, with **Issues: read and write** and **Contents: read and
   write**. It is read from the environment when a report is told (SPEC.md INV-3); it is never in a file of
   this repository.
2. **The branch** `beta-reports` in that repository (it exists already: the agent made it).
3. **HTTPS, by a Cloudflare Tunnel.** A game in a browser posts only to HTTPS. The tunnel's `cloudflared`
   dials out to Cloudflare, so the homelab opens no port and its router forwards nothing:

   1. **The domain on Cloudflare** (the free plan). If `quantumframework.net`'s DNS is elsewhere: Cloudflare →
      Add a domain, then its two nameservers at the registrar. Before switching, check that Cloudflare imported
      every record the site has now (GitHub Pages': the `A` records of the domain and the `CNAME` of `www`), and
      leave them **DNS only** (the grey cloud), so GitHub Pages keeps the site's certificate.
   2. **The tunnel.** Cloudflare → Zero Trust → Networks → Tunnels → Create a tunnel → Cloudflared, named
      `beta-reports`. Copy its token, the `eyJ...` after `--token` in the command it shows; that command is
      not needed, the container below runs it.
   3. **Its public hostname**: subdomain `reports`, domain `quantumframework.net`, service **HTTP**
      `beta-reports:8095` (the receiver's name on the stack's network).

   Cloudflare is the one proxy in front (`server.proxies: 1`): it passes each player's address, so each is
   counted by the limit (20 reports an hour).
4. **The containers**, on the homelab, from the repository's root:

   ```bash
   GITHUB_TOKEN=github_pat_... QUANTUM_SECRET_KEY=$(openssl rand -hex 32) CLOUDFLARE_TUNNEL_TOKEN=eyJ... \
     docker compose -f projects/beta-reports/compose.yaml -f projects/beta-reports/compose.tunnel.yaml \
     up -d --build
   ```

   The receiver also listens on `127.0.0.1:8095`, to try it on the homelab itself; the database is
   `projects/beta-reports/data/reports.db`. The tokens are the environment's: an `.env` file beside the
   compose files, readable by its owner alone (`chmod 600`), keeps them for the next `up`, and is never
   committed (`.gitignore`). Without the tunnel (another reverse proxy of yours in front, with HTTPS),
   `compose.yaml` alone.
5. **Try it** from anywhere:

   ```bash
   curl -X POST https://reports.quantumframework.net/api/reports -H 'Content-Type: application/json' \
     -d '{"game": "pandafoot", "version": "2.1", "kind": "other", "text": "Hello from the homelab"}'
   ```

   It answers `{"number": 1}`, and an issue appears in the repository.
6. **The game's address**: tell the agent `https://reports.quantumframework.net`; it goes into the game
   (`report_server()` in `projects/pandafoot/pandafoot.q`).

## What it accepts

`POST /api/reports`, a JSON object:

| Field | | |
|---|---|---|
| `game` | required | lowercase letters, digits and `-` |
| `version` | required | up to 20 characters |
| `kind` | required | `bug`, `suggestion` or `other` |
| `text` | required | 3 to 4000 characters |
| `screen`, `option`, `context`, `player` | optional | where the game was, the option the cursor was on, who |
| `save` | optional | the game's save, as text (up to 3.5 MB) |

From a browser, only the games' site (`https://quantumframework.net`) may post; a game on the desktop sends no
`Origin` and is never refused for it. One address posts at most 20 reports an hour. Tested by
`tests/apps/test_beta_reports.py`, against a forge of the test.
