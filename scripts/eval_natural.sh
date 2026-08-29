#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

if [[ -f ".env" ]]; then
  set -a
  source ".env"
  set +a
fi

: "${PRI_API_KEY:?Set PRI_API_KEY or create a local .env file from .env.example.}"
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

python src/draw.py --task natural --model gpt-image-1
python src/tasks/natural/eval.py --model gpt-image-1
