#!/usr/bin/env sh
set -eu

: "${YAML_FILENAME:?missing YAML_FILENAME}"
: "${PROJECT_ID:?missing PROJECT_ID}"

PYTHON_BIN="/home/guv/AI_Scientist/.venv/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "missing python venv at $PYTHON_BIN (mount /home/guv/AI_Scientist/.venv into container)" >&2
  exit 2
fi

cd /home/guv/AI_Scientist

exec "$PYTHON_BIN" -m stages.manual_proposal -p "./initial_configs/${YAML_FILENAME}" -i "${PROJECT_ID}"

