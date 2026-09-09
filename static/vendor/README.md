# Vendored third-party assets

Served from `/static/vendor/`. They live here so a Quantum app works
offline, behind a firewall, or on an air-gapped host — the framework
used to inject a CDN `<script>` into every page, and a CDN that was
slow, blocked or offline meant the page's htmx never loaded.

`quantum/runtime/web_server.py::_htmx_url` prefers this copy and falls
back to the CDN only when it is missing.

## htmx.min.js

- Version: 1.9.10
- Source: https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js
- sha256: b3bdcf5c741897a53648b1207fff0469a0d61901429ba1f6e88f98ebd84e669e
- Licence: BSD 2-Clause (see LICENSE-htmx.txt)

To update: fetch the new version, replace the file, and update the
version and digest above.
