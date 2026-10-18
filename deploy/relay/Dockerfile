# quantum relay: where two browsers meet to play a networked game.
#
#   docker build -f deploy/relay/Dockerfile -t quantum-relay .
#   docker run -p 8080:8080 quantum-relay
#
# The image holds the games of projects/ with qg:multiplayer, compiled once
# at build time, and Godot to run each room headless. It listens on plain
# ws:// on port 8080; the host in front of it (Fly.io, Render, a reverse
# proxy) gives it HTTPS, so the players join wss://<host>/<game>/<room>.
# A GET without a WebSocket upgrade answers the relay's health as JSON.
FROM python:3.12-slim

# Godot headless reports an error at every start without fontconfig
RUN apt-get update \
 && apt-get install -y --no-install-recommends fontconfig \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY quantum ./quantum
COPY scripts/godot.py ./scripts/godot.py
COPY projects ./projects
COPY assets ./assets
RUN pip install --no-cache-dir -e ".[websocket]" \
 && python scripts/godot.py install \
 && quantum relay --builds /app/builds --prebuild-only

EXPOSE 8080
CMD ["quantum", "relay", "--bind", "0.0.0.0", "--port", "8080", "--builds", "/app/builds"]
