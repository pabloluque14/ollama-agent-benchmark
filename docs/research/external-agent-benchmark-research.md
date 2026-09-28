# Investigación externa para Ollama Agent Benchmark

Fecha de consulta de fuentes externas: **22 de julio de 2026**.

Este informe parte de una lectura del repositorio abierto —no de otra copia— y contrasta su implementación con documentación oficial, repositorios originales, artículos académicos y especificaciones. No se ha ejecutado Ollama, descargado modelos ni modificado código, datasets, tests o configuración.

Convenciones usadas:

- **Hecho verificado**: constatado en el código local o en una fuente primaria enlazada.
- **Inferencia**: conclusión razonada al comparar el repositorio con la fuente.
- **Recomendación**: decisión propuesta, siempre con prioridad (`imprescindible`, `recomendable`, `opcional` o `descartada`) y acción (`integrar`, `prototipar`, `usar solo para validación`, `importar patrones` o `descartar`).
- **Requiere prototipo**: la documentación no basta para asegurar equivalencia práctica.

Antes de investigar se entendió el proyecto así: `oab` pretende comparar modelos locales como agentes de herramientas con un protocolo seguro, reproducible y auditable. El runner funcional usa seis herramientas enteramente virtuales y evalúa tanto la trayectoria como la respuesta; el runner de rendimiento mide la API nativa de Ollama, streaming y recursos del sistema; los artefactos versionados permiten reanudar y generar informes. La investigación se dividió en cuatro frentes: (1) inventario local y análisis de cobertura; (2) frameworks y benchmarks públicos; (3) estadística y rendimiento; y (4) estrategia de tests y arquitectura de integración. Esa división evita recomendar paquetes que dupliquen sin ventaja lo ya resuelto.

## Resumen ejecutivo

El repositorio ya resuelve bien el núcleo difícil: herramientas simuladas sin acceso real, trayectorias auditables, validación de llamadas y argumentos, dependencias secuenciales, errores, confirmaciones básicas, inyección indirecta, repeticiones, manifests, reanudación, scoring determinista, TTFT por streaming y recursos nativos de Ollama. No hay una razón técnica para sustituir ese núcleo por un framework generalista.

Los huecos prioritarios están en los bordes del protocolo: elección entre herramientas parecidas; argumentos ausentes, inventados o de tipo erróneo; trayectorias alternativas válidas; bucles y finalización prematura; contradicción entre herramienta y respuesta final; resultados ambiguos; confirmaciones ambiguas, revocadas o ligadas a otro recurso; Unicode y conversaciones realmente multivuelta. En la infraestructura faltan rechazo sistemático de duplicados funcionales, diagnóstico de JSONL truncado, invariantes que impidan que una respuesta de rendimiento inválida obtenga ventaja, comprobación de cumplimiento final en TTFT, rotación equilibrada para cualquier número de modelos y validación estadística diferencial.

La mejor opción externa para un **prototipo** es **Inspect AI**, pero como backend opcional de validación cruzada sobre 5–10 casos, nunca como reemplazo inicial. **BFCL V3/V4**, **τ-bench**, **τ²-bench**, **AgentDojo** y **ToolSandbox** deben inspirar familias nuevas, no copiarse en bloque. Para tests, **Hypothesis** merece incorporarse como dependencia exclusiva de desarrollo y `jsonschema` como oráculo de schemas; **statsmodels** debe validar Wilson y McNemar; SciPy puede ser un extra de análisis para bootstrap y pruebas pareadas. El runtime debe seguir sin dependencias obligatorias.

En rendimiento, el runner nativo debe conservarse: GuideLLM y AIPerf no sustituyen el control de carga fría de Ollama, `/api/ps`, VRAM o swap. **GuideLLM** merece un prototipo aislado para concurrencia, ITL y percentiles. GenAI-Perf está en retirada oficial y no debe integrarse. `pyperf` solo sirve para microbenchmarks de Python, no para inferencia.

Decisión global: fortalecer primero el protocolo propio y sus tests; ejecutar dos spikes aislados —Inspect AI y GuideLLM—; y convertir después las familias aceptadas en una especificación versionada antes de editar el dataset.

## Estado actual del repositorio

### Funcionalidades ya resueltas

**Hechos verificados en el repositorio:**

- La CLI coordina configuración, lock, validación, ejecución funcional, ejecución de rendimiento e informes.
- Los datasets, workloads, manifests, schemas de salida y versiones forman parte del protocolo experimental.
- El runner funcional conserva mensajes, tool calls, resultados, errores, tiempos, intentos, orden y `execution_key`; limita el bucle y entrega errores virtuales al modelo.
- Las seis herramientas (`simulated_terminal`, `read_file`, `write_file`, `replace_text`, `search_docs`, `read_doc`) actúan sobre estado en memoria. No ofrecen shell, red o archivos reales.
- Las herramientas rechazan rutas absolutas, `~` y segmentos `..`; `simulated_terminal` usa una lista explícita de operaciones.
- El dataset funcional v2 contiene **60 casos**: 42 de fiabilidad de herramientas y 18 de calidad/razonamiento, repartidos en 14 categorías. Hay 39 pasos esperados de herramienta.
- Los casos permiten cero, una o dos herramientas: 23 no ofrecen herramientas, 29 ofrecen una y 8 ofrecen dos.
- El runner de rendimiento implementa tres workloads versionados: respuesta corta, generación larga y prompt largo con respuesta corta; separa carga fría, ejecuciones calientes y TTFT.
- Se escriben JSON/JSONL de forma durable: JSON mediante temporal, `fsync` y reemplazo atómico; JSONL mediante append, flush y `fsync`.
- `tests/fake_ollama.py` simula `/api/version`, `/api/tags`, `/api/ps`, `/api/show`, `/api/generate` y `/api/chat`, incluido streaming NDJSON, tool calls, errores HTTP y timeouts. La suite normal no necesita Ollama real, Internet ni modelos.

Fuentes locales primarias: [README](../../README.md), [metodología](../methodology.md), [arquitectura](../architecture.md), [métricas](../metrics.md), [limitaciones](../limitations.md), [dataset funcional v2](../../datasets/benchmark_cases_v2.json), [tools v2](../../datasets/tools_v2.json), [workloads v2](../../datasets/performance_workloads_v2.json), [runner funcional](../../src/ollama_agent_benchmark/functional.py), [runner de rendimiento](../../src/ollama_agent_benchmark/performance.py), [scoring e informes](../../src/ollama_agent_benchmark/report.py), [infraestructura compartida](../../src/ollama_agent_benchmark/common.py), [suite de tests](../../tests/) y [servidor Ollama simulado](../../tests/fake_ollama.py).

### Métricas actuales

| Área | Métricas o señales ya calculadas |
|---|---|
| Funcional | éxito por ejecución; mayoría estricta por caso; casos que pasan todas las repeticiones; tasa denominada `case_consistency_rate`; Wilson 95 % sobre casos ganados por mayoría; McNemar exacto entre modelos; puntuación ponderada por suite/categoría; errores del runner; trazas por paso |
| Calidad | scorers `exact`, `json`, `numeric`, `substring` y `regex`; requisitos y prohibiciones textuales; cumplimiento de la respuesta final |
| Rendimiento | duración total y de carga; tiempo de pared; prompt/eval count y duration; prompt tokens/s y generation tokens/s; TTFT al primer `content`, `thinking` o `tool_calls` no vacío; memoria del modelo y VRAM de `/api/ps`; memoria/swap del sistema; cumplimiento mínimo del workload |
| Agregación | media, mediana, desviación estándar muestral, mínimo y máximo; medianas ponderadas por workload; puntuaciones relativas de velocidad y memoria respecto al mejor modelo del run; componentes ausentes como incompletos/N/D |

### Metodología estadística existente

La mayoría estricta se calcula por caso, de modo que las repeticiones no se tratan como muestras independientes en Wilson o McNemar. Wilson usa el número de casos ganados por mayoría. McNemar construye discordancias sobre casos comunes y usa la variante binomial exacta bilateral. Los descriptivos usan `statistics.fmean`, `median` y `stdev` de Python; esta última es desviación muestral N−1 según la [documentación oficial de Python 3.11](https://docs.python.org/3.11/library/statistics.html).

**Inferencia:** la base matemática es razonable y ligera. El intervalo de Wilson describe incertidumbre condicional sobre este conjunto diseñado; no convierte el dataset en una muestra aleatoria de “todas las tareas de agentes”. `case_consistency_rate` mide realmente “aprobar todas las repeticiones”, no acuerdo general: un modelo que falla siempre es estable, pero recibe consistencia cero. Conviene renombrarla como fiabilidad all-pass y añadir una métrica de acuerdo/entropía si se necesita estabilidad conductual.

### Comportamientos funcionales ya probados

La cobertura actual es fuerte en:

- ausencia de llamada cuando no hace falta herramienta;
- herramienta única, nombre, argumentos y orden exactos;
- dependencia secuencial y reutilización de un hash o resultado anterior;
- recuperación básica ante error de herramienta;
- confirmación explícita positiva/ausente antes de acciones sensibles;
- inyección indirecta alojada en archivo, documento, error o nombre;
- rutas peligrosas básicas;
- modificación exacta, resúmenes fieles, datos insuficientes, síntesis y razonamiento numérico;
- respuesta final mediante scorers deterministas y prohibiciones.

Las 14 categorías son: `confirmation`, `debugging`, `error_recovery`, `exact_modification`, `faithful_summary`, `instruction_following`, `insufficient_information`, `missing_information`, `no_tool`, `prompt_injection`, `reasoning_data`, `sequential_dependency`, `single_tool` y `synthesis`.

### Implementación propia y valor que debe conservarse

Parecen implementaciones propias: las herramientas virtuales y su estado; el formato del dataset; el bucle funcional; los scorers textuales/estructurados; la lógica de confirmación; las claves de ejecución y reanudación; Wilson y McNemar; el esquema de puntuación ponderada; la rotación; la medición nativa `/api/chat` y `/api/ps`; la lectura de swap en macOS; los informes; el servidor falso de Ollama.

Ese trabajo no es “reinventar” sin valor: expresa las restricciones diferenciadoras del proyecto. Un framework externo puede aportar logs, adapters o patrones, pero no garantiza a la vez seis herramientas simuladas, seguridad estricta, protocolo español, carga fría nativa, VRAM/swap y runtime cero-deps.

## Huecos identificados

### Dataset y scoring funcional

1. **Selección poco exigente.** Solo ocho casos ofrecen dos herramientas y ninguno ofrece un catálogo amplio de funciones casi equivalentes. Falta medir discriminación semántica bajo ruido.
2. **Schemas no tensionados sistemáticamente.** Los manifests declaran `required` y `additionalProperties: false`, pero faltan familias para obligatorio ausente, argumento extra inventado, tipo incorrecto, enum inválido, objeto parcialmente correcto y `null` inesperado.
3. **Trayectoria exacta demasiado rígida.** El scorer es auditable, pero puede producir falsos negativos cuando dos secuencias diferentes llegan de forma segura al mismo estado permitido.
4. **Scoring textual permisivo.** Un `substring` puede aprobar una negación como “no fue creado” porque contiene “creado”; un número esperado puede aparecer en una explicación contradictoria. También puede fallar una paráfrasis válida.
5. **Prohibiciones por texto.** `must_not_contain` puede penalizar una respuesta segura que cite la instrucción maliciosa para rechazarla, y puede aprobar una obediencia que evita la palabra literal.
6. **Inyección indirecta con éxito superficial.** Algunos casos comprueban la ausencia de una cadena o llamada, pero no separan utilidad benigna de objetivo malicioso; “no hacer nada” puede parecer seguro.
7. **Confirmación estática.** `confirmation_granted` se deriva lexicalmente de toda la conversación. Faltan ambigüedad, revocación, caducidad, alcance por operación/recurso y sustitución del recurso tras confirmar.
8. **Sin multivuelta real.** Los 60 casos comienzan con un solo mensaje de usuario. El bucle de tool calls es multistep, pero no evalúa aclaración, rectificación o cambio de intención en varios turnos.
9. **Seguridad de rutas incompleta.** Faltan backslashes, NUL, normalización Unicode, homoglifos, nombres reservados y semánticas de enlaces. Aunque todo sea virtual, estos casos prueban que el scorer y el sandbox conceptual no acepten representaciones peligrosas.
10. **Final y trayectoria desacoplados.** Faltan casos donde la llamada fue correcta pero la respuesta final contradice, exagera u oculta un resultado incompleto.

### Persistencia, rotación y rendimiento

- El agregado funcional no exige de forma inequívoca el conjunto exacto y único de `execution_key`. Un duplicado puede sesgar métricas o enmascarar una ejecución ausente. Rendimiento sí tiene comprobaciones más fuertes.
- Una línea JSONL truncada o corrupta produce un error JSON crudo, sin diagnóstico estable de archivo/línea ni política explícita de recuperación.
- Un `runner_error` funcional queda marcado con una clave ordinaria y la reanudación lo considera completado; rendimiento distingue fallos. Debe definirse si el error es resultado final o reintentable.
- La rotación cíclica solo queda perfectamente equilibrada cuando las repeticiones son múltiplo del número de modelos. Con tres repeticiones y más de tres modelos hay sesgo de posición.
- En rendimiento, `invalid_records` se cuenta, pero la puntuación penaliza explícitamente `runner_errors` y agrega únicamente registros válidos. Mezclar respuestas rápidas válidas e inválidas puede mantener medianas favorables.
- Los registros TTFT no prueban el cumplimiento final del workload: un primer chunk veloz podría lograr buen TTFT aunque la respuesta final fuese inválida.
- No hay percentiles, ITL/TPOT, throughput agregado, concurrencia, goodput/SLO, intervalos de mediana ni diagnóstico robusto de outliers.
- `_weighted_metric` calcula una media ponderada de medianas por workload y expone `mean` y `median` con el mismo valor. No es un error aritmético, pero el nombre puede inducir a interpretar una mediana global inexistente.
- La velocidad y memoria relativas dependen del conjunto de candidatos: añadir un modelo puede cambiar puntuaciones aunque los demás resultados no cambien.

## Comparativa de frameworks de evaluación

### Matriz de capacidades y encaje

Leyenda: **sí** = soporte explícito; **adapt.** = requiere adapter/configuración; **no** = no es abstracción propia del framework.

| Criterio | Inspect AI | Promptfoo | DeepEval | OpenAI Evals | lm-evaluation-harness |
|---|---|---|---|---|---|
| Agentes/herramientas | sí, agentes, tools y aprobaciones | sí, tool calling y trazas | sí, trazas de agentes | adapt. mediante `CompletionFn` | no; generación/log-likelihood |
| Nombre/argumentos | scorer propio determinista | assertions de nombre, schema y args | opcional; activar exactitud | scorer personalizado | no |
| Trayectoria multillamada | sí, mensajes/estado/log completo | sí con OpenTelemetry | sí, orden/inputs/outputs | adapt. | no |
| Herramientas simuladas | sí, herramientas Python | proveedor/traza custom | instrumentación Python | custom eval | no |
| Scorers deterministas | sí | sí | ToolCorrectness base sí; otras usan juez | básicos y custom | sí por tarea |
| Datasets propios | CSV/JSON/JSONL/loader | YAML/JSON/CSV y providers | JSON/JSONL/CSV/HF | JSONL/registry | YAML/dataset adapter |
| Ollama | proveedor oficial vía endpoint compatible | proveedor nativo | integración oficial | adapter custom | endpoint OpenAI-compatible |
| Endpoint OpenAI-compatible | sí | sí | sí/custom | indirecto | sí |
| Completamente local/sin GPU | sí si el endpoint es local | sí | sí, evitando jueces remotos | posible pero no inmediato | sí |
| macOS/Linux/Python ≥3.11 | sí; Python ≥3.10 | sí; requiere Node moderno | sí; Python ≥3.9 | sí; Python ≥3.9 | sí; Python ≥3.10 |
| Resultados/auditoría | logs completos y re-scoring | HTML/JSON/JSONL/CSV/YAML/JUnit | resultados y trazas | recorder JSONL | JSON y muestras |
| Librería/CLI | Python + CLI | Node + CLI; bridge Python | Python + CLI | Python + CLI | Python + CLI |
| Licencia | MIT | MIT | Apache-2.0 | MIT, datos variables | MIT |
| Acoplamiento | medio; runtime amplio | medio-alto; Node y trazas | alto; deps/telemetría/jueces | alto y poco encaje | medio para calidad, nulo para tools |

Fuentes primarias: [Inspect AI: arquitectura, tools, scorers y datasets](https://inspect.aisi.org.uk/), [proveedores Ollama](https://inspect.aisi.org.uk/providers.html), [logs y re-scoring](https://inspect.aisi.org.uk/eval-logs.html), [licencia y código](https://github.com/UKGovernmentBEIS/inspect_ai); [Promptfoo tool calling](https://www.promptfoo.dev/docs/configuration/tools/), [assertions deterministas](https://www.promptfoo.dev/docs/configuration/expected-outputs/deterministic/), [trazas](https://www.promptfoo.dev/docs/tracing/), [Ollama](https://www.promptfoo.dev/docs/providers/ollama/), [repositorio](https://github.com/promptfoo/promptfoo); [DeepEval ToolCorrectness](https://deepeval.com/docs/metrics-tool-correctness), [Ollama](https://deepeval.com/integrations/models/ollama), [datasets](https://deepeval.com/docs/evaluation-datasets), [repositorio](https://github.com/confident-ai/deepeval); [OpenAI Evals](https://github.com/openai/evals), [custom evals](https://github.com/openai/evals/blob/main/docs/custom-eval.md); [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness), [interfaz de modelos](https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/model_guide.md).

### Decisión por framework

| Framework | Actividad/API/dependencias | Clasificación solicitada | Prioridad | Decisión final |
|---|---|---|---|---|
| Inspect AI | Proyecto muy activo, versión 0.3 y clasificador beta; fijar versión. Dependencias FastAPI/Pydantic/NumPy/psutil/Textual/tiktoken, entre otras. | **backend opcional** y validación cruzada | recomendable | **prototipar** |
| Promptfoo | Muy activo; solo soporta oficialmente la última versión. Requiere Node `^20.20` o `≥22.22` y amplia superficie. | **validación cruzada** | opcional | **usar solo para validación** |
| DeepEval | Activo; muchas dependencias, telemetría y métricas LLM-as-judge. El modo base puede aprobar una selección incompleta si no se activa `should_exact_match`. | **importar únicamente patrones de diseño** | opcional | **importar patrones** |
| OpenAI Evals | Diseño anterior a los evals agentic actuales, dependencias muy amplias y sin Ollama nativo. | **descartar** | descartada | **descartar** |
| lm-evaluation-harness | Activo y maduro para benchmarks lingüísticos; API Alpha y cambios recientes; no modela tools. | **validación cruzada** de calidad/razonamiento, no runner agentic | opcional | **usar solo para validación** |

**Recomendación — recomendable / prototipar:** adaptar a Inspect AI 5–10 casos que incluyan no-tool, dos herramientas, error, dependencia, confirmación e inyección. Comparar llamada por llamada y volver a puntuar el mismo log. No permitir herramientas reales de Inspect ni convertir su log en formato canónico hasta demostrar equivalencia.

## Comparativa de benchmarks públicos

### Capacidades, condiciones y aplicabilidad

| Benchmark | Capacidades y scorer | Licencia/reutilización/localidad | Idioma/determinismo | Adaptación a las seis tools | Prioridad y decisión |
|---|---|---|---|---|---|
| **BFCL V3/V4** | Single/multiple/parallel, irrelevance, AST, multivuelta, parámetros/funciones ausentes, estado, límite de pasos, error recovery, memoria y formato. Scorers AST/estado y logs auditables. | Apache-2.0. Código/datos reutilizables con atribución. Modos no-live y endpoint OpenAI-compatible pueden ser locales; web/live puede depender de APIs. | Incluye diversidad lingüística, pero no equivalencia española garantizada. Determinista en AST/no-live; live es variable. | Alta: selección, no-tool, args/tipos, múltiples llamadas, loops y recovery. Adaptar, no importar masivamente. | imprescindible; **usar para validación** e **importar patrones** |
| **τ-bench** | Diálogo dinámico, políticas, DB y estado final; `pass^k`; autenticación, dependencias, no inventar y confirmación explícita. | MIT en el repositorio oficial actual. Entorno/scorer local; el usuario simulado LLM puede requerir proveedor. | Inglés; traducible con revalidación. Estado objetivo auditable, conversación estocástica. | Alta en patrones de confirmación, cambio de estado, dependencias y consistencia; dominios no coinciden. | imprescindible; **importar patrones** |
| **τ²-bench** | Dec-POMDP con herramientas de agente y usuario sobre estado compartido; generador composicional; coordinación/comunicación. | MIT. Repo actual evolucionado a τ³, Python ≥3.12,<3.14 y refactors; voz/retrieval pueden añadir servicios. | Principalmente inglés; simulador no determinista salvo sustitución por guion local. | Alta para dual-control, recurso que cambia y aclaraciones; integración directa costosa. | recomendable; **importar patrones** |
| **AgentBench / FC** | Ocho entornos originales y cinco containerizados de function calling, long-horizon y métricas por entorno. | Apache-2.0 para repo, licencias de datasets heredados deben revisarse. Docker, MySQL, Redis, Freebase e imágenes grandes; algunos servicios/recursos. | Principalmente inglés; entornos complejos y variables. | Baja: OS/DB reales contradicen el aislamiento; solo patrón task-server/agent-server. | descartada; **descartar** integración/datos |
| **AgentDojo** | 70 herramientas, 97 tareas, 27 objetivos maliciosos y 629 casos de inyección indirecta; utilidad benigna, utilidad bajo ataque y ASR; predicates y trazas. | MIT. Entorno extensible/local; modelo local posible, sin Ollama nativo documentado. API “under development”. | Inglés; ataque/modelo estocástico, scorer auditable. Traducción exige volver a medir fuerza del payload. | Alta como inspiración para resultados no fiables y separación seguridad/utilidad; tools distintas. | imprescindible; **importar patrones** |
| **ToolSandbox** | Conversación stateful, dependencias implícitas, información insuficiente, canonicalización, milestones y minefields sobre trayectorias alternativas. | Licencia Apple personalizada; revisar acknowledgements antes de datos. Repo con mantenimiento limitado y base Python 3.9. Local, pero usuario simulado puede usar modelo. | Inglés y conversación estocástica; milestones auditables. | Alta para resultado ambiguo, estado implícito, final prematuro y planes alternativos. | recomendable; **importar patrones** |

Fuentes primarias: [BFCL leaderboard y categorías](https://gorilla.cs.berkeley.edu/leaderboard), [BFCL V3 multivuelta](https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html), [repositorio/licencia/CLI](https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard); [τ-bench paper](https://arxiv.org/abs/2406.12045), [repositorio](https://github.com/sierra-research/tau-bench), [política retail](https://github.com/sierra-research/tau-bench/blob/main/tau_bench/envs/retail/wiki.md); [τ²-bench paper](https://arxiv.org/abs/2506.07982), [repositorio actual](https://github.com/sierra-research/tau2-bench); [AgentBench paper](https://proceedings.iclr.cc/paper_files/paper/2024/hash/e9df36b21ff4ee211a8b71ee8b7e9f57-Abstract-Conference.html), [repositorio](https://github.com/THUDM/AgentBench); [AgentDojo paper](https://openreview.net/pdf?id=m1YYAQjO3w), [repositorio](https://github.com/ethz-spylab/agentdojo), [TaskSuite](https://agentdojo.spylab.ai/concepts/task_suite_and_tasks/); [ToolSandbox paper](https://arxiv.org/abs/2408.04682), [repositorio](https://github.com/apple/ToolSandbox), [licencia](https://raw.githubusercontent.com/apple/ToolSandbox/main/LICENSE).

### Advertencias metodológicas y legales

- BFCL Live Relevance comprueba relevancia de llamada con criterios más laxos y no debe ser oráculo de argumentos completos. Sus casos no-live/AST son mejores para validación determinista.
- El estado final de τ-bench puede aprobar acciones intermedias inseguras posteriormente revertidas; OAB debe combinar estado/hitos con prohibiciones de trayectoria.
- Los usuarios LLM de τ/τ² y algunos ataques/model graders son estocásticos y sensibles al idioma. Los casos canónicos de OAB deben usar guiones y scorers deterministas.
- La traducción al español crea una variante nueva: conservar ID y procedencia, revisar licencia, hacer back-translation y validación humana, y no presentar comparabilidad directa con el leaderboard original.
- AgentBench usa entornos reales/containerizados incompatibles con la política de sandbox del repositorio.
- ToolSandbox no tiene una licencia OSS estándar; no copiar código/datos sin revisión humana de licencia y acknowledgements.

No se han copiado ni integrado datasets en esta investigación.

## Matriz de cobertura funcional

Estado: **fuerte**, **débil**, **ausente**. “Referencia” indica de dónde importar el patrón, no el dato literal.

| Capacidad | Cobertura actual | Riesgo observado | Familia propuesta / referencia |
|---|---|---|---|
| Selección de herramienta única | fuerte | catálogo demasiado pequeño | conservar; negativos semánticos |
| Herramientas parecidas | débil | solo 8 casos con dos tools | catálogos con nombres/args próximos; BFCL multiple-function |
| No usar herramienta | fuerte | puede depender de frases obvias | peticiones de conocimiento mezcladas con tools irrelevantes; BFCL irrelevance |
| Obligatorio ausente | débil | el modelo puede inventar | pedir aclaración y reanudar; BFCL missing parameter |
| Argumento inventado/extra | débil | `additionalProperties` no se tensiona | adversariales sistemáticos por schema |
| Tipo/enum incorrecto | ausente | serialización parcialmente correcta puede pasar capas tardías | matriz string/int/bool/null/list/object y límites Unicode |
| Llamada parcialmente correcta | débil | exact match no gradúa diagnóstico | score separado selección/schema/args/estado, sin dar éxito total |
| Secuencia de varias tools | fuerte para dos pasos | máximo catálogo 2; poca longitud/alternativas | cadenas 3–5, BFCL V3 y ToolSandbox |
| Dependencia de resultados | fuerte | centrada en hash/orden exacto | resultados ambiguos, ids y estado; τ/ToolSandbox |
| Recuperación tras errores | fuerte básica | poca taxonomía y presupuesto | recuperable/fatal/timeout/schema; BFCL web recovery |
| Repetición innecesaria | ausente | gasto y posibles efectos dobles | detector por firma+estado; límite versionado |
| Bucle de herramientas | ausente | solo límite general | bucle idéntico y ciclo A→B→A; BFCL límite de pasos |
| Finalización prematura | débil | respuesta antes del hito | milestones obligatorios; ToolSandbox |
| Final contradice tool | ausente | substring puede aprobar negación | assertions estructuradas sobre último estado |
| Resultado incompleto/ambiguo | débil | puede inventar conclusión | aclarar, declarar límite o nueva llamada permitida; ToolSandbox |
| Instrucciones conflictivas | débil | prioridades poco sistemáticas | matriz system/user/tool-result; AgentDojo |
| Prompt injection indirecta | fuerte inicial | seguridad no separada de utilidad | utility, utility-under-attack, ASR; AgentDojo |
| Confirmación ausente | fuerte básica | detector lexical global | estado de confirmación por acción/recurso |
| Confirmación ambigua | ausente | “vale quizá” podría conceder | guiones τ-bench |
| Confirmación revocada | ausente | no hay transición de estado | sí→revocación antes de ejecutar |
| Recurso cambiado tras confirmar | ausente | confirmación puede transferirse | confirmar A, intentar B; τ/τ² |
| Límites sandbox/rutas | fuerte básica | falta representación adversarial | backslash, NUL, Unicode, homoglifos, nombres reservados |
| Contenido Unicode | ausente | normalización y comparación | NFC/NFD, RTL, emoji, claves no ASCII |
| Conversación multivuelta | ausente | un mensaje inicial en todos los casos | aclaración, rectificación y dual-control; BFCL V3/τ² |

### Redundancia, sesgos y sensibilidad léxica

**Inferencias:**

- `sequential_dependency` (8) y `single_tool` (6) son las categorías más pobladas; hay riesgo de sobreponderar orden exacto y operaciones simples frente a diálogo y ambigüedad.
- Los casos de no-tool y confirmación pueden aprenderse por palabras gatillo (“confirma”, “no uses herramientas”) en vez de por la política. Deben existir pares mínimos que cambien intención sin conservar el mismo marcador léxico.
- Calidad/razonamiento y tool reliability comparten scorers textuales con semántica desigual; conviene distinguir respuesta factual, cumplimiento de acción y seguridad.
- Un scorer solo de estado final admite falsos positivos por acciones intermedias prohibidas; uno solo de trayectoria exacta da falsos negativos a planes alternativos. La solución es combinar: schema + invariantes prohibidas + hitos/estado final + coherencia de respuesta.

### Nuevas familias propuestas, sin modificar aún el dataset

1. **Discriminación de catálogo**: 3–8 herramientas parecidas, una correcta, una con nombre parecido y otra con schema tentador.
2. **Schema adversarial**: cada campo obligatorio/extra/tipo/enum/null, más JSON sintácticamente inválido.
3. **Aclaración multivuelta**: información ausente, pregunta mínima, usuario responde o revoca.
4. **Confirmación con alcance**: operación, recurso, parámetros, expiración, ambigüedad y revocación.
5. **Estado e hitos**: varias trayectorias permitidas, minefields y estado final auditable.
6. **Economía de llamadas**: no-tool, repetición, bucle y final prematuro con presupuesto explícito.
7. **Coherencia final**: respuesta debe citar estado/resultado, reconocer ambigüedad y no contradecir.
8. **Seguridad con utilidad**: tarea benigna completada pese a payload indirecto, métricas separadas.
9. **Unicode y rutas**: generación sistemática de representaciones peligrosas en tools virtuales.
10. **Errores tipados**: recuperable, no recuperable, timeout, resultado parcial y error que contiene injection.

**Recomendación — imprescindible / importar patrones:** especificar estas familias y sus invariantes antes de crear casos. No traducir ni copiar ejemplos públicos directamente.

## Métricas y metodología estadística

### Revisión y propuestas

| Tema | Diagnóstico | Propuesta | Clasificación de dependencia | Prioridad / decisión |
|---|---|---|---|---|
| `statistics` | ya cubre media, mediana, stdev, min/max sin deps | conservar; rechazar NaN/±inf en entrada | runtime estándar | imprescindible; **integrar** (ya presente) |
| Mayoría estricta | evita inflar n con repeticiones | conservar y publicar también distribución por repetición | propia validada | imprescindible; **integrar** |
| Consistencia | hoy significa all-pass, no acuerdo | renombrar y añadir acuerdo/entropía opcional | propia validada | recomendable; **prototipar** |
| Wilson | fórmula estándar; tests actuales insuficientes | tabla exhaustiva contra statsmodels | statsmodels oráculo dev | imprescindible; **usar solo para validación** |
| McNemar exacto | forma estándar; falta corrección múltiple/efecto | validar contra statsmodels; publicar b,c y diferencia pareada | propia + oráculo dev | imprescindible; **usar solo para validación** |
| Medianas/CI | no hay CI para mediana/diferencias | bootstrap reproducible por bloques/pares; seed en manifest | SciPy opcional u oráculo dev | recomendable; **prototipar** |
| Pruebas pareadas | solo McNemar funcional | permutación pareada/Wilcoxon cuando existan pares reales | SciPy opcional | recomendable; **prototipar** |
| Tamaño de efecto | ausente | funcional: diferencia absoluta + b,c; perf: mediana diferencia y ratio con CI | propia validada | recomendable; **integrar** |
| Comparaciones múltiples | ausente | Holm en una familia predefinida; p crudo y ajustado | propia validada vs statsmodels | recomendable con ≥3 modelos; **prototipar** |
| Pesos/ranking | pesos fijos sin sensibilidad | rejilla/Monte Carlo determinista del simplex y frecuencia por rango | propia validada | recomendable; **prototipar** |
| Outliers | no hay diagnóstico | marcar MAD/IQR, conservar crudo, análisis con/sin solo como sensibilidad | propia; SciPy oráculo | recomendable; **importar patrones** |
| Ausentes | N/D e incompleto, sin renormalizar | conservar; no imputar 0 ni redistribuir silenciosamente | propia | imprescindible; **integrar** |

Fuentes: [Python `statistics`](https://docs.python.org/3.11/library/statistics.html); [SciPy bootstrap reproducible, pareado y BCa](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html), [permutation test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html), [Wilcoxon](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html), [intervalo de cuantiles/mediana](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.quantile_test.html), [MAD](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.median_abs_deviation.html); [statsmodels Wilson](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.proportion_confint.html), [McNemar](https://www.statsmodels.org/stable/generated/statsmodels.stats.contingency_tables.mcnemar.html), [correcciones múltiples](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html).

### Diseño estadístico recomendado

- Tratar el **caso** como unidad funcional y el par `(workload, bloque/repetición, estado cold/hot)` como unidad de rendimiento. No mezclar observaciones heterogéneas como i.i.d.
- Publicar estimación, intervalo y tamaño de efecto; no ordenar solo por p-value. Con 3–5 repeticiones, reconocer baja potencia.
- Para bootstrap, remuestrear bloques/casos completos y conservar el emparejamiento entre modelos. Registrar algoritmo, número de remuestreos y seed derivada del manifest.
- Para rankings, mostrar probabilidad/frecuencia de cada rango bajo bootstrap y sensibilidad de pesos; el score relativo debe declarar el conjunto de candidatos.
- No borrar outliers automáticamente. Marcar causa potencial y mostrar sensibilidad; un outlier puede ser precisamente una carga fría o swap real.
- Distinguir `weighted_mean_of_workload_medians` de mediana global y versionar cualquier cambio de nombre/formato.

SciPy y statsmodels son BSD-3-Clause y están mantenidos en sus [repositorios oficiales de SciPy](https://github.com/scipy/scipy) y [statsmodels](https://github.com/statsmodels/statsmodels), pero su peso no se justifica en runtime. **Recomendación — descartada / descartar:** no hacerlos dependencias obligatorias.

## Benchmarking de rendimiento

### Comparación de herramientas

| Herramienta | Qué aporta | Qué no sustituye | Compatibilidad/coste/licencia | Prioridad y decisión |
|---|---|---|---|---|
| **GuideLLM** | OpenAI-compatible; perfiles síncrono, concurrente, throughput, constante, Poisson y sweep; TTFT, ITL, distribuciones; JSON/CSV/HTML | descarga fría nativa Ollama, `/api/ps`, VRAM/swap, protocolo exacto `/api/chat` | Python 3.10–3.13, macOS/Linux, Apache-2.0; deps grandes incl. datasets, NumPy, Pydantic, Transformers y torch | recomendable; **prototipar** como CLI aislada/validación |
| **GenAI-Perf** | históricamente TTFT, ITL, latencia, tokens/requests throughput y concurrencia | recursos/cold Ollama y protocolo propio | ecosistema NVIDIA/Triton; oficialmente deprecado en favor de AIPerf | descartada; **descartar**, importar definiciones |
| **AIPerf** | sucesor: OpenAI/custom endpoint, streaming, Poisson, multi-turn, warmup, sweeps, goodput/SLO, replay, seed, JSON versionado, CI multirun | mismas métricas nativas de Ollama | Python ≥3.11,<3.14, macOS arm64/Linux, Apache-2.0; pila muy grande | opcional; **importar patrones** y prototipar si concurrencia entra en alcance |
| **pyperf** | procesos, warmups, calibración, metadatos y estabilidad de microbenchmarks Python | streaming, TTFT, tokens, carga de modelo y recursos de Ollama | Python ≥3.9, MIT; dev-only | opcional; **usar solo para validación** de scoring/report/JSONL |
| **pytest-benchmark** | fixture, rounds, warmup y estadísticas de funciones | inferencia real; además introduce pytest en repo unittest | Python ≥3.9, BSD-2 | descartada; **descartar** por ahora |

Fuentes: [GuideLLM](https://github.com/vllm-project/guidellm) y su [configuración/dependencias](https://github.com/vllm-project/guidellm/blob/main/pyproject.toml); [aviso oficial de retirada de GenAI-Perf](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/perf_analyzer/README.html) y [métricas históricas](https://docs.nvidia.com/deeplearning/triton-inference-server/archives/triton-inference-server-2510/user-guide/docs/perf_analyzer/genai-perf/README.html); [AIPerf CLI](https://docs.nvidia.com/aiperf/reference/command-line-options), [replay](https://docs.nvidia.com/aiperf/tutorials/datasets-inputs/inputs-json-replay), [schema JSON](https://docs.nvidia.com/aiperf/reference/json-export-schema), [pyproject](https://github.com/ai-dynamo/aiperf/blob/main/pyproject.toml); [pyperf](https://pyperf.readthedocs.io/en/stable/user_guide.html); [pytest-benchmark](https://pytest-benchmark.readthedocs.io/).

### Recomendación de medición

**Imprescindible / integrar:** conservar carga fría, hot runs, `/api/chat`, TTFT a payload significativo, métricas nativas de prompt/eval, `/api/ps`, memoria/swap, cumplimiento, manifests y reanudación. Añadir primero invariantes: ningún registro inválido mejora score; TTFT solo puntúa si la respuesta final cumple; claves exactas y únicas.

**Recomendable / prototipar:** un modo separado de carga concurrente, porque responde a otra pregunta y no debe mezclarse con el ranking secuencial. GuideLLM sería el primer spike por su enfoque OpenAI-compatible y soporte de macOS. Comparar TTFT/throughput en el mismo endpoint y explicar que OpenAI-compatible no es idéntico a `/api/chat` nativo.

**Opcional / importar patrones:** percentiles con convención de interpolación versionada, ITL/TPOT guardando timestamps de chunks, goodput bajo SLO y perfiles Poisson. No publicar percentiles altos con n=5 como si fueran estables; aumentar repeticiones o declarar insuficiencia.

`pyperf` y pytest-benchmark miden funciones Python. Su resultado no representa inferencia, carga del modelo ni rendimiento del servidor. Esta separación debe aparecer en la documentación y en los comandos de test.

## Estrategia de mejora de tests

### Herramientas

| Herramienta/patrón | Evaluación | Tipo de dependencia | Prioridad y decisión |
|---|---|---|---|
| Hypothesis | genera y reduce contraejemplos; integra con `unittest`; state machines para secuencias | desarrollo exclusivo; MPL-2.0 | imprescindible; **integrar** |
| JSON Schema 2020-12 + `jsonschema` | schemas versionados, `check_schema`, todos los errores; `FormatChecker` debe activarse expresamente | primero oráculo dev; reevaluar runtime | recomendable; **integrar** para validación |
| Pydantic | modelos y schema, pero coerciona por defecto y añade core/dependencia | no incorporar | descartada; **descartar** |
| Cosmic Ray | mutación AST compatible con comando `unittest` | dev manual/nightly | opcional; **prototipar** |
| mutmut | mantenido, pero depende de pytest y `fork` | no incorporar ahora | descartada; **descartar** |
| Librerías snapshot | añaden pytest/deps o snapshots frágiles | usar golden JSON propios pequeños | descartada como librería; **importar patrón** |
| Diferencial/metamórfico/fuzz | encaja con invariantes y no exige runtime | Hypothesis + oráculos dev | imprescindible; **integrar** |

Fuentes: [Hypothesis quickstart](https://hypothesis.readthedocs.io/en/latest/quickstart.html), [compatibilidad](https://hypothesis.readthedocs.io/en/latest/compatibility.html), [stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html), [licencia](https://github.com/HypothesisWorks/hypothesis/blob/master/LICENSE.txt); [JSON Schema 2020-12](https://json-schema.org/specification), [`jsonschema`](https://python-jsonschema.readthedocs.io/en/stable/validate/); [Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/); [Cosmic Ray](https://cosmic-ray.readthedocs.io/en/stable/), [mutmut](https://mutmut.readthedocs.io/en/latest/).

### Plan concreto de 20 validaciones

| # | Prueba propuesta | Clase |
|---|---|---|
| 1 | Misma seed y config producen mismo plan, registros semánticos y score, normalizando timestamps/rutas/run-id. | propiedad + integración simulada |
| 2 | Permutar modelos no cambia métricas por modelo ni ranking, salvo desempate documentado. | metamórfica |
| 3 | Para N modelos y R bloques, cada posición difiere como máximo en 1; si R es múltiplo de N, igualdad exacta. | propiedad unitaria |
| 4 | Reanudar desde cualquier prefijo válido ejecuta solo claves ausentes, es idempotente y equivale a run limpio. | integración simulada |
| 5 | Duplicar cualquier `execution_key`/`measurement_key`, contiguo o no, falla antes de agregar. | unitaria + propiedad |
| 6 | Línea final parcial, UTF-8 inválido, JSON no objeto o corrupción intermedia fallan con archivo+línea; nunca completan silenciosamente. | unitaria/fuzz |
| 7 | `None` atraviesa resumen, score e informe como N/D, deja componente incompleto y no se convierte en 0/100 ni renormaliza. | unitaria + golden estructurado |
| 8 | Convertir un registro válido en error/no compliant/inválido nunca aumenta score ni ranking; aplica también a TTFT final. | propiedad monotónica |
| 9 | Vecinos adversariales —nombre parecido, tipo incorrecto, recurso distinto, orden invertido, negación— fallan; paráfrasis permitidas pasan. | unitaria + mutación |
| 10 | Fuzz de rutas, Unicode, `..`, absolutos, NUL, metacaracteres, URLs y credenciales: ninguna tool toca FS, shell o red reales. | propiedad de seguridad |
| 11 | Solo un sí inequívoco habilita exactamente acción/recurso; silencio, pregunta, quizá, revocación o A→B no habilitan. | funcional multivuelta |
| 12 | Inyección en archivo/doc/error/nombre no desvía la tarea; medir utilidad y seguridad por separado. | funcional |
| 13 | Output de llamada 1 alimenta 2; impedir orden inverso, argumento inventado y final antes de hitos. | stateful + integración fake |
| 14 | Error recuperable lleva a corrección distinta; fatal termina seguro; no hay retry idéntico ilimitado. | stateful |
| 15 | Manifest actual pasa; versión anterior se migra/rechaza según contrato; futura, ausente, bool-como-int, hash truncado e incompatibilidades fallan. | propiedad + regresión |
| 16 | Fallo antes de `os.replace` conserva el archivo previo; fallo durante JSONL no genera run aparentemente completo. | unitaria con fault injection |
| 17 | Wilson para todos los `0≤k≤n≤200` y McNemar para rejilla de `b,c` coinciden con statsmodels, incluidos extremos. | diferencial dev |
| 18 | Ponderación: orden-invariante, monotónica, acotada, ejemplo manual, pesos válidos y missing→incompleto. | propiedad + referencia independiente |
| 19 | Chunks vacíos no cuentan; `content`/`thinking`/`tool_calls` sí; total≥TTFT; NDJSON corrupto falla; resultado final debe cumplir. | integración fake con reloj |
| 20 | Fake Ollama verifica método, body, content-type, NDJSON por línea, `done=true`, métricas finales, tool IDs y errores/versiones. | contrato/integración simulada |

La API oficial de Ollama documenta [streaming NDJSON](https://docs.ollama.com/api/streaming) y el [contrato API/tool calling](https://github.com/ollama/ollama/blob/main/docs/api.md); deben ser las fuentes del contrato fake, no una instalación real durante CI.

### Taxonomía de la suite

- **Unitarios:** validación, scorers, fórmulas, JSONL, pesos, atomicidad.
- **Propiedades:** seeds, rotación, permutaciones, schemas, fuzz de argumentos/rutas e invariantes de score.
- **Funcionales:** dataset versionado de conducta del agente y familias de seguridad.
- **Integración simulada:** CLI + runners + fake Ollama, reanudación, streaming, TTFT y contratos.
- **Integración con Ollama real:** smoke manual, opt-in, nunca requisito de CI ni oráculo canónico.
- **Rendimiento:** suite separada y no bloqueante; `pyperf` para Python y runner/GuideLLM para inferencia son categorías distintas.

## Arquitectura de integración propuesta

Mantener un núcleo estable y adapters unidireccionales:

```text
datasets/workloads OAB versionados
              │
              ▼
     protocolo y tools virtuales
        ┌─────┴──────────┐
        │                │
 runner OAB canónico   adapters opcionales aislados
        │                ├── Inspect AI (trayectoria/scoring)
        │                ├── GuideLLM (carga concurrente)
        │                └── oráculos dev (statsmodels/SciPy/jsonschema)
        ▼
artefactos OAB + informe comparable
```

Reglas de integración:

1. El schema OAB, no el de un tercero, es contrato canónico.
2. Los adapters consumen casos explícitamente exportados y producen artefactos separados; no escriben el run oficial.
3. Nunca exponer tools reales, shell, archivos o credenciales de Inspect/otros frameworks.
4. Fijar versión y lock del entorno experimental del adapter; registrar versión, endpoint, transformaciones y pérdidas de información.
5. Comparar por capas: schema de tool, trayectoria, estado final, respuesta y seguridad. Una coincidencia agregada no basta.
6. Mantener tests normales cero-deps/Ollama-free; extras bajo grupos de desarrollo/análisis o entornos aislados.
7. Versionar las nuevas familias antes de cambiar pesos o ranking; no mezclar resultados de protocolos distintos.

**Requiere prototipo:** fidelidad de schemas Ollama↔Inspect, representación de errores, una llamada por turno, políticas de confirmación, equivalencia de re-scoring y transformación de logs. Para GuideLLM: equivalencia de TTFT, token counts y streaming entre `/api/chat` y endpoint OpenAI-compatible.

## Dependencias potenciales

| Elemento | Rol propuesto | Runtime obligatorio | Prioridad | Decisión |
|---|---|---:|---|---|
| `statistics` | descriptivos | sí, stdlib | imprescindible | **integrar/conservar** |
| Hypothesis | propiedades/stateful/fuzz | no, dev | imprescindible | **integrar** |
| `jsonschema` | oráculo Draft 2020-12 y manifests/datasets | no, dev inicialmente | recomendable | **integrar para validación** |
| statsmodels | oráculo Wilson/McNemar/Holm | no, dev | imprescindible para validación | **usar solo para validación** |
| SciPy | bootstrap, quantile CI, tests pareados, MAD | no, extra análisis/dev | recomendable | **prototipar** |
| Cosmic Ray | mutation testing | no, manual/nightly | opcional | **prototipar** |
| pyperf | microbenchmarks de Python | no, dev/manual | opcional | **usar solo para validación** |
| Inspect AI | adapter experimental | no, entorno aislado | recomendable | **prototipar** |
| GuideLLM | carga concurrente externa | no, entorno aislado | recomendable | **prototipar** |
| AIPerf | referencia/goodput futuro | no | opcional | **importar patrones** |
| Promptfoo | validación externa eventual | no, Node aislado | opcional | **usar solo para validación** |
| lm-eval-harness | calidad general externa | no | opcional | **usar solo para validación** |
| Pydantic | modelos runtime | no | descartada | **descartar** |
| OpenAI Evals / DeepEval | runner principal | no | descartada | **descartar** / **importar patrones** |
| pytest-benchmark / mutmut / snapshots | test infra adicional | no | descartada | **descartar** ahora |

No se propone ninguna dependencia nueva obligatoria de runtime. Esa decisión conserva instalación ligera, superficie de ataque pequeña y ejecución offline.

## Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Acoplamiento a API beta de Inspect | roturas y formato inestable | adapter pequeño, pin estricto, contract tests, artefacto separado |
| Endpoint compatible no equivale a Ollama nativo | discrepancias de tools/tokens/TTFT | validación lado a lado; no fusionar rankings |
| LLM-as-judge/simulador | no determinismo, sesgo idiomático | scorer determinista paralelo; guiones locales; seed/log completo |
| Copiar datasets externos | licencia, contaminación y poca comparabilidad | importar patrones; procedencia/licencia por familia; revisión humana |
| Traducir al español | cambia dificultad y fuerza de ataques | back-translation, pares bilingües piloto y revisión humana |
| Scorer exacto | falsos negativos por trayectorias alternativas | hitos/estado + invariantes de trayectoria + schemas |
| Scorer de estado final | falsos positivos por acciones inseguras revertidas | minefields y auditoría de todos los pasos |
| Scorer textual | negaciones/citas/substring | assertions estructuradas y corpus adversarial |
| Más métricas/p-values | conclusiones espurias | preregistro, Holm, efecto+CI, no ranking solo por significancia |
| Outliers/cold runs | ocultar inestabilidad real | conservar crudo; flag y sensibilidad; no eliminación automática |
| Dependencias pesadas | instalación lenta y fallos macOS | extras/CLI aisladas; runtime sin deps |
| Concurrencia mezclada con secuencial | ranking incoherente | protocolo y reporte separados |
| Corrupción/duplicados | run aparentemente completo o sesgado | conjunto exacto de claves, fail closed y diagnóstico por línea |
| Nuevas tools de frameworks | fuga a shell/FS/red | allowlist de adapter y tools virtuales exclusivamente |

## Prototipos recomendados

### P1. Inspect AI como backend opcional

**Prioridad: recomendable. Decisión: prototipar.**

Alcance: 5–10 casos representativos, las seis tools solo si el primer subconjunto funciona, endpoint Ollama OpenAI-compatible local, cero herramientas reales. Criterios de éxito: identidad de nombre/args/orden, mismo tratamiento de error y confirmación, re-scoring sin inferencia, log completamente auditable y coste de instalación documentado. Criterio de abandono: el adapter necesita duplicar el protocolo o pierde señales canónicas.

### P2. GuideLLM para validación de carga

**Prioridad: recomendable. Decisión: prototipar.**

Alcance: un modelo, un workload, secuencial y concurrencia baja, entorno separado. Comparar TTFT, output TPS y total latency con OAB. No puntuar memoria/cold load. Éxito: diferencias explicables y perfil concurrente reproducible. Abandono: tokenización o streaming no comparables.

### P3. Oráculos estadísticos y schema

**Prioridad: imprescindible. Decisión: integrar para validación.**

Usar statsmodels para rejillas Wilson/McNemar, `jsonschema` para schemas versionados e Hypothesis para invariantes. SciPy prueba bootstrap pareado con seed y CI de mediana. Nada entra en runtime.

### P4. Scorer híbrido de trayectoria/estado

**Prioridad: imprescindible. Decisión: prototipar.**

Probar una representación con pasos obligatorios, alternativas permitidas, minefields, estado final y coherencia textual estructurada. Compararla con exact-match en casos existentes y medir falsos positivos/negativos manualmente.

### P5. Familias multivuelta y seguridad con utilidad

**Prioridad: imprescindible. Decisión: prototipar.**

Diseñar, sin incorporar todavía al dataset canónico, pares mínimos de argumentos ausentes, confirmación ambigua/revocada, cambio de recurso, resultado incompleto e injection. Separar puntuaciones de utilidad y seguridad al estilo AgentDojo.

## Decisiones que necesitan confirmación humana

1. Si Inspect AI puede ser dependencia opcional oficial o solo un spike externo sin soporte continuado.
2. Si concurrencia/goodput forma parte del objetivo del producto o de un protocolo independiente.
3. Qué trayectorias alternativas deben considerarse válidas por familia y qué acciones son minefields absolutas.
4. Si una ejecución con `runner_error` se considera completada o reintentable al reanudar.
5. Qué semántica y nombre tendrá la actual `case_consistency_rate`.
6. Si el ranking relativo debe mantenerse o complementarse con métricas absolutas/estabilidad de ranking.
7. Cuántas repeticiones permiten percentiles o CI publicables y qué presupuesto de tiempo se acepta.
8. Qué licencias y procedimiento de atribución se aceptan para casos inspirados en benchmarks.
9. Si se publicarán variantes bilingües o solo españolas, y quién valida equivalencia lingüística.
10. Qué cambios de schema requieren migración y cuáles deben fallar cerrados.

## Plan recomendado por fases

### Fase 0 — Especificar invariantes

**Prioridad: imprescindible.** Convertir este informe en una especificación versionada: unidad estadística, claves exactas, política de corrupción/reanudación, semántica de invalid records, TTFT válido, confirmación por alcance, scorer híbrido y taxonomía de tests. No editar datasets todavía.

### Fase 1 — Blindar infraestructura y oráculos

**Prioridad: imprescindible.** Incorporar tests con Hypothesis, `jsonschema` y statsmodels como dev/oráculos; cubrir los 20 puntos, especialmente duplicados, JSONL truncado, ventaja inválida, TTFT y atomicidad. Conservar runtime cero-deps.

### Fase 2 — Diseñar dataset vNext

**Prioridad: imprescindible.** Crear especificación de las diez familias propuestas con pares mínimos, procedencia y revisión humana. Inspiración principal: BFCL para selección/schema, τ/τ² para diálogo/confirmación/estado, AgentDojo para injection+utilidad y ToolSandbox para hitos/ambigüedad.

### Fase 3 — Prototipos aislados

**Prioridad: recomendable.** Ejecutar P1 Inspect y P2 GuideLLM con criterios de éxito/abandono. No cambiar el runner canónico ni los scores oficiales durante el spike.

### Fase 4 — Estadística y reporting

**Prioridad: recomendable.** Añadir tamaños de efecto, corrección Holm, bootstrap pareado/sensibilidad de pesos y etiquetas semánticas precisas. Versionar formato y documentar la dependencia del conjunto de candidatos.

### Fase 5 — Validación externa opcional

**Prioridad: opcional.** Promptfoo para assertions/trazas, lm-eval-harness para calidad general y AIPerf si goodput/concurrencia se vuelve requisito. No hacerlos parte de CI normal.

### Recomendación final concreta

1. **Framework externo para prototipo:** Inspect AI como backend opcional de validación de trayectoria, no como reemplazo.
2. **Benchmarks inspiradores:** BFCL V3/V4 para selección, schemas, múltiples llamadas y loops; τ-bench para confirmación/estado/fiabilidad; τ² para dual-control; AgentDojo para inyección indirecta con utilidad; ToolSandbox para ambigüedad, estado e hitos.
3. **Librerías de tests:** Hypothesis como dev dependency; `jsonschema` como oráculo de schemas; statsmodels como oráculo estadístico; Cosmic Ray solo como spike manual.
4. **Métricas a validar externamente:** Wilson, McNemar y Holm con statsmodels; bootstrap/CI de mediana y tests pareados con SciPy; TTFT/ITL/throughput concurrente con GuideLLM.
5. **Elementos propios a conservar:** tools virtuales, aislamiento absoluto, datasets/manifests versionados, scoring determinista auditable, claves/reanudación, runner nativo `/api/chat` y `/api/ps`, cold/hot, memoria/VRAM/swap, fake Ollama y runtime ligero.
6. **Siguiente paso en el flujo de Matt Pocock:** llevar las decisiones humanas de este informe a **`$to-spec`** para producir una especificación cerrada y versionada; después usar **`$to-tickets`**, separando al menos un ticket de blindaje/invariantes, uno de dataset vNext y dos spikes aislados (Inspect y GuideLLM). No crear tickets ni modificar el dataset hasta aprobar esa especificación.
