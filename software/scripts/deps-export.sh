#!/usr/bin/env bash
# Regenerate each software package's src/requirements.txt from its dependency group in
# pyproject.toml (the single source of truth). One definition, shared by `pnpm deps:export`
# and the requirements-sync CI job.
#
# --no-deps: top-level pins only. The runenv supplies transitive deps for the offline
# (--no-index) install, so requirements.txt must not pin a full closure.
# The dependency-group name matches the package directory.
set -euo pipefail
cd "$(dirname "$0")/.."
for pkg in vbc-filtering vbc-normalization hash-column; do
  uv pip compile --group "$pkg" --no-deps --no-annotate \
    --custom-compile-command "pnpm deps:export" -o "$pkg/src/requirements.txt"
done
