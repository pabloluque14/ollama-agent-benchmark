# Ollama Agent Benchmark v0.2.0

Benchmark local, reproducible y auditable para comparar modelos servidos por Ollama antes de
utilizarlos como agentes con herramientas.

> Estado: versión `0.2.0` experimental. Las herramientas del benchmark son virtuales: los modelos
> no reciben acceso a la shell, a tus archivos ni a aplicaciones reales. Los runs de `0.1.0` no son
> compatibles con esta versión.

## Documentación del proyecto

Si buscas una explicación especializada, puedes abrir directamente estos documentos:

- [Metodología experimental](docs/methodology.md): diseño del benchmark, repeticiones y comparabilidad.
- [Métricas y puntuaciones](docs/metrics.md): velocidad, TTFT, memoria, Wilson, McNemar y datos `N/D`.
- [Seguridad](docs/security.md): herramientas simuladas, confirmaciones y prompt injection.
- [Configuración de modelos](docs/model-configuration.md): tags, digests, contexto, sampling y thinking.
- [Arquitectura](docs/architecture.md): componentes, formatos y flujo interno.
- [Limitaciones](docs/limitations.md): qué conclusiones permite y cuáles no.
- [Migración desde 0.1.0](docs/migration-0.2.0.md): por qué hay que repetir los runs antiguos.
- [Recuperación después de formatear](docs/restore-after-format.md): proyecto, digests y pesos.
- [Referencias oficiales](docs/references.md): documentación de Ollama utilizada.
- [Guía de contribución](CONTRIBUTING.md): tests, Ruff, Mypy y cobertura.
- [Historial de cambios](CHANGELOG.md): diferencias entre versiones.
- [Política de seguridad](SECURITY.md): cómo comunicar problemas sensibles.

Este README tiene dos partes principales:

1. Un recorrido completo para macOS que se puede seguir de principio a fin.
2. Una referencia de todos los comandos y opciones de `oab`.

## Qué decisión ayuda a tomar

Un modelo rápido no es necesariamente un buen agente. Puede seleccionar una herramienta incorrecta,
enviar argumentos inventados, ignorar el resultado obtenido, escribir sin confirmación o seguir una
instrucción maliciosa encontrada dentro de un archivo.

El benchmark compara cuatro áreas:

| Área | Peso inicial | Qué observa |
|---|---:|---|
| Fiabilidad de herramientas | 40 % | Herramienta, argumentos, orden, resultados, errores y confirmaciones |
| Calidad y razonamiento | 25 % | Instrucciones, cálculo, síntesis, depuración e información insuficiente |
| Velocidad | 20 % | Generación, procesamiento del prompt, latencia, TTFT y carga fría |
| Memoria y estabilidad | 15 % | `size_vram`, swap, salidas inválidas y errores del runner |

La puntuación ayuda a elegir qué artefacto completo funciona mejor en un Mac concreto con una versión
concreta de Ollama. No demuestra por sí sola que una arquitectura sea universalmente superior ni
permite atribuir una diferencia exclusivamente a MLX, GGUF, una cuantización o una plantilla.

## Qué significa que las herramientas sean simuladas

Los casos funcionales ofrecen al modelo herramientas con nombres como `read_file`, `write_file` o
`simulated_terminal`. El modelo puede solicitar una llamada estructurada, pero el runner la ejecuta
sobre archivos ficticios guardados en memoria.

Por tanto:

- no se abre una terminal real;
- no se leen documentos del usuario;
- no se escriben archivos personales;
- una operación simulada de escritura desaparece al terminar el caso;
- sí se puede medir si el modelo pide confirmación, respeta rutas y rechaza prompt injection.

Superar este benchmark no autoriza a conectar directamente el modelo a OpenClaw, una shell o datos
privados. Antes harían falta un sandbox real, permisos mínimos y confirmaciones externas al texto que
ve el modelo.

## Mapa del proceso completo

```text
Instalar el proyecto
        ↓
oab init                  crea la configuración local
        ↓
editar benchmark.json     elige modelos y protocolo
        ↓
oab validate              revisión estática, sin Ollama
        ↓
dry-runs                  muestran los planes, sin Ollama
        ↓
oab lock                  fija digests y versión de Ollama
        ↓
oab preflight             comprueba que el entorno está preparado
        ↓
smoke funcional           prueba real pequeña
        ↓
smoke de rendimiento      prueba real pequeña
        ↓
benchmark funcional       run oficial completo
        ↓
benchmark rendimiento     run oficial completo
        ↓
oab report                valida procedencia y genera el informe
```

Resumen de contacto con Ollama:

| Acción | Contacta con Ollama | Carga modelos | Genera respuestas |
|---|---:|---:|---:|
| `oab init` | No | No | No |
| `oab validate` | No | No | No |
| `oab functional --mode dry-run` | No | No | No |
| `oab performance --mode dry-run` | No | No | No |
| `oab lock` | Sí | No debería | No |
| `oab preflight` | Sí | No debería | No |
| `oab functional --mode smoke` | Sí | Sí | Sí |
| `oab performance --mode smoke` | Sí | Sí | Sí |
| Runs oficiales | Sí | Sí, repetidamente | Sí |
| `oab report` | No | No | No |

# Parte I: recorrido completo en macOS

## 1. Requisitos

Necesitas:

- macOS;
- Python 3.11 o superior;
- Ollama instalado;
- los modelos que quieras comparar ya descargados;
- espacio suficiente para modelos y resultados;
- el cargador conectado para los runs oficiales.

Comprueba Python:

```bash
python3 --version
```

Debes ver `Python 3.11`, `3.12` o una versión posterior. Si `python3` no existe o la versión es
anterior, instala una versión compatible antes de continuar. El proyecto no modifica el Python
global y no necesita `sudo`.

## 2. Descargar el proyecto

### Qué hace

`git clone` descarga el código y su historial desde GitHub. `cd` cambia la Terminal a la carpeta del
proyecto. Todavía no se instala Python, no se contacta con Ollama y no se carga ningún modelo.

### Por qué se hace

Todos los comandos posteriores deben ejecutarse desde la raíz del repositorio, donde están
`pyproject.toml`, `config/`, `datasets/` y `src/`.

### Comandos

```bash
git clone https://github.com/pabloluque14/ollama-agent-benchmark.git
cd ollama-agent-benchmark
```

### Qué cambia

Se crea la carpeta `ollama-agent-benchmark` con archivos versionados. No se crea aún `.venv`, ninguna
configuración privada ni carpetas de resultados.

### Qué deberías ver

```bash
pwd
ls
```

`pwd` debería terminar en `/ollama-agent-benchmark` y `ls` debería mostrar, entre otros,
`README.md`, `config`, `datasets`, `docs`, `src` y `tests`.

### Si falla

- `git: command not found`: instala las herramientas de línea de comandos de Xcode.
- `repository not found`: revisa la URL y el acceso al repositorio.
- Ya existe la carpeta: entra en ella con `cd` o elige otro destino; no clones encima sin revisar.

## 3. Crear y activar el entorno virtual

### Qué hace

El primer comando crea `.venv`, una instalación de Python aislada dentro del proyecto. El segundo
activa ese entorno en la Terminal actual.

### Por qué se hace

Evita instalar el paquete y las herramientas de desarrollo en el Python global del Mac.

### Contacto y archivos

- No contacta con Ollama.
- No carga modelos.
- Crea la carpeta local `.venv/`, ignorada por Git.

### Comandos

Si tienes el ejecutable `python3.11`:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Si `python3 --version` ya muestra 3.11 o superior, también puedes usar:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Qué deberías ver

Normalmente aparece `(.venv)` al principio del prompt. Confírmalo con:

```bash
which python
python --version
```

`which python` debería señalar a `.../ollama-agent-benchmark/.venv/bin/python`.

### Cómo salir y volver

```bash
deactivate
```

Esto no borra nada; solo desactiva el entorno en esa Terminal. Para volver:

```bash
cd /ruta/a/ollama-agent-benchmark
source .venv/bin/activate
```

### Si falla

- `command not found: python3.11`: usa un `python3` compatible o instala Python 3.11.
- `no such file or directory: .venv/bin/activate`: la creación de `.venv` no terminó correctamente.
- El prompt no cambia: ejecuta de nuevo `source .venv/bin/activate` desde la raíz del proyecto.

## 4. Instalar el paquete

### Qué hace y por qué

Instala el proyecto en modo editable y crea el comando `oab` dentro de `.venv`. “Editable” significa
que los cambios del código se usan sin reinstalar el paquete después de cada edición.

### Contacto y archivos

- Puede contactar con el índice de paquetes para preparar la instalación, dependiendo de tu entorno.
- No contacta con Ollama.
- No carga modelos.
- Añade metadatos del paquete dentro de `.venv`; no instala dependencias obligatorias de ejecución.

### Comando

```bash
python -m pip install -e .
```

### Qué deberías ver

Al final debe aparecer un mensaje equivalente a `Successfully installed ollama-agent-benchmark`.
Comprueba el comando:

```bash
oab --help
```

### Si falla

- Confirma que `.venv` está activa con `which python`.
- Confirma que estás en la carpeta que contiene `pyproject.toml`.
- Si hay un error de red al instalar herramientas de construcción, recupera la conexión y repite.
- No uses `sudo pip install`.

## 5. Crear la configuración con `oab init`

### Qué hace

Copia `config/benchmark.example.json` a `config/benchmark.json`.

### Por qué se hace

El archivo de ejemplo está versionado y sirve de plantilla. `benchmark.json` es tu configuración
local: puede cambiar sin modificar el ejemplo y Git la ignora.

### Contacto y archivos

- No contacta con Ollama.
- No carga modelos.
- Crea `config/benchmark.json`.
- No crea el lock ni ningún run.

### Comando

```bash
oab init
```

### Qué deberías ver

```text
Configuración creada: .../config/benchmark.json
Edita la lista 'models' y después ejecuta: oab lock
```

### Si falla

Si indica que el archivo ya existe, no es necesariamente un error: protege tu configuración.
Revísala con:

```bash
nano config/benchmark.json
```

Solo si quieres sustituirla por el ejemplo y ya tienes copia de cualquier cambio importante:

```bash
oab init --force
```

`--force` sobrescribe `config/benchmark.json`; no afecta al ejemplo ni a los modelos de Ollama.

## 6. Entender y editar `benchmark.json`

Abre el archivo:

```bash
nano config/benchmark.json
```

En `nano`, guarda con `Ctrl+O`, confirma con `Enter` y sal con `Ctrl+X`.

La configuración de ejemplo de v0.2.0 es:

```json
{
  "schema_version": 2,
  "benchmark_version": "0.2.0",
  "models": [
    "gemma4:12b-mlx",
    "gemma4:12b-it-qat",
    "qwen3.5:9b-mlx"
  ],
  "ollama": {
    "base_url": "http://127.0.0.1:11434"
  },
  "generation": {
    "num_ctx": 8192,
    "temperature": 0,
    "seed": 42,
    "top_k": 1,
    "top_p": 1.0,
    "min_p": 0.0,
    "repeat_penalty": 1.0,
    "presence_penalty": 0.0,
    "num_predict": 1024,
    "think": false
  },
  "functional": {
    "repetitions": 3,
    "max_turns": 8,
    "keep_alive": "5m",
    "pause_between_models_seconds": 30,
    "smoke_pause_seconds": 2
  },
  "order_control": {
    "seed": 20260718,
    "policy": "rotating_models_shuffled_cases"
  },
  "performance": {
    "cold_runs": 3,
    "hot_runs": 5,
    "ttft_runs": 3,
    "keep_alive": "5m",
    "pause_after_unload_seconds": 10,
    "pause_between_models_seconds": 30
  },
  "weights": {
    "tool_reliability": 0.4,
    "quality_reasoning": 0.25,
    "speed": 0.2,
    "memory_stability": 0.15
  },
  "speed_weights": {
    "generation": 0.35,
    "prompt": 0.2,
    "hot_latency": 0.15,
    "ttft": 0.15,
    "cold_load": 0.15
  },
  "workload_weights": {
    "short_technical_answer": 0.3333333333333333,
    "long_generation": 0.3333333333333333,
    "long_prompt_short_answer": 0.3333333333333334
  },
  "missing_metric_policy": "incomplete_score"
}
```

### Identidad y modelos

| Campo | Qué significa | Cuándo cambiarlo |
|---|---|---|
| `schema_version` | Versión del formato de configuración | No lo cambies manualmente |
| `benchmark_version` | Versión del protocolo | Debe ser `0.2.0` |
| `models` | Tags exactos de Ollama que se compararán | Cambia la lista por los modelos instalados |
| `ollama.base_url` | Dirección de la API local | Mantén `127.0.0.1:11434` salvo configuración local deliberada |

El orden de `models` es el punto de partida. El runner rota el orden entre repeticiones para reducir
el sesgo de posición. Todos los modelos de un informe oficial deben participar en ambos runs.

Comprueba los nombres instalados:

```bash
ollama list
```

Este comando sí consulta tu instalación real de Ollama. Copia los nombres exactamente, incluidos los
tags situados después de `:`.

### Generación

| Campo | Efecto |
|---|---|
| `num_ctx` | Contexto máximo. Más contexto suele consumir más memoria |
| `temperature` | Aleatoriedad. Cero favorece reproducibilidad |
| `seed` | Semilla de generación. No garantiza igualdad bit a bit en todos los backends |
| `top_k` | Limita cuántos candidatos considera el muestreo |
| `top_p` | Limita candidatos por probabilidad acumulada |
| `min_p` | Descarta candidatos demasiado improbables |
| `repeat_penalty` | Penaliza repeticiones de tokens |
| `presence_penalty` | Penaliza tokens ya presentes |
| `num_predict` | Máximo de tokens de salida |
| `think` | Activa o desactiva thinking cuando el modelo y Ollama lo soportan |

Cambiar cualquiera de estos valores crea un experimento diferente. No reanudes un run antiguo con
parámetros nuevos.

### Runner funcional

| Campo | Efecto |
|---|---|
| `repetitions` | Veces que cada modelo ejecuta cada caso en modo oficial |
| `max_turns` | Máximo de intercambios modelo-herramienta por caso |
| `keep_alive` | Tiempo que Ollama mantiene el modelo cargado |
| `pause_between_models_seconds` | Descanso entre bloques oficiales de modelos |
| `smoke_pause_seconds` | Descanso corto en smoke tests |

Con 60 casos, 3 repeticiones y 3 modelos se ejecutan `60 × 3 × 3 = 540` casos funcionales.

### Orden experimental

| Campo | Efecto |
|---|---|
| `order_control.seed` | Semilla utilizada para barajar casos de manera reproducible |
| `order_control.policy` | Documenta la política de rotación y barajado |

No confundas `generation.seed` con `order_control.seed`: la primera afecta al modelo y la segunda al
orden del experimento.

### Rendimiento

| Campo | Efecto |
|---|---|
| `cold_runs` | Mediciones después de comprobar que el modelo fue descargado |
| `hot_runs` | Mediciones con el modelo ya cargado |
| `ttft_runs` | Mediciones streaming hasta el primer fragmento |
| `keep_alive` | Tiempo que Ollama mantiene el modelo residente |
| `pause_after_unload_seconds` | Espera después de descargar antes de una carga fría |
| `pause_between_models_seconds` | Descanso entre modelos |

Los tres workloads son:

- `short_technical_answer`: respuesta técnica breve con cuatro puntos;
- `long_generation`: generación sostenida sobre caché KV;
- `long_prompt_short_answer`: prompt largo con una respuesta corta verificable.

Una respuesta que no cumple el workload se conserva como inválida. No obtiene una ventaja de
latencia por terminar demasiado pronto.

### Pesos

`weights` combina las cuatro áreas del resultado final. `speed_weights` combina las cinco métricas de
velocidad. `workload_weights` combina los workloads después de resumir cada uno por separado.

Cada grupo debe sumar exactamente `1.0`. `missing_metric_policy: incomplete_score` significa que una
métrica ausente se muestra como `N/D` y puede impedir una puntuación completa; nunca se sustituye por
un valor perfecto.

## 7. Validar la configuración sin Ollama

### Qué hace

`oab validate` comprueba la configuración, IDs de casos, herramientas permitidas y secuencias del
simulador.

### Por qué se hace

Permite detectar errores de JSON o protocolo antes de gastar tiempo y batería cargando modelos.

### Contacto y archivos

- No contacta con Ollama.
- No carga modelos.
- No crea runs.
- Solo lee configuración y datasets.

### Comando

```bash
oab validate
```

### Qué deberías ver

Un resumen parecido a:

```text
Casos: 60
Herramientas simuladas: 6
Pasos de herramienta auditados: 39
Resultado: OK. No se llamó a Ollama.
```

### Si falla

- Revisa la ruta exacta mencionada en el error.
- Compara `config/benchmark.json` con `config/benchmark.example.json`.
- Comprueba comas, llaves y comillas del JSON.
- No continúes con `lock` o runs reales hasta obtener `Resultado: OK`.

## 8. Revisar los planes con dry-run

### Qué hace

Los dry-runs calculan modelos, casos, repeticiones, workloads y número de ejecuciones, pero se
detienen antes de contactar con Ollama.

### Por qué se hace

Sirven para verificar el tamaño del experimento y las selecciones antes de cargar modelos.

### Contacto y archivos

- No contactan con Ollama.
- No cargan modelos.
- No crean carpetas dentro de `runs/`.

### Comandos

```bash
oab functional --mode dry-run
oab performance --mode dry-run
```

### Qué deberías ver

El funcional muestra modelos, casos, repeticiones, total y orden. Rendimiento muestra workloads,
cargas frías, calientes, TTFT y total de respuestas no streaming. Ambos terminan indicando que no se
llamó a Ollama.

### Si falla

El problema es local y estático: configuración ausente, schema antiguo, modelo vacío, peso incorrecto
o dataset dañado. Ejecuta `oab validate` y corrige la causa antes de continuar.

## 9. Crear el lock con `oab lock`

### Qué hace

Consulta la API de Ollama y guarda la identidad exacta observada de cada modelo: tag, digest, tamaño,
familia, cuantización, capacidades y hashes de plantilla/Modelfile. También registra la versión del
servidor Ollama.

### Por qué se hace

Los tags pueden cambiar. El lock permite detectar si `modelo:tag` apunta posteriormente a otro
artefacto y evita mezclar resultados incomparables.

### Contacto y archivos

- Sí contacta con Ollama.
- Consulta `/api/version`, `/api/tags` y `/api/show`.
- No solicita generación de texto y no debería cargar modelos para inferencia.
- Crea `config/models.lock.json` y `config/models.lock.json.sha256`.

### Antes de ejecutarlo

Abre Ollama y confirma que los modelos de `benchmark.json` aparecen en:

```bash
ollama list
```

### Comando

```bash
oab lock
```

### Qué deberías ver

Una línea por modelo con parte del digest, formato, cuantización y tamaño de parámetros, seguida de la
ruta del lock.

### Si falla

- `modelo no está instalado`: corrige el tag o descarga ese modelo con Ollama.
- No puede conectar: abre Ollama y revisa `ollama.base_url`.
- El lock ya existe: no lo sobrescribas sin saber por qué. Si cambiaste deliberadamente modelos o
  versión y quieres un experimento nuevo, utiliza:

```bash
oab lock --force
```

Regenerar el lock no convierte runs antiguos. Los siguientes runs deben usar IDs nuevos.

## 10. Comprobar el entorno con `oab preflight`

### Qué hace

Comprueba configuración, lock, versión/digests, modelos cargados, alimentación, estado térmico, swap,
espacio libre y hashes de artefactos.

### Por qué se hace

Un benchmark oficial debe empezar en condiciones conocidas. Cambios de digest, versión o energía
pueden alterar el resultado.

### Contacto y archivos

- Sí contacta con Ollama.
- No genera texto.
- No debería cargar un modelo que estuviera descargado.
- No crea un run; imprime el diagnóstico en Terminal.

### Comando recomendado en macOS

Conecta el cargador y ejecuta:

```bash
oab preflight --require-ac
```

### Qué deberías ver

Filas `[OK]`, `[INFO]` o `[AVISO]`, seguidas por:

```text
Errores críticos: 0
```

Un aviso no siempre bloquea, pero debes entenderlo antes de medir. Un error crítico devuelve código
de salida distinto de cero.

### Si falla

- Ollama no iniciado: abre la aplicación y repite.
- Digest o versión diferentes: no mezcles; decide si restaurar el artefacto anterior o crear un lock
  y experimento nuevos.
- Modelo cargado: espera a que se descargue o descárgalo antes de medir cargas frías.
- Batería: conecta el cargador.
- Poco espacio: libera espacio sin borrar locks o runs que necesites conservar.

## 11. Ejecutar un smoke test funcional

### Qué hace

Ejecuta una muestra pequeña de seis casos representativos por modelo: herramientas, confirmaciones,
seguridad y calidad.

### Por qué se hace

Confirma que los modelos aceptan tool calling, que la API responde y que el runner puede guardar
resultados antes del run oficial de 540 ejecuciones del ejemplo.

### Contacto y archivos

- Sí contacta con Ollama.
- Sí carga cada modelo seleccionado.
- Sí genera respuestas y tool calls.
- Crea `runs/<run-id>/` con manifest, JSONL, resumen, CSV y snapshots.
- El resultado es exploratorio y no debe presentarse como ranking oficial.

### Comando

```bash
SMOKE_FUNCTIONAL="smoke-functional-$(date -u '+%Y%m%dT%H%M%SZ')"

oab functional \
  --mode smoke \
  --run-id "$SMOKE_FUNCTIONAL"
```

### Qué deberías ver

Una cabecera por modelo y líneas `[PASS]` o `[FAIL]` por caso. `FAIL` significa que el modelo no
cumplió una regla; no implica necesariamente un error del programa. Al final aparecen las rutas de
`records.jsonl`, `summary.json` y `results.csv`.

### Si falla

- Error de conexión: repite `oab preflight`.
- Timeout: revisa memoria, modelo y contexto.
- Run ya existente: usa otro `--run-id` o reanuda exactamente el mismo experimento con `--resume`.
- Muchos `FAIL`: revisa `results.csv` y los `failed_checks`; no cambies expectativas solo para hacer
  que un modelo concreto pase.

## 12. Ejecutar un smoke test de rendimiento

### Qué hace

En modo smoke utiliza el primer workload y realiza una carga fría y una ejecución caliente por
modelo. No ejecuta TTFT en este modo reducido.

### Por qué se hace

Comprueba el flujo de descarga, carga, métricas y `/api/ps` con un coste mucho menor que el run
oficial.

### Contacto y archivos

- Sí contacta con Ollama.
- Carga y descarga modelos.
- Genera respuestas.
- Crea `runs/<run-id>/performance_*` y snapshots.
- El resultado es exploratorio.

### Comando

```bash
SMOKE_PERFORMANCE="smoke-performance-$(date -u '+%Y%m%dT%H%M%SZ')"

oab performance \
  --mode smoke \
  --run-id "$SMOKE_PERFORMANCE"
```

### Qué deberías ver

Líneas `[COLD]` y `[HOT]` con `generation tok/s`, `prompt tok/s` y posibles errores, seguidas por el
resumen agregado.

### Si falla

- No se confirmó la descarga: revisa si el modelo sigue apareciendo en `/api/ps` y reanuda después.
- Métrica `N/D`: puede no estar disponible; no equivale a cero.
- Presión de memoria o swap creciente: detén otras aplicaciones, deja enfriar el Mac y repite con un
  ID nuevo si cambian las condiciones.

## 13. Preparar los identificadores oficiales

Los identificadores evitan sobrescribir runs y permiten reanudarlos. En la misma Terminal:

```bash
BENCHMARK_DATE="$(date -u '+%Y%m%dT%H%M%SZ')"
FUNCTIONAL_RUN="functional-$BENCHMARK_DATE"
PERFORMANCE_RUN="performance-$BENCHMARK_DATE"

echo "$FUNCTIONAL_RUN"
echo "$PERFORMANCE_RUN"
```

Estas variables solo viven en la Terminal actual. Si cierras la ventana, consulta los nombres reales
con `ls runs` y vuelve a asignarlos exactamente antes de reanudar o informar.

## 14. Ejecutar el benchmark funcional oficial

### Qué hace

Ejecuta todos los casos seleccionados con las repeticiones configuradas. Con el ejemplo completo son
60 casos × 3 repeticiones × 3 modelos = 540 ejecuciones.

### Por qué se hace

Produce las mediciones funcionales que después se agregan por caso único y se comparan mediante
Wilson y McNemar.

### Contacto y archivos

- Sí contacta con Ollama y carga modelos.
- Genera múltiples turnos y tool calls simuladas.
- Puede tardar considerablemente.
- Crea `runs/$FUNCTIONAL_RUN/`.
- Guarda cada caso al terminar, por lo que una interrupción no pierde los registros completos.

### Antes de ejecutarlo

- Conecta el cargador.
- Cierra cargas intensivas innecesarias.
- Ejecuta `oab preflight --require-ac`.
- Confirma el dry-run y el smoke test.

### Comando

```bash
oab functional \
  --mode official-functional \
  --run-id "$FUNCTIONAL_RUN"
```

### Qué deberías ver

El plan completo, el orden por repetición y el progreso `[PASS]`/`[FAIL]`. Al finalizar:

```text
runs/<id>/
├── run_manifest.json
├── records.jsonl
├── results.csv
├── summary.json
└── system_snapshots.jsonl
```

### Cómo interrumpir y reanudar

Puedes pulsar `Ctrl+C`. Para continuar debes conservar exactamente configuración, lock, versión de
Ollama, modelos, digests, opciones, casos, repeticiones y modo:

```bash
oab functional \
  --mode official-functional \
  --run-id "$FUNCTIONAL_RUN" \
  --resume
```

El runner omite las `execution_key` ya terminadas. Si el manifest no coincide, se detiene en lugar de
mezclar experimentos. No edites el manifest para forzar la reanudación.

### Si falla

- `resume incompatible`: recupera la configuración original o inicia un run nuevo.
- Error del runner en un caso: queda registrado como fallo; inspecciona `records.jsonl`.
- Batería o térmica: detén el run, estabiliza las condiciones y decide si debe repetirse completo.
- Falta de memoria: reduce el conjunto de modelos o el contexto, pero usa un ID nuevo porque cambia
  el experimento.

## 15. Ejecutar el benchmark de rendimiento oficial

### Qué hace

Para cada modelo y workload realiza tres cargas frías verificadas, cinco ejecuciones calientes y tres
mediciones TTFT. También consulta memoria y swap cuando están disponibles.

### Por qué se hace

Separa comportamientos que una única mediana mezclaría: carga, prompt, generación, latencia, TTFT y
memoria. Los resultados se calculan primero por workload y después se agregan con pesos explícitos.

### Contacto y archivos

- Sí contacta con Ollama.
- Carga y descarga repetidamente todos los modelos.
- Genera respuestas no streaming y streaming.
- Es la fase más sensible a temperatura, batería y cargas externas.
- Crea `runs/$PERFORMANCE_RUN/`.

### Comando

```bash
oab performance \
  --mode official-performance \
  --run-id "$PERFORMANCE_RUN"
```

### Qué deberías ver

Progreso `[COLD]` y `[HOT]`, métricas y errores. Al finalizar:

```text
runs/<id>/
├── performance_manifest.json
├── performance_records.jsonl
├── ttft_records.jsonl
├── performance_results.csv
├── performance_summary.json
└── performance_system_snapshots.jsonl
```

### Cómo reanudar

```bash
oab performance \
  --mode official-performance \
  --run-id "$PERFORMANCE_RUN" \
  --resume
```

Las mediciones no streaming y TTFT tienen claves estables. Las completadas se omiten. Si una carga
fría no consiguió descargar el modelo, se registra el intento y puede reintentarse; los errores no
mejoran la puntuación.

### Si falla

- Descarga no verificada: espera y revisa modelos cargados antes de reanudar.
- Duplicado histórico: el resumen se detiene para evitar una mediana contaminada.
- Métricas ausentes: se muestran como `N/D`; consulta el informe antes de interpretar el score.
- Cambio de digest, Ollama o generación: inicia un experimento nuevo.

## 16. Generar el informe

### Qué hace

Lee el run funcional y el de rendimiento, valida que proceden del mismo experimento y genera Markdown,
JSON, CSV y SVG.

### Por qué se hace

Compartir nombres de modelos no basta. Antes de producir un ranking se comparan schema, benchmark,
modelos, digests, versión de Ollama, contexto, thinking, generación, orden, hashes, elegibilidad y
protocolo de scoring guardado en los manifests.

### Contacto y archivos

- No contacta con Ollama.
- No carga modelos.
- Lee únicamente los dos runs indicados.
- Crea una carpeta dentro de `reports/`.

### Comando recomendado

```bash
oab report \
  --functional-run "runs/$FUNCTIONAL_RUN" \
  --performance-run "runs/$PERFORMANCE_RUN"
```

### Qué deberías ver

El ranking completo, si todos los componentes están disponibles, y rutas semejantes a:

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

Abre primero `report.md`. Usa `report.json` para auditoría detallada y `scores.csv` para una hoja de
cálculo. Las gráficas SVG son vistas; no sustituyen las métricas brutas.

### Si falla

- Runs incompatibles: comprueba que ambos IDs pertenecen a la misma fecha/configuración.
- Run incompleto: reanuda la fase correspondiente.
- Score `N/D`: falta un componente necesario; el modelo no se incluye silenciosamente en un ranking
  completo.
- No uses `--allow-incompatible` para publicar un ganador. Esa opción produce únicamente un informe
  exploratorio, con advertencias visibles y sin ranking oficial.

## 17. Cómo interpretar el resultado

### Funcional

- **Tasa bruta:** porcentaje de ejecuciones individuales aprobadas.
- **Mayoría por caso:** cada caso cuenta una vez; necesita más de la mitad de repeticiones aprobadas.
- **Empate:** se considera fallo de forma conservadora.
- **Todas las repeticiones:** casos superados siempre.
- **Consistencia:** estabilidad del modelo entre repeticiones.
- **Wilson 95 %:** incertidumbre calculada sobre casos únicos, no sobre repeticiones independientes.
- **McNemar:** compara dos modelos sobre exactamente los mismos casos mayoritarios.

### Rendimiento

- **Prompt tok/s:** velocidad de procesar la entrada; más alto suele ser mejor.
- **Generation tok/s:** velocidad de producir la salida; más alto suele ser mejor.
- **Latencia caliente:** tiempo total con el modelo cargado; más bajo suele ser mejor.
- **TTFT:** espera hasta el primer fragmento visible; más bajo suele ser mejor.
- **Carga fría:** tiempo de cargar después de confirmar la descarga; más bajo suele ser mejor.
- **`size_vram`:** memoria comunicada por `/api/ps`; no equivale al tamaño descargado.
- **Swap:** paginación observada en macOS; un incremento puede indicar presión de memoria.

### Puntuaciones

Herramientas y calidad son tasas absolutas. Velocidad y memoria son relativas a los otros modelos del
mismo experimento. Si quitas o añades un modelo, pueden cambiar aunque las métricas brutas de un
modelo sean idénticas.

Por eso el ganador no siempre es el más rápido. Para elegir un agente, revisa también errores,
consistencia, seguridad, memoria y cumplimiento de workloads.

# Parte II: referencia completa de `oab`

## Ayuda general

```bash
oab --help
oab <comando> --help
```

`-h` y `--help` muestran ayuda y terminan sin ejecutar el comando. Ejemplo:

```bash
oab functional --help
```

## `oab init`

```text
oab init [--force]
```

| Opción | Valor predeterminado | Explicación |
|---|---|---|
| `-h`, `--help` | — | Muestra la ayuda |
| `--force` | Desactivado | Sobrescribe `config/benchmark.json` con el ejemplo |

Sin `--force`, se detiene si la configuración ya existe para no perder cambios.

## `oab lock`

```text
oab lock [--config RUTA] [--output RUTA] [--force]
```

| Opción | Valor predeterminado | Explicación |
|---|---|---|
| `-h`, `--help` | — | Muestra la ayuda |
| `--config RUTA` | `config/benchmark.json` | Usa otra configuración |
| `--output RUTA` | `config/models.lock.json` | Guarda el lock en otra ruta |
| `--force` | Desactivado | Sustituye un lock existente |

Ejemplo con rutas explícitas:

```bash
oab lock \
  --config config/benchmark.json \
  --output config/models.lock.json \
  --force
```

## `oab validate`

```text
oab validate
```

Solo admite `-h`/`--help`. No contacta con Ollama y no tiene modos abreviados.

## `oab preflight`

```text
oab preflight [--config RUTA] [--lock RUTA] [--require-ac] [--json]
```

| Opción | Valor predeterminado | Explicación |
|---|---|---|
| `-h`, `--help` | — | Muestra la ayuda |
| `--config RUTA` | `config/benchmark.json` | Comprueba otra configuración |
| `--lock RUTA` | `config/models.lock.json` | Comprueba otro lock |
| `--require-ac` | Desactivado | Convierte la falta de corriente en error en macOS |
| `--json` | Desactivado | Imprime resultados como JSON en vez de tabla humana |

`--json` es útil para scripts:

```bash
oab preflight --require-ac --json
```

## `oab functional`

```text
oab functional
  [--mode {dry-run,smoke,official-functional}]
  [--models MODELO1,MODELO2]
  [--case-ids CASO1,CASO2]
  [--run-id ID]
  [--resume]
  [--allow-battery]
  [--repetitions N]
```

| Opción | Predeterminado | Explicación |
|---|---|---|
| `-h`, `--help` | — | Muestra todas las opciones |
| `--mode dry-run` | `dry-run` | Valida y muestra el plan sin Ollama |
| `--mode smoke` | — | Ejecuta seis casos representativos, una repetición |
| `--mode official-functional` | — | Ejecuta el conjunto oficial completo |
| `--models` | Todos los del lock | Limita modelos; se separan con comas y sin espacios necesarios |
| `--case-ids` | Casos del modo | Limita IDs concretos, por ejemplo `T001,Q005` |
| `--run-id` | ID basado en fecha UTC | Elige nombre estable para la carpeta del run |
| `--resume` | Desactivado | Reanuda el mismo ID tras validar el manifest |
| `--allow-battery` | Desactivado | Permite batería, pero el run oficial queda como exploratorio |
| `--repetitions N` | Configuración/modo | Sobrescribe repeticiones; `N` debe ser al menos 1 |

Ejemplo de diagnóstico muy pequeño:

```bash
oab functional \
  --mode smoke \
  --models gemma4:12b-mlx \
  --case-ids T001,Q005 \
  --run-id diagnostico-gemma \
  --repetitions 1
```

No utilices una selección parcial como si fuera el benchmark oficial completo.

## `oab performance`

```text
oab performance
  [--mode {dry-run,smoke,official-performance}]
  [--models MODELO1,MODELO2]
  [--workloads ID1,ID2]
  [--run-id ID]
  [--allow-battery]
  [--resume]
```

| Opción | Predeterminado | Explicación |
|---|---|---|
| `-h`, `--help` | — | Muestra todas las opciones |
| `--mode dry-run` | `dry-run` | Muestra el plan sin Ollama |
| `--mode smoke` | — | Primer workload, una fría, una caliente y sin TTFT |
| `--mode official-performance` | — | Protocolo completo configurado |
| `--models` | Todos los del lock | Limita modelos bloqueados, separados por comas |
| `--workloads` | Todos los del dataset | Limita workloads por ID, separados por comas |
| `--run-id` | ID basado en fecha UTC | Elige la carpeta estable del run |
| `--allow-battery` | Desactivado | Permite batería y vuelve exploratorio un run oficial |
| `--resume` | Desactivado | Reanuda tras comparar el manifest y omite claves completas |

Ejemplo exploratorio de un modelo y un workload:

```bash
oab performance \
  --mode official-performance \
  --models gemma4:12b-mlx \
  --workloads short_technical_answer \
  --run-id exploratorio-rendimiento \
  --allow-battery
```

Aunque usa el protocolo de rendimiento, `--allow-battery` impide que sea elegible como oficial.

## `oab report`

```text
oab report
  [--functional-run RUTA]
  [--performance-run RUTA]
  [--output RUTA]
  [--allow-incompatible]
```

| Opción | Predeterminado | Explicación |
|---|---|---|
| `-h`, `--help` | — | Muestra la ayuda |
| `--functional-run RUTA` | Último funcional localizado | Selecciona explícitamente el run funcional |
| `--performance-run RUTA` | Último rendimiento localizado | Selecciona explícitamente el run de rendimiento |
| `--output RUTA` | `reports/report_<fecha>` | Elige la carpeta de salida |
| `--allow-incompatible` | Desactivado | Permite informe exploratorio incompatible, nunca ranking oficial |

Es preferible indicar siempre ambos runs. La selección automática del “último” puede escoger fases de
experimentos diferentes, que después serán rechazadas por la validación.

Ejemplo con salida explícita:

```bash
oab report \
  --functional-run runs/functional-20260718T120000Z \
  --performance-run runs/performance-20260718T120000Z \
  --output reports/comparacion-20260718
```

## Archivos locales y Git

El proyecto ignora por defecto:

```text
.venv/
config/benchmark.json
config/models.lock.json
runs/
reports/
```

GitHub recupera código, datasets, documentación y configuración de ejemplo. No recupera
automáticamente tu entorno virtual, configuración local, lock, runs ignorados ni pesos de Ollama.

Los pesos pueden ocupar decenas de GB y tener licencias propias. No los subas a GitHub. Consulta la
[guía de recuperación](docs/restore-after-format.md) antes de formatear el Mac.

## Solución de problemas resumida

| Problema | Qué significa | Acción recomendada |
|---|---|---|
| Ollama no responde | La API local no está disponible | Abre Ollama y ejecuta preflight |
| Modelo no instalado | El tag configurado no aparece | Revisa `ollama list` y corrige `models` |
| Digest cambiado | El tag apunta a otro artefacto | No mezcles; crea lock y runs nuevos |
| Versión de Ollama cambiada | Cambió parte del entorno | Empieza un experimento nuevo |
| Configuración inválida | Falta una clave, tipo o peso | Compara con el ejemplo y usa validate |
| Falta el cargador | El run oficial no es estable/elegible | Conecta corriente y repite preflight |
| Modelo sigue cargado | No se puede confirmar carga fría | Espera, descarga y reanuda |
| Run ya existente | El ID está ocupado | Reanuda el mismo o crea otro ID |
| Resume incompatible | El experimento solicitado cambió | Recupera originales o usa un ID nuevo |
| Falta de memoria | Modelo/contexto exceden el entorno | Cierra cargas o diseña otro experimento |
| Swap elevado | Existe presión de memoria | Estabiliza el Mac antes de medir |
| Timeout | Ollama/modelo no terminó a tiempo | Revisa recursos y registro del run |
| Métrica `N/D` | No fue posible medirla | No la interpretes como cero o perfecta |
| Informe incompatible | Los manifests no describen el mismo experimento | Selecciona la pareja correcta de runs |

## Desarrollo

Para trabajar en el código y ejecutar la suite contra el servidor Ollama falso:

```bash
source .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check .
mypy
PYTHONPATH=tests coverage run -m unittest discover -s tests -v
coverage report
oab validate
```

Las pruebas integrales no necesitan una instalación real de Ollama. La CI ejecuta la suite en macOS y
Ubuntu con Python 3.11 y 3.12. La licencia del proyecto continúa pendiente de una decisión expresa del
propietario.
