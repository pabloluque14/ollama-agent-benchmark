#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--confirm-run" ]]; then
  cat >&2 <<'EOF'
Este script ejecuta el benchmark funcional y de rendimiento completo.
Puede tardar bastante y cargar repetidamente todos los modelos.

Uso:
  scripts/run_official.sh --confirm-run
EOF
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -x .venv/bin/oab ]]; then
  echo "ERROR: ejecuta primero scripts/bootstrap_macos.sh" >&2
  exit 3
fi

source .venv/bin/activate
oab preflight --require-ac

STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
FUNCTIONAL_RUN="functional_$STAMP"
PERFORMANCE_RUN="performance_$STAMP"

oab functional --mode official-functional --run-id "$FUNCTIONAL_RUN"
oab performance --mode official-performance --run-id "$PERFORMANCE_RUN"
oab report \
  --functional-run "runs/$FUNCTIONAL_RUN" \
  --performance-run "runs/$PERFORMANCE_RUN"

echo
printf 'Run funcional: %s\n' "$FUNCTIONAL_RUN"
printf 'Run rendimiento: %s\n' "$PERFORMANCE_RUN"
