# Ollama Agent Benchmark

Benchmark local, reproducible y auditable para comparar modelos servidos por **Ollama** antes de utilizarlos como agentes con acceso a herramientas.

El proyecto está pensado especialmente para Apple Silicon, pero la parte funcional y la API de Ollama también pueden ejecutarse en Linux. Las comprobaciones de batería, estado térmico y swap son específicas de macOS y se omiten cuando no están disponibles.

> Estado: **v0.2.0 experimental y auditable**. Las herramientas son simuladas; ningún modelo recibe acceso real a la shell ni a tus archivos. Los runs de `0.1.0` son incompatibles y se rechazan.

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

Los pesos se cambian en `config/benchmark.json`. La velocidad integra generación (35 %), prompt (20 %), latencia caliente (15 %), TTFT (15 %) y carga fría (15 %). Una métrica ausente queda como `N/D` y hace incompleto el score: nunca cuenta como perfecta.

## Conceptos esenciales

- **LLM:** modelo de lenguaje que predice tokens; **modelo/tag:** artefacto y nombre local con el que Ollama lo expone.
- **Ollama:** servidor local de inferencia; **digest:** huella del artefacto exacto detrás de un tag mutable.
- **Cuantización:** representación numérica reducida que ahorra memoria a costa de posibles cambios de calidad.
- **Contexto (`num_ctx`):** ventana máxima de tokens; **seed:** semilla que reduce variación sin prometer determinismo bit a bit.
- **Prompt/token:** entrada y unidad de texto procesada. **Prompt tok/s** mide lectura; **generation tok/s**, salida.
- **Tool calling:** petición JSON estructurada de una herramienta. Un **agente** itera entre modelo, herramientas y resultados.
- **TTFT:** tiempo hasta el primer fragmento; **carga fría:** modelo descargado antes de medir; **caliente:** modelo ya residente.
- **Caché/KV:** estado reutilizado durante generación; crece con contexto. En Apple Silicon comparte la **memoria unificada**.
- **`size_vram`/swap:** asignación comunicada por Ollama y memoria paginada. Si no están disponibles se informa `N/D`.
- **Manifest/JSONL:** ficha de procedencia del experimento y formato de un objeto JSON por línea.
- **Wilson/McNemar:** intervalo sobre mayorías por caso y comparación pareada entre los mismos casos.
- **Consistencia:** caso superado en todas las repeticiones. Un run **oficial** cumple todo el protocolo; uno **exploratorio** no entra en el ranking oficial.

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
git clone https://github.com/pabloluque14/ollama-agent-benchmark.git
cd ollama-agent-benchmark
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
oab init
```

`.venv` es una carpeta local e ignorada por Git: contiene Python y paquetes del proyecto sin modificar la instalación global. `source` solo cambia la Terminal actual; `deactivate` sale y `source .venv/bin/activate` vuelve a entrar. `pip install -e .` instala un enlace editable y el comando `oab`; no instala dependencias de ejecución externas.

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
# 1. CONTACTA con Ollama, pero no carga modelos: fija versión, digests y metadatos.
oab lock

# 2. NO contacta con Ollama: audita configuración, dataset y simulador.
oab validate

# 3. CONTACTA con Ollama y consulta estado; no genera respuestas.
oab preflight

# 4. CARGA modelos y genera: muestra exploratoria de seis casos.
oab functional --mode smoke --allow-battery
```

Antes de contactar con Ollama puedes revisar ambos planes, sin red ni modelos:

```bash
oab functional --mode dry-run
oab performance --mode dry-run
```

`oab init` crea `config/benchmark.json`; `lock` crea `config/models.lock.json` y su SHA-256; los runners crean `runs/<id>/`; `report` crea `reports/report_<fecha>/`. Estos artefactos locales están ignorados por Git.

## Configuración v0.2.0

El ejemplo completo y ejecutable está en `config/benchmark.example.json`. `models` fija nombres y orden inicial; `ollama.base_url` debe ser localhost; `generation` fija contexto, sampling, seed, límite y `think`; `functional` controla repeticiones, turnos y pausas; `performance` usa tres frías, cinco calientes y tres TTFT; `order_control.seed` baraja casos reproduciblemente; `weights` combina las cuatro categorías; `speed_weights` suma 1; `workload_weights` agrega después de calcular cada workload. `missing_metric_policy: incomplete_score` impide premiar datos ausentes. Una clave obligatoria ausente produce un error con su ruta, no un `KeyError` opaco.

No mezcles `think`, contexto, sampling, workloads, modelos, digests o versiones. Cada combinación es un experimento diferente y queda capturada en el manifest.

## Benchmark oficial

Conecta el Mac a la corriente y verifica. En Linux la batería es `not_applicable`: el run puede ser oficial, pero térmica, swap o `size_vram` no disponibles permanecen `N/D`.

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

- tres ejecuciones frías verificadas;
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
- **TTFT:** espera hasta el primer fragmento visible; forma parte del score de velocidad.
- **`size_vram`:** memoria que Ollama asocia al modelo cargado; no es el tamaño del archivo descargado.
- **Wilson 95 %:** intervalo sobre el resultado mayoritario de casos únicos, nunca sobre repeticiones pseudorreplicadas.
- **McNemar:** comparación pareada de mayorías por los mismos casos. Un empate de repeticiones se considera fallo conservador.
- **Consistencia:** porcentaje de casos superados en todas las repeticiones.

`report.md` explica el resultado; `report.json` conserva datos y procedencia; `scores.csv` facilita hojas de cálculo; los SVG son vistas. Revisa primero tasas absolutas, consistencia, intervalos, errores y métricas brutas. El ganador no tiene por qué ser el más rápido, y los scores relativos cambian si cambia el conjunto de modelos.

El informe compara schema, benchmark, identidades/digests, Ollama, generación, orden, hashes, modelos, elegibilidad y protocolo guardado en ambos manifests. Por defecto falla ante cualquier incompatibilidad. `--allow-incompatible` crea una salida marcada visiblemente como exploratoria y sin ranking oficial.

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

## Desarrollo y comprobaciones

```bash
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
oab validate
ruff check .
mypy
coverage run -m unittest discover -s tests
coverage report
```

Las integrales levantan un servidor Ollama falso en un puerto efímero y prueban API, streaming, errores, timeouts, cambios de identidad, descarga y report. CI repite lo anterior en Ubuntu/macOS y Python 3.11/3.12 sin modelos ni servidor externo. El umbral es 75 % sobre lógica reutilizable; las envolturas `main()` se validan por flujos de CI y no entran en el denominador.

Cambios de schema, evaluación o scoring requieren dataset versionado, pruebas deterministas y changelog. Consulta [CONTRIBUTING.md](CONTRIBUTING.md) y [migración 0.2.0](docs/migration-0.2.0.md). La licencia (MIT, Apache-2.0 u otra) queda pendiente de decisión expresa del propietario; este repositorio no añade una automáticamente.

## Solución de problemas

- **Ollama no iniciado/timeout:** inicia Ollama y repite `oab preflight`; no uses `--resume` hasta recuperar el mismo servidor.
- **Modelo ausente:** instala el tag y regenera el lock. **Digest o versión cambiados:** no mezcles; conserva el run antiguo o crea experimento nuevo.
- **Configuración inválida:** lee la ruta exacta mostrada; compara con `benchmark.example.json` y ejecuta `oab validate`.
- **Sin cargador en macOS:** el oficial se bloquea; `--allow-battery` solo produce exploratorio. Linux no necesita `pmset`.
- **Modelo aún cargado:** espera o revisa `/api/ps`; una fría no verificada se registra inválida y puede reintentarse con `--resume`.
- **Run existente/resume incompatible:** usa exactamente el mismo comando/configuración o un `--run-id` nuevo. Nunca borres el manifest para forzar una mezcla.
- **Memoria/swap:** detén otras cargas, reduce modelos/contexto y empieza un run nuevo. `N/D` significa no medido, no cero.
- **Informe incompatible:** usa los dos runs del mismo experimento. `--allow-incompatible` sirve solo para diagnóstico exploratorio.
- **Runs 0.1.0:** no se convierten ni mezclan; repite el benchmark con v0.2.0.

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
