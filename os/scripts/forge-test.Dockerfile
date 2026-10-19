# Built and run on the Forge homelab host (10.10.1.40) by
# scripts/test-on-forge.sh — gives a native Linux toolchain for
# fmt/clippy/test without needing WSL or fighting Windows cross-compile.
FROM rust:1-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends pkg-config libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && rustup component add rustfmt clippy

WORKDIR /app
