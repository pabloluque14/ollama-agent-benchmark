# Claude Code

@AGENTS.md
@CONTEXT.md

## Project decisions

Antes de proponer o modificar código:

- consulta los ADR aceptados de `docs/adr/`;
- utiliza como especificación activa `docs/specs/ollama-agent-benchmark-0.3.0.md`;
- respeta el alcance de Ollama Agent Benchmark 0.3.0;
- no amplíes el dataset, los scorers ni las métricas fuera de la especificación;
- trata el plan y los registros primarios como evidencia canónica;
- conserva `dependencies = []` en runtime.

## Multi-agent workflow

- Codex es el escritor principal.
- Claude Code actúa inicialmente como revisor independiente.
- No modifiques archivos durante tareas de revisión salvo autorización expresa.
- No ejecutes simultáneamente cambios sobre los mismos archivos que otro agente.
- Informa de contradicciones entre AGENTS.md, CONTEXT.md, ADR y la especificación.
