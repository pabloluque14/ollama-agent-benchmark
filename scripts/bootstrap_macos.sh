#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 no está disponible." >&2
  exit 1
fi

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .

if [[ ! -f config/benchmark.json ]]; then
  cp config/benchmark.example.json config/benchmark.json
  echo "Creado config/benchmark.json desde el ejemplo."
fi

cat <<'EOF'

Instalación terminada.

Siguientes pasos:
  1. Edita config/benchmark.json y cambia la lista "models".
  2. Comprueba que Ollama está abierto y que los modelos aparecen en: ollama list
  3. Ejecuta: source .venv/bin/activate
  4. Ejecuta: oab lock
  5. Ejecuta: oab preflight
  6. Ejecuta: oab functional --mode smoke --allow-battery
EOF
