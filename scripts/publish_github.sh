#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Uso:
  scripts/publish_github.sh --repo NOMBRE [--public|--private] --confirm-publish

El modo predeterminado es privado. El script no publica nada sin
--confirm-publish. Requiere GitHub CLI autenticada: gh auth status.
EOF
}

REPO=""
VISIBILITY="private"
CONFIRMED="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="${2:-}"; shift 2 ;;
    --public) VISIBILITY="public"; shift ;;
    --private) VISIBILITY="private"; shift ;;
    --confirm-publish) CONFIRMED="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Argumento desconocido: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$REPO" ]]; then
  echo "ERROR: falta --repo." >&2
  exit 2
fi
if [[ "$CONFIRMED" != "true" ]]; then
  echo "ERROR: falta --confirm-publish. No se ha publicado nada." >&2
  exit 3
fi
if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: instala GitHub CLI (gh)." >&2
  exit 4
fi
gh auth status

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .git ]]; then
  git init
  git branch -M main
fi

if [[ -n "$(git status --porcelain)" ]]; then
  git add README.md pyproject.toml .gitignore .editorconfig Makefile config datasets docs examples scripts src tests .github
  git commit -m "Initial portable Ollama agent benchmark"
fi

if git remote get-url origin >/dev/null 2>&1; then
  echo "ERROR: ya existe un remoto origin. Revísalo manualmente antes de publicar." >&2
  exit 5
fi

gh repo create "$REPO" --"$VISIBILITY" --source=. --remote=origin --push

echo "Repositorio publicado como $VISIBILITY: $REPO"
