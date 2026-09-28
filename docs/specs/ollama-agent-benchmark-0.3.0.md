# Especificación técnica de Ollama Agent Benchmark 0.3.0

Estado: **lista para descomposición en tickets**

Benchmark: **`0.3.0`**

Schema principal: **`3`**

Alcance: **blindaje interno del protocolo existente**

Esta especificación sintetiza las decisiones aprobadas durante `grill-with-docs`, el lenguaje de
[CONTEXT.md](../../CONTEXT.md), los [ADR](../adr/), la
[investigación externa](../research/external-agent-benchmark-research.md) y el comportamiento
actual documentado e implementado por el repositorio.

## 1. Resumen ejecutivo

Ollama Agent Benchmark `0.3.0` hará que un run sea reconstruible, verificable y resistente a datos
ambiguos sin ampliar lo que el benchmark mide. La versión introduce un plan del run materializado
e inmutable, un calendario equilibrado por bloque experimental, un conjunto exacto de claves
esperadas, persistencia y lectura fail-closed, reanudación idempotente y una separación normativa
entre fallos de ejecución medidos y fallos de integridad del benchmark.

El rendimiento se agregará con completitud estricta por celda. Una muestra inválida nunca podrá
mejorar una métrica: la celda será `N/D`, no se recalculará con el subconjunto válido y un componente
requerido incompleto impedirá el ranking global. El TTFT solo será oficial cuando el stream completo
sea válido, reconstruible y cumpla el workload.

El plan, los registros primarios y el diario de integridad serán la evidencia canónica. Informes,
resúmenes y puntuaciones serán artefactos derivados regenerables. Los contratos se formalizarán
mediante JSON Schema local, mientras el runtime conservará validadores propios y
`dependencies = []`. Hypothesis, `jsonschema`, statsmodels y Cosmic Ray se limitarán a desarrollo.

Los modos `dry-run`, `smoke`, `official-functional` y `official-performance`, junto con cualquier
override efectivo que altere repeticiones, workloads, mediciones o claves esperadas, quedarán
fijados por el plan. Solo los modos `official-*` producirán evidencia canónica elegible para
informes y rankings oficiales.

`0.3.0` utilizará `schema_version: 3`. Los runs `0.2.0` no podrán reanudarse, mezclarse, migrarse ni
reinterpretarse silenciosamente bajo el protocolo nuevo.

## 2. Problem Statement — situación actual y problemas confirmados

La versión `0.2.0` ya proporciona herramientas virtuales seguras, runners funcional y de
rendimiento, scoring determinista, manifests, reanudación, TTFT, métricas de Ollama, Wilson,
McNemar, informes y un servidor Ollama simulado. Su runtime no tiene dependencias externas y la
suite normal no necesita red, GPU, modelos ni una instalación real de Ollama.

La inspección del código actual confirmó los siguientes problemas:

1. El runner funcional reduce las claves existentes a un conjunto; el informe comprueba el número
   de registros, pero no el conjunto exacto. Un duplicado puede ocultar una ausencia.
2. La lectura JSONL delega directamente en el parser JSON y no ofrece una política uniforme con
   archivo, línea, posición y clasificación del defecto.
3. Los runners no comparten una semántica completa para errores, claves completadas y reanudación.
4. `runner_error` puede mezclar fallos atribuibles al sistema evaluado con defectos del harness.
5. La rotación parte del orden configurado y no garantiza el equilibrio aprobado dentro de cada
   caso o cada combinación workload/tipo.
6. Rendimiento excluye registros incumplidores de los agregados. Si quedan muestras válidas, una
   respuesta inválida puede no perjudicar la mediana e incluso eliminar una observación lenta.
7. TTFT mide el primer payload, pero no reconstruye ni valida la respuesta streaming completa con
   las mismas reglas del workload no streaming.
8. El informe consume al menos un resumen persistido en lugar de reconstruir siempre desde la
   evidencia primaria.
9. Los contratos son validaciones propias parciales; no existen schemas formales ni un corpus
   diferencial independiente.
10. Los tests actuales son principalmente ejemplos concretos. Faltan propiedades sistemáticas de
    claves, planificación, reanudación, monotonicidad, serialización y equivalencia de validadores.

Fuentes locales principales: [arquitectura](../architecture.md),
[metodología](../methodology.md), [métricas](../metrics.md),
[limitaciones](../limitations.md), [runner funcional](../../src/ollama_agent_benchmark/functional.py),
[runner de rendimiento](../../src/ollama_agent_benchmark/performance.py),
[informes](../../src/ollama_agent_benchmark/report.py),
[infraestructura común](../../src/ollama_agent_benchmark/common.py) y [tests](../../tests/).

## 3. Solution — objetivos

### 3.1 Objetivo principal

Aumentar la confianza, reproducibilidad y auditabilidad del protocolo actual antes de ampliar el
dataset o incorporar frameworks externos.

### 3.2 Objetivos específicos

- Fijar antes de medir todo dato que pueda cambiar ejecución o interpretación.
- Hacer exactas y verificables la completitud, elegibilidad e idempotencia.
- Evitar que corrupción, duplicados, respuestas inválidas o datos ausentes produzcan ventaja.
- Separar los fallos medidos de los defectos del benchmark.
- Reconstruir cualquier resultado oficial desde evidencia canónica.
- Formalizar contratos sin aumentar las dependencias del runtime.
- Probar invariantes con oráculos independientes y sin Ollama real.

### 3.3 Principios normativos

Las palabras **DEBE**, **NO DEBE**, **DEBERÍA** y **PUEDE** expresan obligación, prohibición,
recomendación y posibilidad respectivamente. Todos los requisitos `REQ-*` son obligatorios salvo
que su campo `Tipo` indique expresamente recomendación o detalle delegable.

## 4. User Stories

1. Como operador, quiero materializar el plan completo antes de medir, para saber exactamente qué
   experimento estoy ejecutando.
2. Como operador, quiero reanudar un run sin repetir claves, para no seleccionar resultados
   favorables ni desperdiciar inferencia.
3. Como auditor, quiero reconstruir el conjunto esperado de claves, para detectar ausencias,
   duplicados y registros inesperados.
4. Como auditor, quiero que la corrupción falle de forma explícita, para no confundir datos
   recuperados parcialmente con resultados oficiales.
5. Como evaluador de modelos, quiero distinguir un fallo de Ollama de un defecto del harness, para
   no penalizar al modelo por errores del benchmark.
6. Como evaluador de modelos, quiero que las muestras inválidas no mejoren el rendimiento oficial,
   para evitar rankings sesgados.
7. Como evaluador de modelos, quiero que TTFT dependa de una respuesta completa y válida, para no
   premiar respuestas rápidas pero inútiles.
8. Como mantenedor, quiero regenerar informes desde registros primarios, para que una caché obsoleta
   no cambie el resultado.
9. Como mantenedor, quiero contratos formales y offline, para revisar los formatos sin depender de
   servicios externos.
10. Como usuario, quiero conservar un runtime sin dependencias externas, para instalar y ejecutar
    el benchmark de forma ligera.
11. Como contribuidor, quiero propiedades generativas rápidas, para descubrir casos límite que las
    pruebas de ejemplos no cubren.
12. Como contribuidor, quiero comparar validadores y fórmulas con oráculos independientes, para
    detectar errores conceptuales compartidos.
13. Como investigador, quiero un calendario equilibrado y registrado, para limitar el sesgo de
    posición sin aumentar repeticiones.
14. Como usuario de resultados históricos, quiero un rechazo explícito de protocolos
    incompatibles, para no mezclar `0.2.0` y `0.3.0` accidentalmente.
15. Como responsable de seguridad, quiero que los tests sigan usando herramientas virtuales y fake
    Ollama, para que CI nunca exponga shell, archivos, credenciales o modelos reales.

## 5. Out of Scope — fuera de alcance

`0.3.0` NO incluirá:

- nuevos casos funcionales, datasets externos o familias de benchmark;
- nuevos scorers o cambios en los scorers funcionales existentes;
- nuevos tipos de herramientas virtuales;
- cambios en la semántica de confirmaciones;
- Inspect AI o GuideLLM, ni siquiera como prototipos de esta versión;
- concurrencia, throughput, ITL, goodput o percentiles nuevos;
- métricas estadísticas oficiales nuevas, Holm, bootstrap o tamaños de efecto;
- cambios de pesos, normalización o ranking destinados a alterar la clasificación;
- reparación automática o best-effort de runs;
- migración de resultados `0.2.0`;
- Ollama real, modelos reales, Internet o GPU como requisitos de tests o CI;
- equilibrio completo de parejas de precedencia u optimización térmica avanzada.

## 6. Terminología del dominio

La terminología normativa procede de [CONTEXT.md](../../CONTEXT.md):

| Término | Significado en esta especificación |
|---|---|
| Protocolo de benchmark | Reglas versionadas de ejecución, aceptación, agregación e interpretación |
| Run | Aplicación de un protocolo a modelos y entorno bloqueados |
| Plan del run | Descripción canónica e inmutable materializada antes de medir |
| Identidad bloqueada del modelo | Nombre canónico y digest del artefacto evaluado |
| Clave esperada | Identificador único previsto por el plan |
| Registro primario | Evidencia terminal, inmutable y estructuralmente válida de una clave |
| Evidencia canónica | Plan, registros primarios y diario de integridad |
| Artefacto derivado | Salida regenerable desde evidencia canónica |
| Fallo de ejecución | Fallo terminal atribuible al sistema evaluado |
| Fallo de integridad del benchmark | Defecto que impide al harness garantizar la medición |
| Bloque experimental | Unidad mínima donde el orden puede afectar a la comparación |
| Celda de rendimiento | Muestras de modelo, workload, tipo y métrica oficial |
| Run estructuralmente completo | Contiene exactamente una vez todas sus claves y ninguna inesperada |
| Run elegible | Evidencia íntegra y sin fallos de integridad impeditivos |
| Ranking oficial | Clasificación con todos los componentes requeridos disponibles |
| N/D | Ausencia explícita de valor oficial; nunca cero ni permiso para renormalizar |
| Informe oficial | Salida de un run elegible; puede contener `N/D` y puede carecer de ranking global |
| Informe diagnóstico no oficial | Salida de un run inelegible por `benchmark_integrity_failure`, sin scores ni ranking oficiales |
| Rechazo explícito | Resultado sin informe ante evidencia corrupta, duplicada, inesperada o estructuralmente incompatible |

## 7. Implementation Decisions — arquitectura propuesta

```text
inputs versionados + lock
          │
          ▼
validación estructural y semántica offline
          │
          ▼
plan del run inmutable ───────► preflight contra Ollama
          │                            │
          │                            ▼
          └──────────────► ejecución según calendario
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
          registros primarios                  diario de integridad
                    └─────────────────┬─────────────────┘
                                      ▼
                         validación de evidencia
                                      ▼
                    agregación y artefactos derivados
```

### 7.1 Seams de prueba

El seam principal será:

> Dado un plan y su evidencia canónica, producir de forma determinista un informe oficial, un
> informe diagnóstico no oficial o un rechazo explícito sin informe, sin consultar la
> configuración actual ni contactar con Ollama.

Seams auxiliares necesarios:

1. inputs bloqueados → plan materializado;
2. plan → calendario y conjunto de claves;
3. evidencia existente → decisión de reanudación;
4. bytes JSON/JSONL → artefactos validados o diagnóstico fail-closed;
5. stream NDJSON → respuesta reconstruida, cumplimiento y TTFT válido o inválido;
6. artefacto → resultado del validador runtime y del oráculo de desarrollo.

### 7.2 Recomendaciones de implementación

- Preferir funciones puras para planificar, calcular claves, validar evidencia y agregar.
- Mantener efectos de red y disco fuera de esas funciones para facilitar tests deterministas.
- Centralizar reglas compartidas de versiones, claves, errores y `N/D`.
- No introducir nombres de módulos, clases o rutas como requisitos de producto.

Estas recomendaciones no autorizan una reorganización amplia del código fuera de lo necesario.

## 8. Modelo de artefactos

### 8.1 Inputs

Los inputs versionados son configuración, lock, casos funcionales, fixtures, definiciones de
herramientas y workloads. Se validan antes de materializar el plan. Después, sus identidades,
versiones, contenido metodológicamente relevante y hashes quedan fijados por el plan; los archivos
actuales no los sustituyen.

### 8.2 Plan del run

Es evidencia canónica, JSON, durable e inmutable. Contiene todo dato capaz de cambiar ejecución,
aceptación, agregación, scoring o interpretación.

### 8.3 Registros primarios

Son JSONL append-only diferenciados para funcional, rendimiento y TTFT. Cada registro válido se
asocia inequívocamente al plan y a una clave esperada. Incluyen resultados correctos, incorrectos,
incumplimientos, respuestas inválidas atribuibles al sistema y `execution_failure`.

### 8.4 Diario de integridad

Es JSONL canónico, append-only y separado. Sus eventos no satisfacen claves. La presencia de un
`benchmark_integrity_failure` hace inelegible el run.

### 8.5 Derivados

Resúmenes, agregados, scores, rankings, CSV, Markdown, SVG e informe JSON son regenerables. Pueden
usarse como cache solo tras verificar plan, hashes de registros y versiones de agregación/scoring.

## 9. Ciclo de vida completo de un run

1. Cargar y validar offline configuración, lock e inputs.
2. Resolver el modo, los defaults y todos los overrides efectivos de CLI.
3. Resolver identidades bloqueadas de modelos desde el lock.
4. Construir calendario, bloques y claves esperadas desde los valores efectivos.
5. Materializar y persistir atómicamente el plan.
6. Validar el plan y sus invariantes antes de contactar con Ollama.
7. Ejecutar preflight y comprobar servidor/modelos contra el plan.
8. Ejecutar cada clave en el orden fijado.
9. Persistir exactamente un registro terminal por clave ejecutada.
10. Ante defecto del harness, registrar un evento de integridad y detener la ruta oficial.
11. En reanudación, cargar el plan original, validar toda la evidencia y ejecutar solo ausencias.
12. Validar completitud, elegibilidad y celdas desde la evidencia primaria.
13. Producir el resultado de informe permitido por la matriz de estados.
14. Publicar ranking solo cuando el run sea elegible y estén disponibles todos los componentes
    requeridos.

## 10. Materialización e inmutabilidad del plan

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-PLAN-001` | Obligatorio | El plan DEBE existir y ser válido antes de la primera medición. | Ninguna llamada de medición ocurre sin plan durable; el preflight de medición lee ese plan. | Inputs, plan | Validación previa o `benchmark_integrity_failure` si el run ya comenzó | Integración con fake Ollama que comprueba orden de eventos |
| `REQ-PLAN-002` | Obligatorio | El plan DEBE fijar versiones, runner, modelos/digests, Ollama esperado, URL pública saneada, generación/thinking/contexto, seed, planificador, calendario, casos/workloads, repeticiones, claves, hashes, cumplimiento, scoring, pesos, métricas, políticas e información necesaria para interpretar plataforma y entorno. | El schema y validador semántico rechazan cualquier campo requerido ausente o incoherente. | Plan | Plan inválido; run no iniciado | Corpus positivo/negativo y test de manifest completo |
| `REQ-PLAN-003` | Obligatorio | El plan NO DEBE sobrescribirse ni regenerarse después de la primera ejecución. | Un segundo intento de materialización deja los bytes originales intactos y falla explícitamente. | Plan | Conflicto de inmutabilidad | Test de regresión y fault injection |
| `REQ-PLAN-004` | Obligatorio | Reanudación, agregación e informe DEBEN usar el plan original, nunca valores actuales. | Cambiar configuración, pesos o inputs actuales no cambia el resultado; una incompatibilidad detiene reanudación. | Plan, inputs, derivados | Incompatibilidad con plan | Test metamórfico con configuración modificada |
| `REQ-PLAN-005` | Obligatorio | El preflight DEBE verificar que Ollama y los modelos reales coinciden con lo materializado. | Una diferencia de versión o digest rechaza el preflight, impide medir y no completa claves. | Plan, lock | Preflight rechazado | Integración con fake Ollama e identidad alterada |
| `REQ-PLAN-006` | Obligatorio | El plan DEBE registrar identidades de benchmark, schema, paquete/implementación y algoritmos relevantes. | Un auditor puede identificar la lógica compatible de planificación, agregación, scoring e informe. | Plan | Versión ausente/incompatible | Test de schema y compatibilidad histórica |

### 10.1 Modos de ejecución y overrides efectivos

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-MODE-001` | Obligatorio | La CLI DEBE distinguir `dry-run`, `smoke`, `official-functional` y `official-performance`, y rechazar un modo incompatible con la pista invocada. | Cada invocación acepta solo los modos definidos para su pista y conserva su identidad exacta. | CLI, plan | Modo inválido | Tests de interfaz |
| `REQ-MODE-002` | Obligatorio | El plan DEBE fijar el modo y los valores efectivos resultantes de defaults, configuración y overrides de CLI, incluidos repeticiones, workloads y cantidades de mediciones que alteren claves esperadas. | El plan permite reconstruir qué valores se aplicaron, incluidos `--repetitions`, `--workloads` y cualquier override futuro con el mismo efecto. | CLI, plan | Plan incompleto | Tests de materialización |
| `REQ-MODE-003` | Obligatorio | Las claves esperadas DEBEN calcularse exclusivamente desde los valores efectivos fijados en el plan. | Cambiar un valor efectivo cambia plan y claves antes de medir; `ttft_runs = 0` no planifica claves ni celdas TTFT y no produce fallo ni `N/D` por su ausencia. | Plan, claves, celdas | Planificación incoherente | Tests parametrizados de conteos |
| `REQ-MODE-004` | Obligatorio | Reanudar DEBE exigir igualdad exacta del modo y de todo valor efectivo que pueda alterar ejecución, mediciones o claves. | Cualquier diferencia se rechaza antes de escribir evidencia o contactar con Ollama. | CLI, plan, evidencia | Reanudación incompatible | Integración con overrides mutados |
| `REQ-MODE-005` | Obligatorio | `dry-run` DEBE validar y mostrar la planificación sin ejecutar mediciones ni producir evidencia canónica de ejecución. | No crea registros primarios ni diario de un run ejecutado; cualquier representación del plan es una previsualización no reanudable ni elegible. | CLI, salida de planificación | Previsualización | Integración que comprueba cero mediciones y cero evidencia de ejecución |
| `REQ-MODE-006` | Obligatorio | `smoke` DEBE producir únicamente resultados exploratorios marcados como no oficiales. | Sus resultados nunca validan como informe oficial ni aportan scores o ranking oficiales. | Plan, registros, derivados | Exploratorio no oficial | Integración de informe |
| `REQ-MODE-007` | Obligatorio | Solo `official-functional` y `official-performance` PUEDEN producir evidencia canónica elegible para informe oficial y ranking. | Cambiar solo el modo a `dry-run` o `smoke` elimina la elegibilidad oficial aunque el resto de valores coincida. | Plan, evidencia, informe | Elegible/no oficial | Matriz de modos |

## 11. Generación y verificación del calendario

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-SCHEDULE-001` | Obligatorio | El calendario DEBE derivarse de seed e identidades bloqueadas, no del orden de configuración. | Toda permutación del mismo conjunto bloqueado produce las mismas asignaciones por identidad. | Plan | Calendario inválido | Propiedad Hypothesis de permutación |
| `REQ-SCHEDULE-002` | Obligatorio | Funcional DEBE equilibrar posiciones por caso y repeticiones. | Por caso/posición las frecuencias son iguales cuando es posible y difieren como máximo en uno en otro caso. | Plan, registros funcionales | Bloque desequilibrado | Propiedad sobre N modelos y R repeticiones |
| `REQ-SCHEDULE-003` | Obligatorio | Rendimiento DEBE equilibrar por workload y tipo `cold`, `hot`, `TTFT`. | Cada bloque cumple la misma cota de diferencia máxima de uno. | Plan, registros de rendimiento/TTFT | Bloque desequilibrado | Propiedad parametrizada por workload/tipo |
| `REQ-SCHEDULE-004` | Obligatorio | La seed DEBE resolver determinísticamente las posiciones sobrantes sin aumentar repeticiones. | Mismos inputs producen bytes o estructura semántica equivalente; ningún plan añade muestras. | Plan | No determinismo | Repetición y comparación del plan normalizado |
| `REQ-SCHEDULE-005` | Obligatorio | El plan DEBE permitir reconstruir y verificar el calendario independientemente. | Registra versión de algoritmo, seed, identidades, bloques y posición de cada ejecución. | Plan | Evidencia insuficiente | Validador independiente en tests |
| `REQ-SCHEDULE-006` | Obligatorio | Las invariantes del calendario DEBEN validarse antes de contactar con Ollama. | Un calendario mutado falla sin peticiones HTTP. | Plan | `benchmark_integrity_failure` si se detecta después de iniciar | Test con fake que cuenta cero peticiones |

No se exige equilibrio completo de parejas de precedencia.

## 12. Definición de claves esperadas

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-KEY-001` | Obligatorio | El plan DEBE enumerar o permitir reconstruir el conjunto exacto de claves. | Un validador independiente obtiene la misma colección sin consultar estado parcial. | Plan | Plan incompleto/incoherente | Propiedad de generación de claves |
| `REQ-KEY-002` | Obligatorio | Cada clave DEBE identificar sin ambigüedad modelo, caso/workload, repetición, tipo y posición relevantes. | Dos ejecuciones planificadas distintas nunca comparten clave. | Plan, registros | Colisión | Hypothesis sobre combinaciones válidas |
| `REQ-KEY-003` | Obligatorio | Cada registro primario DEBE referenciar plan y clave esperada. | Registros huérfanos o con identidad divergente son rechazados. | Registros primarios | Clave inesperada/incompatibilidad | Corpus negativo y test semántico |
| `REQ-KEY-004` | Obligatorio | `execution_key` y `measurement_key` DEBEN tener semántica estable y validarse por tipo de registro. | La clave incorrecta para el tipo de medición no supera schema/semántica. | Plan, registros | Tipo de clave inválido | Tests de contrato |

## 13. Política de completitud

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-COMPLETE-001` | Obligatorio | Un run estructuralmente completo DEBE contener cada clave esperada exactamente una vez. | Igualdad exacta entre conjunto planificado y multiconjunto observado. | Plan, registros | Ausente, duplicada, inesperada | Tests unitarios y propiedades |
| `REQ-COMPLETE-002` | Obligatorio | Duplicados NO DEBEN resolverse por precedencia ni deduplicación. | Cualquier duplicado produce rechazo explícito y no genera informe. | Registros | Run incompatible | Casos contiguos y no contiguos |
| `REQ-COMPLETE-003` | Obligatorio | Una clave inesperada DEBE considerarse incompatible con el plan. | Produce rechazo explícito y no genera informe. | Plan, registros | Run incompatible | Mutación de claves |
| `REQ-COMPLETE-004` | Obligatorio | Estructuralmente completo y elegible DEBEN ser estados distintos. | Un run con todas las claves y evento de integridad es completo pero inelegible. | Toda evidencia | Completo/inelegible | Test de matriz de estados |
| `REQ-COMPLETE-005` | Obligatorio | Un run elegible con claves o celdas planificadas incompletas PUEDE producir un informe oficial con `N/D`, pero no ranking global si falta un componente requerido. | El informe conserva la ausencia, marca la comparación inconclusa y no la confunde con inelegibilidad. | Informe JSON y presentaciones | Informe oficial sin ranking | Integración de informe |

## 14. Reanudación e idempotencia

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-RESUME-001` | Obligatorio | Reanudar DEBE cargar primero el plan original y validar toda la evidencia. | No se contacta con Ollama antes de completar la validación. | Plan, registros, diario | Reanudación rechazada | Integración fake y evidencia corrupta |
| `REQ-RESUME-002` | Obligatorio | Reanudar DEBE ejecutar solo claves esperadas ausentes. | Desde cualquier subconjunto válido, la unión final contiene cada clave una vez. | Registros | Pendiente/completada | Stateful property con prefijos y subconjuntos |
| `REQ-RESUME-003` | Obligatorio | Una clave completada NO DEBE sobrescribirse ni volver a escribirse. | Reanudar un run completo no modifica evidencia ni contacta con Ollama. | Registros | No-op válido | Test de idempotencia y hashes |
| `REQ-RESUME-004` | Obligatorio | Duplicados, inesperadas, corrupción o diario de integridad DEBEN detener la reanudación. | No se intenta reparar ni continuar. | Evidencia canónica | Reanudación rechazada | Matriz de fallos |
| `REQ-RESUME-005` | Obligatorio | `execution_failure` DEBE satisfacer su clave y ser terminal; un evento de integridad NO. | El primero no se reintenta; el segundo deja la clave ausente y el run inelegible. | Registros, diario | Fallo medido/fallo de integridad | Test de clasificación y reanudación |
| `REQ-RESUME-006` | Obligatorio | Reanudar DEBE respetar exactamente el calendario original. | El estado parcial no cambia posiciones ni orden planificado de pendientes. | Plan, registros | Calendario incompatible | Propiedad stateful |

## 15. Persistencia JSON y JSONL

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-STORAGE-001` | Obligatorio | El plan JSON DEBE escribirse de forma durable y atómica. | Un fallo antes del reemplazo conserva el estado anterior y nunca expone un plan parcial como válido. | Plan | Error de persistencia | Fault injection |
| `REQ-STORAGE-002` | Obligatorio | Cada registro JSONL DEBE serializarse y validarse completamente antes de append. | Nunca se inicia una escritura con un objeto no validado. | Registros, diario | Registro inválido | Test con serialización fallida |
| `REQ-STORAGE-003` | Obligatorio | Tras append se DEBE hacer flush y `fsync`. | El retorno exitoso implica que el registro fue entregado al sistema de persistencia. | Registros, diario | Error de persistencia | Mock/fault injection en seam de escritura |
| `REQ-STORAGE-004` | Obligatorio | Los artefactos canónicos DEBEN ser inmutables una vez escritos. | Ninguna operación oficial trunca, elimina o reescribe contenido existente. | Plan, registros, diario | Conflicto de inmutabilidad | Hashes antes/después en tests |
| `REQ-STORAGE-005` | Obligatorio | Una escritura JSONL parcial DEBE invalidar el run. | La lectura posterior detecta corrupción, rechaza sin informe y no consume el prefijo. | Registros, diario | Corrupción/rechazo explícito | Fault injection de línea parcial |
| `REQ-STORAGE-006` | Obligatorio | El diario de integridad DEBE ser canónico, append-only y tener eventos únicos. | Duplicados o corrupción del diario fallan cerrado. | Diario | Diario inválido | Tests de schema, unicidad y parser |
| `REQ-STORAGE-007` | Obligatorio | Si no puede persistirse un evento de integridad, el proceso DEBE fallar y admitir que la evidencia quedó incompleta. | Código de error no cero, diagnóstico saneado y ninguna clave completada. | Diario, stderr | Evidencia no persistida | Fault injection |

## 16. Política fail-closed

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-FAILCLOSED-001` | Obligatorio | Validación, reanudación, agregación, comparación e informe DEBEN rechazar corrupción sintáctica o estructural. | Ninguna operación continúa con registros anteriores aparentemente válidos. | Todos los JSON/JSONL canónicos | Corrupción | Corpus de archivos corruptos |
| `REQ-FAILCLOSED-002` | Obligatorio | Se DEBEN detectar JSON inválido, UTF-8 inválido, línea vacía no permitida, truncamiento, línea malformada y tipo raíz incorrecto. | Cada clase produce rechazo determinista. | JSON/JSONL | Código de diagnóstico estable | Tests parametrizados |
| `REQ-FAILCLOSED-003` | Obligatorio | El diagnóstico DEBE incluir archivo, línea y causa/posición disponibles. | El usuario puede localizar el defecto sin una traza cruda obligatoria. | Diagnóstico | Error saneado | Assertions sobre mensajes/estructura |
| `REQ-FAILCLOSED-004` | Obligatorio | El artefacto original NO DEBE modificarse durante el rechazo. | Hash y bytes permanecen iguales. | Artefacto defectuoso | Rechazo explícito | Test antes/después |
| `REQ-FAILCLOSED-005` | Obligatorio | NO DEBE existir recuperación automática o best-effort oficial. | No hay flags/rutas oficiales que ignoren o reparen corrupción en `0.3.0`. | CLI y runtime | Operación no soportada | Tests de interfaz y documentación |

## 17. Modelo de errores y resultados

### 17.1 Estados normativos

| Estado | Registro | Satisface clave | Efecto oficial |
|---|---:|---:|---|
| Resultado correcto | Primario | Sí | Puede contribuir si cumple todas las reglas |
| Resultado funcionalmente incorrecto | Primario | Sí | Fallo funcional |
| Incumplimiento de workload | Primario | Sí | Muestra inválida; celda `N/D` |
| Respuesta inválida atribuible al sistema | Primario | Sí | Muestra inválida/fallo según pista |
| `execution_failure` | Primario | Sí | Terminal, sin métricas positivas, efecto negativo aplicable |
| `benchmark_integrity_failure` | Diario | No | Run inelegible; nunca penaliza al modelo |

### 17.2 Requisitos

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-ERROR-001` | Obligatorio | El protocolo DEBE distinguir resultados incorrectos, incumplimientos, `execution_failure` y `benchmark_integrity_failure`. | Cada escenario produce exactamente una clasificación compatible. | Registros, diario | Estados anteriores | Tabla de decisión en tests |
| `REQ-ERROR-002` | Obligatorio | `execution_failure` DEBE conservar clave, estado, causa, evidencia y métricas parciales disponibles. | Es auditable, terminal y no aporta valores oficiales positivos. | Registro primario | Fallo de ejecución | Integración fake: HTTP error, timeout, desconexión/malformado |
| `REQ-ERROR-003` | Obligatorio | `benchmark_integrity_failure` NO DEBE penalizar al modelo ni satisfacer claves. | Cualquier evento hace inelegible el run y solo permite un informe diagnóstico no oficial que declara la inelegibilidad y excluye scores y ranking oficiales. | Diario, informe diagnóstico no oficial | Fallo de integridad | Tests de clasificación y salida |
| `REQ-ERROR-004` | Obligatorio | Ante atribución incierta, la clasificación DEBE ser conservadora como fallo de integridad. | Ningún defecto no atribuible con certeza se transforma en fallo del modelo. | Runtime, diario | Integridad | Casos límite versionados |
| `REQ-ERROR-005` | Obligatorio | Los eventos de integridad DEBEN registrar identidad, evento único, timestamp, fase, código, descripción saneada, componente, operación, clave opcional y posible compromiso de persistencia. | El schema rechaza eventos sin evidencia mínima. | Diario | Evento inválido | Corpus de schema |
| `REQ-ERROR-006` | Obligatorio | Diagnósticos, errores y eventos del diario NO DEBEN exponer credenciales, tokens, URLs con secretos ni contenido privado innecesario. | Casos adversariales con secretos se redactan antes de persistir o mostrar por cualquier canal. | Diario, stderr, salidas de error | Diagnóstico saneado | Tests de redacción |
| `REQ-ERROR-007` | Obligatorio | Un input inválido antes de crear el run DEBE impedir su materialización; un defecto de integridad de un run existente DEBE registrarse cuando sea posible. | No se crea evidencia de run para una configuración rechazada; un run iniciado conserva diagnóstico. | Inputs, plan, diario | Validación previa/integridad | Tests de ciclo de vida |

La lista exacta de códigos y fases es delegable, pero sus valores deberán ser estables y
versionados.

## 18. Completitud de celdas de rendimiento

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-PERF-001` | Obligatorio | Una celda DEBE identificarse por modelo, workload, estado/tipo y métrica oficial. | Cada muestra planificada pertenece inequívocamente a sus celdas. | Plan, registros | Celda incoherente | Tests de agrupación |
| `REQ-PERF-002` | Obligatorio | Una celda solo DEBE producir métrica oficial si contiene exactamente todas sus muestras y todas son válidas. | Cantidad, claves y validez coinciden con el plan. | Plan, registros, derivados | Completa/incompleta | Matriz de celdas |
| `REQ-PERF-003` | Obligatorio | Una muestra es inválida ante `execution_failure`, incumplimiento, respuesta incompleta, métrica requerida ausente o inválida, verificación fría ausente o evidencia incoherente. | Los criterios se fijan en el plan antes de observar resultados. | Plan, registro | Muestra inválida | Tests parametrizados |
| `REQ-PERF-004` | Obligatorio | Una sola muestra inválida DEBE dejar la métrica de la celda en `N/D`. | No se agrega el subconjunto válido ni se inventa sustituto. | Derivados | Celda incompleta | Regresión sobre mediana sesgada |
| `REQ-PERF-005` | Obligatorio | Las muestras válidas de una celda incompleta PUEDEN mostrarse solo como diagnóstico. | Están separadas de agregación, score y ranking. | Informe | Diagnóstico no puntuable | Test de informe |
| `REQ-PERF-006` | Obligatorio | Invalidar una muestra NO DEBE mejorar ninguna métrica o puntuación oficial. | Propiedad monotónica para todas las celdas y componentes. | Agregación/scoring | `N/D` o score no disponible | Hypothesis metamórfico |

## 19. Validación de streaming y TTFT

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-TTFT-001` | Obligatorio | El tiempo se DEBE medir hasta el primer payload significativo. | Solo `content`, `thinking` o `tool_calls` observables activan el reloj; líneas vacías, metadatos y evento final aislado no. | Registro TTFT | TTFT ausente | Fake stream con secuencias de chunks |
| `REQ-TTFT-002` | Obligatorio | El stream DEBE leerse íntegramente como NDJSON válido y terminar con la señal final esperada. | Truncamiento, línea malformada o final ausente invalidan la muestra. | Registro TTFT | Stream inválido/`execution_failure` | Fake Ollama y corpus NDJSON |
| `REQ-TTFT-003` | Obligatorio | La respuesta DEBE reconstruirse determinísticamente incluyendo contenido, thinking, tool calls y métricas finales aplicables. | La reconstrucción equivale a la secuencia de eventos y conserva orden/información. | Registro TTFT | Reconstrucción inválida | Tests de contrato streaming |
| `REQ-TTFT-004` | Obligatorio | La respuesta reconstruida DEBE cumplir las mismas reglas del workload equivalente no streaming. | Se reutiliza la misma semántica de cumplimiento, sin reglas TTFT laxas. | Plan, registro TTFT | Incumplimiento | Test diferencial stream/no-stream |
| `REQ-TTFT-005` | Obligatorio | El TTFT observado solo DEBE ser oficial si toda la muestra es válida. | Un stream rápido pero truncado/incumplidor no entra en mediana ni score. | Registro, celda TTFT | Diagnóstico/no oficial | Regresión de ventaja inválida |
| `REQ-TTFT-006` | Obligatorio | El tiempo observado y evidencia parcial PUEDEN conservarse para diagnóstico. | La medición está marcada como no oficial y no sustituye valores. | Sección diagnóstica de informe | Muestra inválida | Test de serialización/informe |

## 20. Agregación, N/D y ranking

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-AGG-001` | Obligatorio | La agregación DEBE partir exclusivamente de plan y registros primarios validados. | Eliminar caches produce el mismo informe semántico. | Evidencia, derivados | Derivado regenerado | Integración principal |
| `REQ-AGG-002` | Obligatorio | `N/D` NO DEBE convertirse en cero, infinito, mejor/peor observado ni valor perfecto. | El informe conserva disponibilidad separada del valor. | Informe, CSV/Markdown | Dato ausente | Unitarios y schemas |
| `REQ-AGG-003` | Obligatorio | Los pesos NO DEBEN renormalizarse cuando falte un componente. | El score queda incompleto. | Plan, informe | Score incompleto | Regresión de ponderación |
| `REQ-AGG-004` | Obligatorio | Si cualquier modelo planificado tiene un componente requerido incompleto, NO DEBE existir ranking global oficial. | El informe declara comparación inconclusa sin ganador. | Informe | Sin ranking | Integración multimodelo |
| `REQ-AGG-005` | Obligatorio | Las reglas, métricas y pesos DEBEN provenir del plan, sin cambios en las fórmulas oficiales de esta versión salvo los necesarios para impedir ventaja inválida. | La configuración actual no altera resultados; los pesos acordados permanecen. | Plan, derivados | Incompatibilidad | Test metamórfico |
| `REQ-AGG-006` | Obligatorio | Un `execution_failure` NO DEBE aportar métricas positivas y DEBE reflejarse en estabilidad/fallo aplicable sin inventar valores. | Sustituir éxito por fallo nunca mejora el mismo resultado oficial. | Registros, agregados | Fallo medido | Propiedad monotónica |

### 20.1 Matriz normativa de resultados de informe

Para evidencia producida por modos `official-*`, el procesamiento DEBE terminar en exactamente uno
de estos tres resultados. `dry-run` y `smoke` quedan fuera de esta matriz porque no son elegibles
para informe oficial.

| Estado de entrada | Resultado permitido | Scores y ranking oficiales | Declaración obligatoria |
|---|---|---|---|
| Run elegible | Informe oficial, aunque incluya `N/D` | Los scores incompletos quedan no disponibles; solo hay ranking global si están todos los componentes requeridos | Elegibilidad, disponibilidad de cada componente y presencia o ausencia de ranking |
| Run inelegible por `benchmark_integrity_failure` con evidencia legible | Únicamente informe diagnóstico no oficial | Ninguno | Inelegibilidad inequívoca y eventos de integridad saneados |
| Run incompatible o evidencia corrupta, incluidos duplicados, claves inesperadas, corrupción o incompatibilidad estructural | Rechazo explícito; no se genera informe | Ninguno | Causa localizable y saneada del rechazo |

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-REPORT-001` | Obligatorio | Un run elegible PUEDE producir informe oficial con `N/D`; solo PUEDE incluir ranking global cuando todos los componentes requeridos estén disponibles. | La ausencia de un componente no convierte el informe en diagnóstico ni inventa ranking. | Informe oficial | Elegible con/sin ranking | Matriz de integración |
| `REQ-REPORT-002` | Obligatorio | Un run inelegible por `benchmark_integrity_failure` solo PUEDE producir informe diagnóstico no oficial. | La salida declara inelegibilidad y no contiene scores ni ranking oficiales. | Informe diagnóstico no oficial | Inelegible | Matriz de integración |
| `REQ-REPORT-003` | Obligatorio | Duplicados, claves inesperadas, corrupción o incompatibilidad estructural DEBEN producir rechazo explícito sin informe. | No se escribe JSON, Markdown, CSV, SVG ni otra presentación de informe. | Evidencia, salida | Rechazo explícito | Matriz de integración |

## 21. Reconstrucción de artefactos derivados

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-DERIVED-001` | Obligatorio | Resúmenes, agregados e informes DEBEN poder regenerarse desde evidencia canónica. | Un run válido sin derivados vuelve a producirlos. | Plan, registros, informe | Regenerado | Integración end-to-end sin red |
| `REQ-DERIVED-002` | Obligatorio | Un cache solo PUEDE usarse tras verificar run, huella del plan, hashes de registros y versiones de algoritmos. | Un cache sin procedencia o divergente se ignora. | Cache, evidencia | Cache inválido | Tests con cache mutado |
| `REQ-DERIVED-003` | Obligatorio | Una contradicción o desactualización del derivado NO DEBE invalidar por sí sola evidencia íntegra. | El derivado se detecta, descarta y regenera; la salida regenerada coincide con la evidencia y se diagnostica el defecto del generador. | Derivados | Derivado inválido u obsoleto | Integración comparativa |
| `REQ-DERIVED-004` | Obligatorio | Si la discrepancia revela corrupción o incoherencia canónica, la operación DEBE rechazarse sin generar informe. | La causa se atribuye al artefacto primario y no se oculta regenerando derivados. | Evidencia | Rechazo explícito | Casos corruptos |
| `REQ-DERIVED-005` | Obligatorio | Regenerar NO DEBE modificar plan, registros, identidad ni fechas originales. | Hashes canónicos idénticos antes/después. | Toda evidencia | Conflicto de inmutabilidad | Test de hashes |
| `REQ-DERIVED-006` | Obligatorio | Una implementación incompatible NO DEBE producir un informe histórico aproximado. | Rechaza con versión requerida o usa un mecanismo explícito futuro. | Plan histórico | Versión no soportada | Test con `0.2.0` |

## 22. Contratos JSON Schema

### 22.1 Artefactos cubiertos

La cobertura obligatoria comprende:

- configuración y lock;
- casos funcionales, fixtures, herramientas y workloads;
- plan del run;
- registros funcionales, de rendimiento y TTFT;
- eventos de integridad y estructuras de fallo/validez;
- salidas JSON de informe oficial y diagnóstico no oficial.

No cubre caches internos, temporales, CSV, Markdown o SVG.

### 22.2 Requisitos

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-SCHEMA-001` | Obligatorio | Cada artefacto cubierto DEBE tener un schema local, identificable y versionado. | Todos los ejemplos producidos declaran contrato y validan offline. | Inputs, evidencia, informe JSON | Schema ausente | Inventario automático de contratos |
| `REQ-SCHEMA-002` | Obligatorio | Los schemas DEBEN exigir campos, tipos, límites y enums estables; campos adicionales se rechazan salvo justificación. | Corpus de ausencias, tipos y extras falla como se espera. | Todos los cubiertos | Contrato inválido | `jsonschema` corpus negativo |
| `REQ-SCHEMA-003` | Obligatorio | Definiciones de versiones, IDs, hashes, claves, modelos, métricas, `N/D`, procedencia, fallos, validez, timestamps y entorno DEBEN reutilizarse. | No existen definiciones incompatibles para el mismo concepto. | Schemas | Divergencia contractual | Revisión y tests de referencias |
| `REQ-SCHEMA-004` | Obligatorio | No DEBE haber referencias remotas necesarias en tests o runtime. | La validación completa funciona sin red. | Schemas | Referencia no resoluble | Test offline |
| `REQ-SCHEMA-005` | Obligatorio | Un cambio incompatible DEBE crear nueva versión de contrato y nunca cambiar interpretación histórica silenciosamente. | Fixtures antiguos conservan resultado bajo su schema original. | Schemas/artefactos | Versión incompatible | Tests de compatibilidad |
| `REQ-SCHEMA-006` | Obligatorio | Schema valida estructura; validadores semánticos validan unicidad, conjunto exacto, hashes, calendario, celdas y coherencia cruzada. | Un JSON estructuralmente válido pero semánticamente incoherente es rechazado por la capa correcta. | Runtime, schemas | Error estructural/semántico | Corpus diferencial etiquetado |
| `REQ-SCHEMA-007` | Obligatorio | El contrato de informe JSON DEBE distinguir informe oficial y diagnóstico no oficial, procedencia, elegibilidad, resultados reconstruidos, celdas completas/incompletas, valores/`N/D`, componentes puntuables y disponibilidad de score/ranking. | Un diagnóstico no valida como informe oficial y los consumidores interpretan estado y disponibilidad sin inferir desde valores. | Informe JSON | Informe inválido | Schema y snapshots estructurales |
| `REQ-SCHEMA-008` | Obligatorio | Los schemas NO DEBEN coercionar, completar, eliminar ni corregir datos. | El objeto validado conserva exactamente su contenido o se rechaza. | Todos | Contrato inválido | Casos de bool/int, null, strings numéricos y extras |
| `REQ-SCHEMA-009` | Obligatorio | El contrato estructural y el validador runtime necesarios para cerrar un artefacto DEBEN entregarse en la misma fase que su primer uso canónico o antes. | Ninguna fase ni ticket declara completo un artefacto que dependa de un contrato o validador futuro. | Todos los cubiertos | Dependencia incumplida | Revisión de fases y edges de tickets |
| `REQ-SCHEMA-010` | Obligatorio | Los validadores entregados por fase DEBEN ser definitivos para el contrato v3 y NO DEBEN ser implementaciones provisionales destinadas a sustituirse en una fase posterior. | Un ticket posterior puede ampliar cobertura o refactorizar con equivalencia demostrada, pero no reemplazar semántica pendiente; un cambio incompatible exige versión nueva. | Schemas, runtime | Validador provisional/incompatibilidad | Revisión y corpus de regresión |

## 23. Validación ligera de runtime

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-RUNTIME-001` | Obligatorio | El paquete DEBE mantener `dependencies = []`. | La metadata de `0.3.0` no contiene dependencias obligatorias. | Paquete | Configuración inválida | Test de pyproject/metadata |
| `REQ-RUNTIME-002` | Obligatorio | Los validadores propios DEBEN rechazar obligatorios ausentes, tipos, límites, enums, extras prohibidos y versiones, sin coerciones ni valores predeterminados silenciosos. | Coinciden con el corpus estructural de `jsonschema` y conservan exactamente el input aceptado. | Runtime | Validación estructural | Tests diferenciales |
| `REQ-RUNTIME-003` | Obligatorio | Los validadores DEBEN aplicar invariantes semánticas cruzadas no expresables adecuadamente en schema. | Ningún artefacto solo formalmente válido entra en una operación canónica si viola el plan. | Runtime/evidencia | Validación semántica | Corpus semántico |
| `REQ-RUNTIME-004` | Obligatorio | Instalar dependencias de desarrollo NO DEBE cambiar aceptación o resultados canónicos. | La misma entrada produce igual decisión en entorno mínimo y dev. | Runtime | Divergencia | Job comparativo de entorno |
| `REQ-RUNTIME-005` | Obligatorio | Los errores DEBEN señalar la ruta del campo o invariante afectada cuando sea posible. | Diagnóstico preciso sin corrección silenciosa. | Diagnósticos | Error validado | Assertions estructuradas |

## 24. Testing Decisions — estrategia de tests

### 24.1 Principio

Los tests verificarán comportamiento observable a través de los seams definidos, no nombres
internos. La suite normal continuará sin Ollama real, modelos, Internet ni GPU. Las integraciones
usarán exclusivamente fake Ollama y herramientas virtuales.

### 24.2 Requisitos de testing

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-TEST-001` | Obligatorio | Tests unitarios DEBEN cubrir parsers, validadores, claves, calendario, clasificación, celdas, `N/D`, agregación, Wilson y McNemar. | Cada regla normativa tiene al menos un ejemplo positivo y negativo. | Lógica pura | Pass/fail | Suite `unittest` |
| `REQ-TEST-002` | Obligatorio | Tests de regresión DEBEN conservar defectos críticos descubiertos, incluido cualquier contraejemplo mínimo de Hypothesis. | Un defecto corregido reaparece si se revierte la protección. | Suite | Regresión | Tests nombrados por comportamiento |
| `REQ-TEST-003` | Obligatorio | Hypothesis DEBE cubrir claves, duplicados/ausencias/inesperadas, equilibrio, permutación, seed, reanudación, idempotencia, sobrescritura, estructuras, equivalencia, `N/D`, monotonicidad, seguridad de rutas, round-trip e invariancias irrelevantes. | Perfil CI acotado completa sin red ni tiempos reales y reduce fallos. | Lógica pura | Contraejemplo mínimo | Properties integradas con `unittest` |
| `REQ-TEST-004` | Obligatorio | Hypothesis NO DEBE generar dataset oficial, juzgar semántica, medir rendimiento ni reemplazar fake Ollama. | No hay tests generativos que pretendan puntuar modelos. | Suite | Uso fuera de alcance | Revisión y separación de perfiles |
| `REQ-TEST-005` | Obligatorio | Debe existir corpus versionado positivo y negativo para schemas y validadores. | Incluye ausencias, tipos, extras, versiones, límites, incoherencias y JSON válido pero contrato inválido. | Fixtures de test | Aceptado/rechazado | Tests parametrizados |
| `REQ-TEST-006` | Obligatorio | `jsonschema` DEBE actuar solo como oráculo de desarrollo. | Oráculo y runtime coinciden en casos comparables; divergencias intencionales semánticas están documentadas. | Schemas/validadores | Divergencia | Job dev offline |
| `REQ-TEST-007` | Obligatorio | statsmodels DEBE validar Wilson y McNemar exacto en un job de oráculos separado. | Rejillas, extremos, simetría y casos sin observaciones coinciden dentro de tolerancias declaradas; fallos muestran inputs y diferencias. | Estadística | Divergencia numérica | Job de oráculo versionado |
| `REQ-TEST-008` | Obligatorio | Deben conservarse casos estadísticos dorados y propiedades independientes de statsmodels. | Un cambio del oráculo no redefine automáticamente la política de OAB. | Tests estadísticos | Oráculo incompatible | Golden tests y propiedades |
| `REQ-TEST-009` | Obligatorio | Fake Ollama DEBE cubrir contrato de request/response, NDJSON, final, métricas, errores y timeouts necesarios para `0.3.0`. | Runners y lifecycle se prueban end-to-end sin servidor real. | Integración | Respuestas simuladas | Suite de integración |
| `REQ-TEST-010` | Obligatorio | Fault injection DEBE comprobar atomicidad, append parcial, fallo del diario y preservación del original. | Un fallo al persistir el evento termina con código no cero, no completa ninguna clave y emite diagnóstico saneado; los demás puntos producen el estado especificado. | Persistencia | Integridad | Tests deterministas sin sleeps |
| `REQ-TEST-011` | Obligatorio | El seam principal plan+evidencia→resultado de informe DEBE cubrir run elegible completo o con `N/D`, run inelegible por integridad, evidencia incompatible o corrupta y cache divergente. | Produce respectivamente informe oficial con ranking condicionado, diagnóstico no oficial sin scores/ranking, rechazo sin informe o regeneración del derivado. | Todo el protocolo | Matriz de tres resultados | Integración de informe |
| `REQ-TEST-012` | Obligatorio | Cosmic Ray DEBE ejecutarse después de estabilizar la suite como prototipo manual sobre lógica pura crítica. | Produce informe reproducible con versión, alcance, mutantes, coste, supervivientes clasificados y huecos reales. | Entorno dev | Prototipo útil/incompatible | Informe de campaña |
| `REQ-TEST-013` | Obligatorio | Cosmic Ray NO DEBE ser gate de CI ni tener score mínimo en `0.3.0`. | Su ausencia no impide instalar/ejecutar; incompatibilidad se documenta antes de evaluar alternativa. | Dev | Resultado experimental | Revisión de configuración |
| `REQ-TEST-014` | Obligatorio | La matriz de modos y overrides DEBE probar planificación, elegibilidad, reanudación y cálculo de claves. | Cubre los cuatro modos, overrides mutados y `ttft_runs = 0` sin tratar TTFT como fallido o `N/D`. | CLI, plan, evidencia | Válido/incompatible/no oficial | Integración con fake Ollama |
| `REQ-TEST-015` | Obligatorio | Tests adversariales DEBEN insertar credenciales, tokens y URLs con secretos en errores y eventos. | Ninguna salida, diagnóstico ni línea del diario conserva el secreto en claro. | Diagnósticos, diario | Redacción | Corpus de secretos ficticios |
| `REQ-TEST-016` | Obligatorio | La misma matriz canónica DEBE ejecutarse en entorno mínimo y de desarrollo. | Ambos entornos aceptan, rechazan y generan salidas semánticamente idénticas. | Runtime, CI | Divergencia | Job comparativo |

### 24.3 Tipos de test

- **Unitarios:** lógica pura de planificación, validación, scoring existente, agregación y fórmulas.
- **Regresión:** contraejemplos y fallos conocidos con fixtures pequeños.
- **Propiedades:** invariantes combinatorias y metamórficas con Hypothesis.
- **Diferenciales:** runtime frente a `jsonschema`; estadística propia frente a statsmodels.
- **Integración simulada:** CLI/runners/report con fake Ollama y URL localhost efímera.
- **Contrato:** schemas, plan, registros, streaming y fake Ollama.
- **Mutation testing:** campaña manual posterior, no CI.
- **Integración real:** fuera de CI y fuera de los criterios automáticos de `0.3.0`.

## 25. Compatibilidad y versionado

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-COMPAT-001` | Obligatorio | El protocolo DEBE declarar `benchmark_version: 0.3.0` y `schema_version: 3` donde corresponda. | Configuración, plan, registros e informe nuevos no se identifican como `0.2.0`. | Artefactos v3 | Versión incompatible | Tests de schema/metadata |
| `REQ-COMPAT-002` | Obligatorio | Runs `0.2.0` NO DEBEN reanudarse, mezclarse, migrarse ni reinterpretarse silenciosamente. | Cada intento falla con diagnóstico explícito antes de ejecutar/agregar. | Runs históricos | Protocolo incompatible | Fixtures históricos |
| `REQ-COMPAT-003` | Obligatorio | Datos de protocolos distintos NO DEBEN entrar en una comparación oficial común. | El informe rechaza manifests/planes heterogéneos. | Informe | Runs incompatibles | Integración multimodelo/multirun |
| `REQ-COMPAT-004` | Obligatorio | Un cambio futuro incompatible DEBE obtener nueva identidad de contrato/algoritmo. | No se cambia silenciosamente el significado de artefactos existentes. | Schemas, plan | Versión futura | Contract tests |
| `REQ-COMPAT-005` | Obligatorio | El contenido funcional medido NO DEBE ampliarse en `0.3.0`. | Casos, scorers y herramientas mantienen la semántica de `0.2.0`; cualquier empaquetado conserva procedencia y demuestra equivalencia. | Inputs | Cambio fuera de alcance | Comparación versionada de inventario/semántica |
| `REQ-COMPAT-006` | Obligatorio | El runtime DEBE seguir siendo Python ≥3.11 y cero-deps. | Instalación mínima ejecuta validación, runners e informe sin extras de desarrollo. | Paquete | Entorno no soportado | Job mínimo |

La decisión física de reutilizar directamente inputs v2 o publicar artefactos equivalentes con
metadata nueva es delegable. No puede modificar casos, workloads, herramientas, scoring ni
procedencia, y nunca puede reescribir silenciosamente artefactos históricos.

## 26. Cambios previstos en documentación

| ID | Tipo | Comportamiento esperado | Condición de aceptación | Artefactos afectados | Errores/estados | Prueba o evidencia |
|---|---|---|---|---|---|---|
| `REQ-DOC-001` | Obligatorio | README DEBE describir `0.3.0`, plan, reanudación, compatibilidad y estados de informe. | El recorrido no promete compatibilidad o reparación inexistente. | README | Documentación obsoleta | Revisión documental |
| `REQ-DOC-002` | Obligatorio | Arquitectura DEBE reflejar evidencia canónica, diario y derivados. | Diagramas y componentes coinciden con ADR 0001/0003. | Arquitectura | Contradicción | Revisión cruzada |
| `REQ-DOC-003` | Obligatorio | Metodología y métricas DEBEN explicar calendario, celdas estrictas, TTFT condicionado, `N/D` y ausencia de ranking. | Un lector puede interpretar un informe incompleto sin inferencias ocultas. | Docs metodológicas | Ambigüedad | Checklist de términos |
| `REQ-DOC-004` | Obligatorio | Limitaciones DEBE documentar invalidación por JSONL parcial y ausencia de reparación automática. | El coste del fail-closed es visible. | Limitaciones | Omisión | Revisión documental |
| `REQ-DOC-005` | Obligatorio | Changelog/migración DEBEN explicar por qué `0.2.0` no es compatible. | No se ofrecen pasos de conversión silenciosa. | Docs de versión | Migración engañosa | Revisión de release |
| `REQ-DOC-006` | Obligatorio | La documentación de schemas DEBE enumerar contratos y separar estructura de semántica. | Cada artefacto cubierto enlaza a su contrato y reglas cruzadas. | Docs/schema | Contrato no localizable | Inventario documental |
| `REQ-DOC-007` | Obligatorio | Toda la documentación de comportamiento DEBE actualizarse en español, incluido `docs/security.md` con saneamiento de secretos, aislamiento de tests y ausencia de credenciales reales. | La revisión cruzada no encuentra comportamiento v3 sin documentar ni texto normativo contradictorio. | Documentación española | Documentación obsoleta | Checklist documental de release |

Toda documentación de comportamiento se mantendrá en español.

## 27. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación obligatoria |
|---|---|---|
| El alcance de schemas crece demasiado | Retraso de `0.3.0` | Implementar en orden: plan/registros, inputs, definiciones/corpus, informe JSON |
| Divergencia schema/runtime | Aceptación distinta en CI y usuarios | Corpus diferencial obligatorio y bloqueo de entrega |
| JSONL parcial tras caída | Run irrecuperable | Fail-closed explícito, fault injection y documentación; no reparación en esta versión |
| Clasificación errónea de fallos | Penalización injusta o defecto oculto | Tabla de decisión, códigos estables y clasificación conservadora como integridad |
| Calendario complejo | Sesgo o no determinismo | Función pura, versionada y properties exhaustivas sobre tamaños pequeños |
| Cache contradictorio | Informe incorrecto | Recalcular desde evidencia y verificar procedencia antes de usar cache |
| Celdas estrictas producen muchos `N/D` | Menos rankings concluyentes | Diagnóstico completo; repetir mediante run nuevo, no relajar reglas |
| statsmodels encarece CI | Feedback lento | Job de oráculos separado y ejecución condicionada delegable |
| Hypothesis introduce lentitud/flakiness | CI inestable | Perfil acotado, sin deadlines irrelevantes, sleeps, red o aleatoriedad externa |
| Cosmic Ray no encaja | Prototipo costoso | Campaña manual; documentar incompatibilidad y pedir aprobación antes de sustituirlo |
| Reproducción histórica incompleta | Informes antiguos no regenerables | Rechazo explícito y registro de versión/commit; no aproximaciones |
| Datos sensibles en errores | Exposición accidental | Redacción y tests adversariales de diagnósticos |

## 28. Plan de implementación por fases

### Fase 1 — Plan, calendario y claves

- Introducir el plan canónico v3, modos, overrides efectivos y materialización durable.
- Implementar calendario equilibrado y conjunto exacto de claves.
- Entregar los schemas v3 y validadores runtime definitivos de inputs de planificación, plan y
  registros primarios, incluidas las definiciones compartidas que necesiten.
- Validar contratos, plan y calendario offline.
- Añadir tests de propiedades de planificación.

### Fase 2 — Persistencia, errores y reanudación

- Endurecer JSON/JSONL fail-closed.
- Separar `execution_failure` y diario de integridad.
- Entregar el schema v3 y validador runtime definitivos del diario de integridad y sus estructuras
  de error antes de persistir el primer evento.
- Hacer reanudación idempotente contra el plan.
- Cubrir atomicidad y fallos mediante fault injection.

### Fase 3 — Rendimiento, TTFT y derivados

- Aplicar completitud estricta por celda.
- Reconstruir y validar el stream completo.
- Eliminar la autoridad de resúmenes persistidos.
- Entregar los schemas v3 y validadores runtime definitivos de informe oficial y diagnóstico no
  oficial antes de generar esas salidas.
- Regenerar informes desde evidencia, aplicar la matriz de estados y suprimir ranking incompleto.

### Fase 4 — Contratos restantes y corpus diferencial

- Formalizar los inputs y definiciones compartidas restantes que no fueran requisito de fases
  anteriores.
- Completar el corpus positivo/negativo de todos los contratos ya entregados.
- Validar diferencialmente runtime y `jsonschema`.
- No introducir ni sustituir validadores provisionales de fases anteriores.

### Fase 5 — Oráculos y endurecimiento de suite

- Completar properties Hypothesis y regresiones.
- Añadir job statsmodels para Wilson/McNemar.
- Verificar fake Ollama y contrato streaming.

### Fase 6 — Compatibilidad, documentación y release

- Actualizar versiones, documentación española —incluido `docs/security.md`— y rechazo de `0.2.0`.
- Ejecutar tests, `oab validate`, Ruff, Mypy y cobertura.
- Verificar `dependencies = []` e igualdad de comportamiento entre entorno mínimo y desarrollo.

### Fase 7 — Prototipo manual Cosmic Ray

- Ejecutar la campaña solo después de estabilizar la fase 5.
- Documentar coste, mutantes y huecos; no bloquear `0.3.0` por un score global.

El corte exacto en tickets deberá usar tracer bullets verificables y declarar dependencias entre
fases; esta sección no crea tickets.

### 28.1 Dependencias obligatorias entre fases y futuros tickets

| Trabajo | Bloqueado por | Contrato que debe estar cerrado al terminar |
|---|---|---|
| Fase 1 | Ninguno | Inputs de planificación, plan y registros primarios |
| Fase 2 | Fase 1 | Diario de integridad y estructuras de error |
| Fase 3 | Fases 1 y 2 | Informe JSON oficial y diagnóstico no oficial |
| Fase 4 | Fases 1, 2 y 3 | Inputs y definiciones restantes; corpus diferencial completo |
| Fase 5 | Fase 4 | Sin contratos pendientes para los oráculos y la suite |
| Fase 6 | Fase 5 | Compatibilidad, documentación y paridad de entornos verificadas |
| Fase 7 | Fase 5 | Ninguno nuevo; no bloquea la fase 6 ni el release |

Todo futuro ticket que use o produzca un artefacto DEBE incluir su contrato y validador definitivos
o declarar como bloqueo el ticket que ya los entrega. Ningún ticket PUEDE cerrarse apoyándose en un
validador provisional que otro ticket sustituirá después.

## 29. Criterios observables de aceptación

- [ ] `ACC-001` — Existe un plan v3 válido y durable antes de cualquier medición.
- [ ] `ACC-002` — El plan no puede sobrescribirse después de iniciar el run.
- [ ] `ACC-003` — Misma seed e identidades producen el mismo calendario.
- [ ] `ACC-004` — Permutar modelos en configuración no cambia asignaciones por identidad.
- [ ] `ACC-005` — Cada bloque cumple igualdad posible o diferencia máxima de uno.
- [ ] `ACC-006` — Las claves esperadas se reconstruyen independientemente.
- [ ] `ACC-007` — Duplicados y claves inesperadas se rechazan sin informe; las ausencias
  planificadas se conservan como incompletitud y no se confunden con ambos defectos.
- [ ] `ACC-008` — Reanudar desde cualquier subconjunto válido ejecuta solo ausencias.
- [ ] `ACC-009` — Reanudar un run completo no modifica evidencia ni llama a Ollama.
- [ ] `ACC-010` — Corrupción JSON/JSONL informa archivo, línea y causa disponibles.
- [ ] `ACC-011` — Ningún rechazo modifica el artefacto original.
- [ ] `ACC-012` — `execution_failure` es terminal, auditable y sin métricas positivas.
- [ ] `ACC-013` — `benchmark_integrity_failure` no satisface clave, no penaliza modelo y solo permite
  un informe diagnóstico no oficial sin scores ni ranking oficiales.
- [ ] `ACC-014` — Una muestra inválida deja su celda oficial en `N/D`.
- [ ] `ACC-015` — Invalidar una muestra nunca mejora métrica o score.
- [ ] `ACC-016` — Stream truncado, malformado, sin final o incumplidor no produce TTFT oficial.
- [ ] `ACC-017` — TTFT ignora líneas vacías, metadatos y final sin payload.
- [ ] `ACC-018` — El informe se reconstruye sin resúmenes persistidos.
- [ ] `ACC-019` — Cache divergente se ignora y evidencia canónica permanece intacta.
- [ ] `ACC-020` — Un componente requerido incompleto impide ranking global.
- [ ] `ACC-021` — Todos los artefactos acordados tienen schema y ejemplos positivos/negativos.
- [ ] `ACC-022` — Runtime y `jsonschema` coinciden en el corpus estructural comparable.
- [ ] `ACC-023` — Las invariantes semánticas rechazan contratos formalmente válidos pero incoherentes.
- [ ] `ACC-024` — Properties Hypothesis acordadas pasan en perfil CI acotado.
- [ ] `ACC-025` — Wilson y McNemar coinciden con statsmodels dentro de tolerancias declaradas.
- [ ] `ACC-026` — Fake Ollama cubre streaming, errores, timeouts y métricas finales sin red externa.
- [ ] `ACC-027` — Cosmic Ray produce un informe reproducible posterior a la estabilización.
- [ ] `ACC-028` — `0.2.0` se rechaza para reanudación, mezcla, migración e informe `0.3.0`.
- [ ] `ACC-029` — `dependencies = []` permanece y el entorno mínimo ejecuta `oab`.
- [ ] `ACC-030` — No cambian casos, herramientas, scorers, confirmaciones, pesos ni métricas oficiales.
- [ ] `ACC-031` — Tests, `oab validate`, Ruff, Mypy y cobertura pasan conforme a `AGENTS.md`.
- [ ] `ACC-032` — Ningún test normal requiere Ollama real, modelos, Internet o GPU.
- [ ] `ACC-033` — Cada artefacto tiene schema y validador runtime definitivos en la fase de su
  primer uso o antes; no existe ningún validador provisional pendiente de sustitución.
- [ ] `ACC-034` — El plan registra el modo y todos los valores efectivos resultantes de defaults,
  configuración y overrides que afectan repeticiones, workloads, mediciones o claves.
- [ ] `ACC-035` — Reanudar con un modo u override efectivo distinto se rechaza antes de escribir o
  contactar con Ollama.
- [ ] `ACC-036` — `dry-run` no ejecuta mediciones, no crea registros ni diario de ejecución y no
  produce evidencia canónica de ejecución.
- [ ] `ACC-037` — `smoke` produce resultados marcados como exploratorios y nunca informe oficial,
  score oficial o ranking oficial.
- [ ] `ACC-038` — Solo `official-functional` y `official-performance` producen evidencia canónica
  potencialmente elegible, sujeta al resto de reglas.
- [ ] `ACC-039` — Las claves coinciden con los valores efectivos del plan y `ttft_runs = 0` no crea
  claves ni celda TTFT fallida o `N/D`.
- [ ] `ACC-040` — Un run elegible produce informe oficial; puede contener `N/D` y solo incluye
  ranking global con todos los componentes requeridos.
- [ ] `ACC-041` — Un run inelegible por `benchmark_integrity_failure` produce como máximo un informe
  diagnóstico no oficial que declara inelegibilidad y no contiene scores ni ranking oficiales.
- [ ] `ACC-042` — Duplicados, claves inesperadas, corrupción e incompatibilidad estructural producen
  rechazo explícito y no generan ningún informe.
- [ ] `ACC-043` — Credenciales, tokens y URLs con secretos inyectados en errores, diagnósticos o
  eventos nunca aparecen en claro en salidas ni artefactos.
- [ ] `ACC-044` — Fallar al persistir un evento de integridad devuelve código distinto de cero, no
  completa ninguna clave y emite un diagnóstico saneado.
- [ ] `ACC-045` — Un digest de modelo o versión de Ollama distinto del plan hace fallar el preflight
  sin medir ni completar claves.
- [ ] `ACC-046` — Un derivado contradictorio o desactualizado se detecta, descarta y regenera desde
  evidencia íntegra; si revela corrupción canónica, se rechaza sin informe.
- [ ] `ACC-047` — Schemas y validadores rechazan coerciones, defaults silenciosos y datos
  desconocidos; todo input aceptado conserva exactamente su contenido.
- [ ] `ACC-048` — El mismo corpus produce decisiones y salidas semánticamente idénticas en entorno
  mínimo y de desarrollo.
- [ ] `ACC-049` — Toda la documentación de comportamiento está actualizada en español y
  `docs/security.md` refleja el saneamiento de secretos y el aislamiento de tests.

## 30. Matriz de trazabilidad

| Decisión/ADR | Requisitos principales | Evidencia de aceptación |
|---|---|---|
| Plan inmutable y evidencia canónica — ADR 0001 | `REQ-PLAN-*`, `REQ-MODE-*`, `REQ-DERIVED-*` | `ACC-001`, `ACC-002`, `ACC-018`, `ACC-019`, `ACC-034`–`ACC-039` |
| Protocolo fail-closed — ADR 0002 | `REQ-KEY-*`, `REQ-COMPLETE-*`, `REQ-STORAGE-*`, `REQ-FAILCLOSED-*` | `ACC-006`–`ACC-011` |
| Fallos medidos frente a integridad — ADR 0003 | `REQ-ERROR-*`, `REQ-RESUME-005` | `ACC-012`, `ACC-013`, `ACC-043`, `ACC-044` |
| Runtime cero-deps y oráculos dev — ADR 0004 | `REQ-SCHEMA-*`, `REQ-RUNTIME-*`, `REQ-TEST-*` | `ACC-021`–`ACC-027`, `ACC-029`, `ACC-033`, `ACC-047`, `ACC-048` |
| Calendario por bloque — ADR 0005 | `REQ-SCHEDULE-*` | `ACC-003`–`ACC-005` |
| Reanudación idempotente | `REQ-RESUME-*`, `REQ-MODE-004` | `ACC-008`, `ACC-009`, `ACC-035` |
| Modos y overrides efectivos | `REQ-MODE-*` | `ACC-034`–`ACC-039` |
| Completitud estricta de celdas | `REQ-PERF-*`, `REQ-AGG-002`–`006` | `ACC-014`, `ACC-015`, `ACC-020` |
| TTFT condicionado a validez final | `REQ-TTFT-*` | `ACC-016`, `ACC-017` |
| Estados de informe | `REQ-REPORT-*`, `REQ-COMPLETE-002`–`005`, `REQ-ERROR-003` | `ACC-007`, `ACC-013`, `ACC-020`, `ACC-040`–`ACC-042` |
| Reconstrucción de informes | `REQ-AGG-001`, `REQ-DERIVED-*` | `ACC-018`, `ACC-019`, `ACC-046` |
| JSON Schema como contrato | `REQ-SCHEMA-*`, `REQ-RUNTIME-002`–`005` | `ACC-021`–`ACC-023`, `ACC-033`, `ACC-047` |
| Hypothesis en CI | `REQ-TEST-003`, `REQ-TEST-004` | `ACC-024` |
| statsmodels como oráculo | `REQ-TEST-007`, `REQ-TEST-008` | `ACC-025` |
| Fake Ollama obligatorio | `REQ-TEST-009`–`011` | `ACC-026`, `ACC-032` |
| Cosmic Ray manual | `REQ-TEST-012`, `REQ-TEST-013` | `ACC-027` |
| Incompatibilidad `0.2.0` | `REQ-COMPAT-001`–`004` | `ACC-028` |
| Blindaje sin ampliar benchmark | `REQ-COMPAT-005`, `REQ-DOC-*` | `ACC-030`, `ACC-049` |
| Definición de terminado | Todos | `ACC-001`–`ACC-049` |

## 31. Preguntas no bloqueantes delegables a tickets

Las siguientes decisiones no cambian el comportamiento aprobado y pueden resolverse en tickets:

1. Nombres y rutas exactas del plan, diario, schemas y caches.
2. Dialecto concreto de JSON Schema y forma de sus identificadores locales.
3. Organización física de `$defs` y referencias compartidas.
4. Reutilización física de inputs v2 o publicación de artefactos equivalentes con metadata nueva,
   siempre sin cambiar su semántica ni reescribir históricos.
5. Forma exacta de `run_id`, huella del plan, serialización canónica y algoritmo de hashes donde no
   esté ya fijado por compatibilidad.
6. Algoritmo concreto que construye el calendario cumpliendo las propiedades normativas.
7. Enumeración final de fases y códigos estables del diario de integridad.
8. Representación JSON concreta de `N/D`, siempre separando disponibilidad y valor.
9. Forma y ubicación de procedencia de caches derivados.
10. Mensajes exactos de CLI y códigos de salida, conservando la semántica fail-closed.
11. Tolerancias numéricas y límites de las rejillas de statsmodels.
12. Frecuencia exacta del job de oráculos fuera del requisito de publicación.
13. Parámetros del perfil Hypothesis: `max_examples`, tamaños y health checks justificados.
14. Comandos, selección exacta de funciones y ubicación del informe de Cosmic Ray.
15. Soporte opcional de lectura histórica puramente diagnóstica para `0.2.0`.
16. Nombres internos y transición desde el campo histórico `runner_error`.
17. Si los derivados se recalculan siempre o se permite un cache verificado por defecto.

Ninguna de estas preguntas autoriza cambios en alcance, métricas, pesos, datasets, scorers,
herramientas o dependencias de runtime.

## 32. Further Notes

- Los cinco ADR aceptados gobiernan cualquier ambigüedad de esta especificación.
- La investigación externa justifica los oráculos y patrones, pero ningún framework o dataset
  externo entra en `0.3.0`.
- Los tickets deberán ser tracer bullets pequeños y verificables, con edges de bloqueo explícitos.
- Esta especificación no crea tickets ni modifica código, tests, datasets, configuración o
  dependencias.
