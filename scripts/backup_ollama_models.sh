#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT/ollama-model-backups}"
INCLUDE_WEIGHTS="false"
CONFIRMED="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --include-weights) INCLUDE_WEIGHTS="true"; shift ;;
    --confirm-large-backup) CONFIRMED="true"; shift ;;
    --output-dir) OUTPUT_DIR="${2:-}"; shift 2 ;;
    -h|--help)
      cat <<'EOF'
Uso:
  scripts/backup_ollama_models.sh [--output-dir RUTA]
  scripts/backup_ollama_models.sh --include-weights --confirm-large-backup [--output-dir RUTA]

Sin --include-weights solo guarda metadatos y digests.
Con pesos puede ocupar decenas o cientos de GB. No subas ese archivo a GitHub.
EOF
      exit 0
      ;;
    *) echo "Argumento desconocido: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$OUTPUT_DIR"
STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
META="$OUTPUT_DIR/ollama_metadata_$STAMP"
mkdir -p "$META"

ollama --version > "$META/ollama_version.txt"
ollama list > "$META/ollama_list.txt"
curl --fail --silent --show-error http://127.0.0.1:11434/api/tags > "$META/api_tags.json"
[[ -f "$ROOT/config/models.lock.json" ]] && cp "$ROOT/config/models.lock.json" "$META/"
shasum -a 256 "$META"/* > "$META/SHA256SUMS.txt"

echo "Metadatos guardados en: $META"

if [[ "$INCLUDE_WEIGHTS" == "true" ]]; then
  if [[ "$CONFIRMED" != "true" ]]; then
    echo "ERROR: para copiar pesos añade --confirm-large-backup." >&2
    exit 3
  fi
  MODEL_DIR="${OLLAMA_MODELS:-$HOME/.ollama/models}"
  if [[ ! -d "$MODEL_DIR" ]]; then
    echo "ERROR: no existe $MODEL_DIR" >&2
    exit 4
  fi
  ARCHIVE="$OUTPUT_DIR/ollama-models_$STAMP.tar.gz"
  echo "Creando copia grande desde $MODEL_DIR ..."
  tar -czf "$ARCHIVE" -C "$(dirname "$MODEL_DIR")" "$(basename "$MODEL_DIR")"
  shasum -a 256 "$ARCHIVE" > "$ARCHIVE.sha256"
  echo "Pesos guardados en: $ARCHIVE"
fi
