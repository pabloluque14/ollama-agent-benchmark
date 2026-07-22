# Guía para agentes de desarrollo

## Propósito y arquitectura

Este repositorio compara modelos locales servidos por Ollama como candidatos a agentes. La CLI
`oab` coordina configuración y lock, runner funcional con herramientas virtuales, runner de
rendimiento y generador de informes. `common.py` contiene la infraestructura compartida; los
datasets versionados son parte del protocolo experimental.

## Seguridad obligatoria

- Las pruebas y CI nunca llaman a una instalación real de Ollama, Internet ni modelos reales.
- Las integrales usan exclusivamente `tests/fake_ollama.py` y una URL localhost efímera.
- Nunca se ofrece shell, archivos reales ni credenciales a un modelo.
- No se versionan locks locales, runs, informes privados ni pesos.

## Desarrollo

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
oab validate
ruff check .
mypy
coverage run -m unittest discover -s tests
coverage report
```

## Git y definición de terminado

Trabaja en una rama `codex/*`, conserva el árbol del usuario, no reescribas historial y no hagas
push sin petición expresa. Todo cambio de evaluación, scoring, schema o seguridad necesita pruebas.
Un cambio termina cuando tests, validación, Ruff, Mypy y cobertura pasan; los formatos están
versionados; la documentación española refleja el comportamiento; y ninguna prueba depende de
Ollama real.

## Agent skills

### Issue tracker

Issues and specs are tracked as local Markdown under `.scratch/<feature>/`. See
`docs/agents/issue-tracker.md`.

### Domain docs

This repository uses a single-context domain documentation layout. See `docs/agents/domain.md`.
