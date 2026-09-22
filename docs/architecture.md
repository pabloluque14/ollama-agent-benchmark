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

- `benchmark_cases_v2.json`: 60 casos y matchers deterministas auditables.
- `fixtures_v2.json`: archivos y documentos virtuales.
- `tools_v2.json`: esquemas JSON de las seis herramientas.
- `performance_workloads_v2.json`: cargas y reglas de cumplimiento.

### Runner funcional

Ambos runners escriben un `plan.json` v3 validado antes de consultar
Ollama. Guarda los inputs bloqueados por hash, identidades, opciones, valores efectivos y el
calendario de claves. El calendario usa seed e identidades bloqueadas, equilibra por caso o
workload/tipo y se vuelve a validar antes de la ejecución. El preflight contrasta versión y digests
contra el plan original, no contra una configuración posterior. La publicación es atómica y excluye
sobrescrituras. `dry-run` no persiste ese plan ni registros.

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

Combina los dos runs desde planes y registros canónicos v3 y genera JSON, CSV, Markdown y SVG sin
dependencias externas. Rechaza corrupción o incompatibilidad antes de crear salida. Los pesos,
métricas y políticas proceden del plan guardado, no de la configuración presente al informar.

### Infraestructura común y pruebas

`common.py` centraliza JSON/JSONL atómico, HTTP, URL, plataforma, alimentación, snapshots,
descarga, métricas, lock, timestamps y hashes. `tests/fake_ollama.py` implementa los endpoints
necesarios mediante la biblioteca estándar; CI nunca utiliza Ollama real.

En `0.3.0`, cada registro primario pasa por su contrato v3 antes del append. El lector JSONL valida
el artefacto completo y falla ante UTF-8 inválido, línea vacía, truncamiento, JSON malformado o raíz
que no sea objeto. El diario de integridad usa el mismo almacenamiento durable y una clasificación
conservadora: ante atribución incierta, el fallo pertenece al benchmark y no al modelo.

## Formatos

- JSON para planes, contratos, resúmenes e informes.
- JSONL para registros primarios y diario de integridad.
- CSV para análisis tabular.
- Markdown para lectura humana.
- SVG para gráficas portables.
