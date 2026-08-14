#!/usr/bin/env bash
# Bootstrap a local dev environment: venv + dependencies + .env.
set -euo pipefail

PYTHON="${PYTHON:-python3}"
VENV=".venv"

if [ ! -d "${VENV}" ]; then
  echo ">> Creating virtualenv at ${VENV}"
  "${PYTHON}" -m venv "${VENV}"
fi

# shellcheck disable=SC1091
source "${VENV}/bin/activate"

echo ">> Installing dev dependencies"
pip install --upgrade pip
pip install -r requirements/dev.txt

if [ ! -f .env ]; then
  echo ">> Copying .env.example -> .env (edit it with real secrets)"
  cp .env.example .env
fi

echo ">> Done. Activate with: source ${VENV}/bin/activate"
