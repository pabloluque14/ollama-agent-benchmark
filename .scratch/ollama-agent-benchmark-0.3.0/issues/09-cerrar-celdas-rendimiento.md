# 09 — Cerrar celdas de rendimiento con N/D estricto

**Identificador:** OAB-0.3.0-09

**What to build:** Agregar una celda de rendimiento solo cuando contiene exactamente todas sus
muestras planificadas y válidas; en otro caso producir `N/D`.

**Blocked by:** 05 — Persistir registros de rendimiento y TTFT canónicos; 06 — Clasificar fallos y
persistir el diario de integridad; 08 — Validar íntegramente el stream TTFT.

**Status:** ready-for-agent

## Objetivo

Garantizar que eliminar o invalidar una muestra nunca mejore una métrica ni una puntuación oficial.

## Contexto

La implementación actual puede agregar el subconjunto válido. La especificación exige completitud
estricta por modelo, workload, tipo de medición y métrica.

## Requisitos cubiertos

`REQ-PERF-001`–`006`, `REQ-AGG-002`, `REQ-AGG-003`, `REQ-AGG-006`, `REQ-TEST-001`–`004` y la
parte de celdas de `REQ-TEST-011`.

## Criterios cubiertos

`ACC-014` y `ACC-015`; contribuye a `ACC-020`.

## Alcance

- Identidad exacta y muestras previstas de cada celda.
- Validez por fallo de ejecución, cumplimiento, respuesta, métrica y verificación fría.
- `N/D` ante una sola muestra ausente o inválida.
- Prohibición de agregar subconjuntos o inventar sustitutos.
- Separación de observaciones diagnósticas y valores puntuables.
- Pesos no renormalizados y propiedad monotónica.

## Fuera de alcance

Cambiar pesos, fórmulas, workloads, métricas oficiales o decidir los estados finales del informe.

## Archivos o áreas probablemente afectadas

Agregación de rendimiento, scoring existente, representación de disponibilidad y tests
estadísticos/de propiedades.

## Dependencias

Requiere registros canónicos, taxonomía de fallos y validez TTFT completa.

## Estrategia de tests

Matriz de celdas completa/incompleta, muestras inválidas por cada causa y propiedad metamórfica que
sustituye éxito por ausencia/fallo sin permitir mejora.

## Criterios observables de aceptación

- [ ] Una celda oficial contiene exactamente sus muestras planificadas.
- [ ] Una sola muestra inválida convierte la métrica de la celda en `N/D`.
- [ ] `N/D` nunca se convierte en cero, infinito o valor observado.
- [ ] Los pesos no se renormalizan por componentes ausentes.
- [ ] Invalidar una muestra nunca mejora métrica ni score.

## Riesgos

Aplicar la regla después de calcular medianas o confundir muestra inválida con TTFT no planificado.
Mitigar validando claves primero y respetando `ttft_runs = 0`.

## Documentación que debe actualizarse

Metodología, métricas y limitaciones: celda de rendimiento, `N/D`, completitud y monotonicidad.

## Comments
