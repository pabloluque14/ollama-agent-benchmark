# Arquitectura

## Componentes

### CLI `oab`

Enruta los subcomandos:

```text
init → lock → validate → preflight → functional → performance → report
```

### Configuración

- `config/benchmark.json`: modelos, parámetros, repeticiones y pesos.
- `config/models.lock.json`: identidad exacta local; se genera y no se versiona por defecto.

### Dataset

- `benchmark_cases_v1.json`: 60 casos y reglas de evaluación.
- `fixtures_v1.json`: archivos y documentos virtuales.
- `tools_v1.json`: esquemas JSON de las seis herramientas.
- `performance_workloads_v1.json`: cargas sintéticas de rendimiento.

### Runner funcional

Conserva la conversación completa. Cuando el modelo solicita una herramienta:

1. valida nombre y argumentos;
2. ejecuta la herramienta virtual;
3. añade un mensaje `tool`;
4. vuelve a llamar al modelo;
5. evalúa la secuencia y la respuesta final.

### Runner de rendimiento

Separa:

- carga fría;
- ejecuciones calientes;
- streaming de TTFT;
- snapshots de `/api/ps`, swap y sistema.

### Informe

Combina los dos runs y genera JSON, CSV, Markdown y SVG sin dependencias externas.

## Formatos

- JSON para manifests y resúmenes.
- JSONL para eventos y ejecuciones completas.
- CSV para análisis tabular.
- Markdown para lectura humana.
- SVG para gráficas portables.
