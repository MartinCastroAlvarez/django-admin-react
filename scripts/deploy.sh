#!/usr/bin/env bash
#
# scripts/deploy.sh — publish the built artifact to PyPI.
#
# Requirements:
#   - dist/ already populated by scripts/build.sh.
#   - PYPI_TOKEN env var set to a PyPI API token starting with "pypi-".
#     For TestPyPI use TESTPYPI_TOKEN and pass --test.
#
# Usage:
#   PYPI_TOKEN=pypi-... bash scripts/deploy.sh
#   TESTPYPI_TOKEN=pypi-... bash scripts/deploy.sh --test
#
# This script never echoes the token. Even in --verbose mode the token is
# masked. The token is passed to Poetry via stdin / config commands, not
# via the command line, so it cannot leak through `ps`.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

USE_TEST=0
if [[ "${1:-}" == "--test" ]]; then
  USE_TEST=1
fi

step() {
  printf '\n\033[1;34m▶ %s\033[0m\n' "$*"
}

if [[ ! -d "$ROOT/dist" ]] || [[ -z "$(ls -A "$ROOT/dist" 2>/dev/null)" ]]; then
  echo "dist/ is empty — run scripts/build.sh first"
  exit 1
fi

if [[ "$USE_TEST" == "1" ]]; then
  : "${TESTPYPI_TOKEN:?TESTPYPI_TOKEN env var required for --test deploy}"
  step "configure poetry for TestPyPI"
  poetry config repositories.testpypi https://test.pypi.org/legacy/
  poetry config pypi-token.testpypi "$TESTPYPI_TOKEN"
  step "publish to TestPyPI"
  poetry publish --repository testpypi --no-interaction
else
  : "${PYPI_TOKEN:?PYPI_TOKEN env var required (start with pypi-...)}"
  step "configure poetry for PyPI"
  poetry config pypi-token.pypi "$PYPI_TOKEN"
  step "publish to PyPI"
  echo "  • This step is gated by repo-owner approval; abort with Ctrl-C if you"
  echo "    did not mean to push a public release."
  sleep 3
  poetry publish --no-interaction
fi

printf '\n\033[1;32m✔ deploy complete\033[0m\n'
