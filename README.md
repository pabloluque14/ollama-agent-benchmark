# Ollama Agent Benchmark

Benchmark local, reproducible y auditable para comparar modelos servidos por **Ollama** antes de utilizarlos como agentes con acceso a herramientas.

El proyecto está pensado especialmente para Apple Silicon, pero la parte funcional y la API de Ollama también pueden ejecutarse en Linux. Las comprobaciones de batería, estado térmico y swap son específicas de macOS y se omiten cuando no están disponibles.

> Estado: **alpha formativa**. Las herramientas del benchmark son simuladas; ningún modelo recibe acceso real a la shell ni a tus archivos.

## Qué problema resuelve

Comparar modelos solo por tokens por segundo es insuficiente para elegir un agente. Un modelo rápido puede:

- llamar a la herramienta incorrecta;
- producir JSON inválido;
- ignorar resultados;
- repetir una llamada que ya falló;
- escribir sin confirmación;
- obedecer instrucciones maliciosas encontradas dentro de un archivo.

Este benchmark mide cuatro áreas y calcula una puntuación configurable:

| Área | Peso inicial | Qué evalúa |
|---|---:|---|
| Fiabilidad de herramientas | 40 % | Selección, argumentos, orden, recuperación, confirmaciones e inyección |
| Calidad y razonamiento | 25 % | Instrucciones, datos, síntesis, depuración e información insuficiente |
| Velocidad | 20 % | Carga, prompt tok/s, generation tok/s, latencia y TTFT |
| Memoria y estabilidad | 15 % | Memoria declarada por `/api/ps`, swap y errores del runner |

Los pesos se cambian en `config/benchmark.json`.

## Seguridad

- Las herramientas se ejecutan **en memoria** sobre archivos y documentación virtuales.
- No se utiliza `shell=True`, `sudo` ni una terminal real durante el benchmark funcional.
- Las operaciones de escritura simulada requieren confirmación en los casos que corresponden.
- Los resultados de archivos, búsquedas y errores se marcan como contenido no confiable.
- Ollama debe permanecer en `127.0.0.1` salvo decisión explícita del usuario.
- Los runs oficiales exigen corriente en macOS; con `--allow-battery` quedan marcados como exploratorios.

Consulta [docs/security.md](docs/security.md).

## Requisitos

- Python 3.11 o superior.
- Ollama instalado y ejecutándose.
- Modelos ya descargados mediante Ollama.
- macOS o Linux. Apple Silicon es el entorno principal de desarrollo.
- Espacio suficiente para modelos, resultados y, si se desea, copias de seguridad de pesos.

El proyecto utiliza únicamente la biblioteca estándar de Python.

## Inicio rápido

```bash
git clone <URL-DEL-REPOSITORIO>
cd ollama-agent-benchmark

./scripts/bootstrap_macos.sh
source .venv/bin/activate
```

Edita la lista de modelos:

```bash
nano config/benchmark.json
```

Ejemplo:

```json
{
  "models": [
    "gemma4:12b-mlx",
    "gemma4:12b-it-qat",
    "qwen3.5:9b-mlx"
  ]
}
```

Los nombres deben coincidir exactamente con:

```bash
ollama list
```

Después:

```bash
# 1. Fija versión de Ollama, digests, cuantización, capacidades y plantillas.
oab lock

# 2. Audita el dataset y las herramientas sin llamar a modelos.
oab validate

# 3. Comprueba Ollama, digests, alimentación, térmica, swap y espacio.
oab preflight

# 4. Ejecuta una muestra de seis casos por modelo.
oab functional --mode smoke --allow-battery
```

## Benchmark oficial

Conecta el Mac a la corriente y verifica:

```bash
oab preflight --require-ac
```

### Fase funcional

```bash
FUNCTIONAL_RUN="functional_$(date -u '+%Y%m%dT%H%M%SZ')"

oab functional \
  --mode official-functional \
  --run-id "$FUNCTIONAL_RUN"
```

Por defecto ejecuta:

```text
60 casos × 3 repeticiones × número de modelos
```

Puede interrumpirse con `Ctrl+C`. Los casos terminados quedan guardados:

```bash
oab functional \
  --mode official-functional \
  --run-id "$FUNCTIONAL_RUN" \
  --resume
```

### Fase de rendimiento

```bash
PERFORMANCE_RUN="performance_$(date -u '+%Y%m%dT%H%M%SZ')"

oab performance \
  --mode official-performance \
  --run-id "$PERFORMANCE_RUN"
```

Mide, por workload:

- una ejecución fría;
- cinco ejecuciones calientes;
- tres ejecuciones streaming para TTFT;
- tiempos oficiales de la API de Ollama;
- memoria comunicada por `/api/ps`;
- variación de swap cuando macOS la expone.

### Informe final

```bash
oab report \
  --functional-run "runs/$FUNCTIONAL_RUN" \
  --performance-run "runs/$PERFORMANCE_RUN"
```

Genera:

```text
reports/report_<fecha>/
├── report.md
├── report.json
├── scores.csv
└── charts/
    ├── final_score.svg
    ├── generation_tps.svg
    ├── memory_gib.svg
    └── tool_reliability.svg
```

## Cómo añadir o cambiar modelos

1. Descarga los modelos con Ollama.
2. Modifica `config/benchmark.json`.
3. Regenera el lock:

```bash
oab lock --force
```

4. Ejecuta de nuevo `oab preflight`.

No mezcles resultados producidos con listas de modelos, parámetros o digests diferentes. Cada run guarda un manifiesto para detectarlo.

Consulta [docs/model-configuration.md](docs/model-configuration.md).

## Qué guarda cada run

### Funcional

```text
runs/<id>/
├── run_manifest.json
├── records.jsonl
├── results.csv
├── summary.json
└── system_snapshots.jsonl
```

Cada registro conserva:

- prompt y mensajes exactos;
- definición de herramientas;
- respuesta completa;
- tool calls y argumentos;
- resultados simulados;
- puntuación automática;
- métricas de Ollama por turno;
- errores y duración de pared.

### Rendimiento

```text
runs/<id>/
├── performance_manifest.json
├── performance_records.jsonl
├── ttft_records.jsonl
├── performance_results.csv
├── performance_summary.json
└── performance_system_snapshots.jsonl
```

## Interpretación rápida

- **Prompt tok/s:** rapidez al leer y procesar la entrada.
- **Generation tok/s:** rapidez al escribir la salida.
- **Load duration:** coste de cargar el modelo después de descargarlo de memoria.
- **TTFT:** espera hasta el primer fragmento visible en una respuesta streaming.
- **`size_vram`:** memoria que Ollama asocia al modelo cargado; no es el tamaño del archivo descargado.
- **Wilson 95 %:** intervalo de incertidumbre de una tasa de éxito.
- **McNemar:** comparación pareada de qué casos supera un modelo y falla el otro.
- **Consistencia:** porcentaje de casos superados en todas las repeticiones.

Consulta [docs/metrics.md](docs/metrics.md).

## Después de formatear el ordenador

El repositorio conserva:

- código;
- casos y herramientas;
- configuración de ejemplo;
- metodología;
- manifests y resultados que decidas versionar externamente.

No conserva automáticamente los pesos de Ollama. Los tags pueden cambiar y apuntar a artefactos nuevos. Para conservar exactamente los mismos modelos:

```bash
# Solo metadatos y digests:
./scripts/backup_ollama_models.sh

# Copia grande de ~/.ollama/models; requiere confirmación explícita:
./scripts/backup_ollama_models.sh \
  --include-weights \
  --confirm-large-backup \
  --output-dir /Volumes/MI_DISCO/ollama-backup
```

No subas los pesos a GitHub. Pueden ocupar decenas de GB y estar sujetos a licencias específicas.

Guía completa: [docs/restore-after-format.md](docs/restore-after-format.md).

## Publicar este proyecto en GitHub

El script se detiene si no recibe confirmación explícita y crea el repositorio como privado por defecto:

```bash
brew install gh
gh auth login

./scripts/publish_github.sh \
  --repo ollama-agent-benchmark \
  --private \
  --confirm-publish
```

Para hacerlo público, sustituye `--private` por `--public`. Antes de publicarlo conviene elegir una licencia. Este borrador no concede una licencia de reutilización.

## Estructura

```text
.
├── config/                 # Parámetros y lock local ignorado por Git
├── datasets/               # Casos, fixtures, herramientas y workloads
├── docs/                   # Metodología, seguridad y recuperación
├── examples/               # Configuraciones de referencia
├── scripts/                # Instalación, publicación y backups
├── src/ollama_agent_benchmark/
├── tests/
└── .github/workflows/ci.yml
```

## Limitaciones

- Compara artefactos completos. No puede aislar por sí solo el efecto causal de backend, cuantización, plantilla, arquitectura o speculative decoding.
- La puntuación de velocidad y memoria es relativa al conjunto de modelos de cada run.
- Las herramientas son simuladas. Antes de conectar un ganador a herramientas reales se necesita una validación adicional con sandbox y confirmación humana.
- El benchmark no garantiza que un tag antiguo siga disponible en el registro de Ollama.
- La primera versión se centra en texto y tool calling; visión y audio no forman parte de la puntuación principal.

## Documentación

- [Metodología](docs/methodology.md)
- [Métricas](docs/metrics.md)
- [Seguridad](docs/security.md)
- [Configuración de modelos](docs/model-configuration.md)
- [Arquitectura](docs/architecture.md)
- [Recuperación tras formatear](docs/restore-after-format.md)
- [Limitaciones](docs/limitations.md)

## Referencias oficiales

Las decisiones relacionadas con la API, duraciones, tool calling, modelos cargados y contexto se apoyan en la [documentación oficial de Ollama](docs/references.md).
