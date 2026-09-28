# 11 — Aplicar los tres resultados normativos de informe

**Identificador:** OAB-0.3.0-11

**What to build:** Producir exactamente un informe oficial, un diagnóstico no oficial o un rechazo
sin informe según el estado validado del run.

**Blocked by:** 06 — Clasificar fallos y persistir el diario de integridad; 10 — Regenerar
artefactos derivados desde evidencia canónica.

**Status:** ready-for-agent

## Objetivo

Eliminar cualquier interpretación alternativa sobre elegibilidad, `N/D`, scores y ranking.

## Contexto

La salida depende de dos ejes ya cerrados: integridad de la evidencia y disponibilidad de
componentes. Corrupción estructural no equivale a un evento legible de integridad.

## Requisitos cubiertos

`REQ-COMPLETE-005`, `REQ-AGG-004`, `REQ-REPORT-001`–`003`, `REQ-SCHEMA-007`,
`REQ-SCHEMA-009`, `REQ-SCHEMA-010`, `REQ-RUNTIME-002`, `REQ-RUNTIME-003`,
`REQ-TEST-001`, `REQ-TEST-002` y `REQ-TEST-011`.

## Criterios cubiertos

`ACC-020` y `ACC-040`–`042`.

## Alcance

- Contrato y validador definitivos para informe oficial y diagnóstico no oficial.
- Run elegible: informe oficial, `N/D` permitido y ranking solo con todos los componentes.
- `benchmark_integrity_failure` legible: diagnóstico no oficial sin scores/ranking oficiales.
- Duplicados, inesperadas, corrupción o incompatibilidad estructural: rechazo sin ningún informe.
- Estado, elegibilidad, disponibilidad y procedencia explícitos en JSON y presentaciones.

## Fuera de alcance

Reparación, informes aproximados históricos, ranking parcial, renormalización o nuevas métricas.

## Archivos o áreas probablemente afectadas

Generador de informes JSON/CSV/Markdown/SVG, validación de evidencia, contratos de informe y tests
de integración.

## Dependencias

Necesita la semántica definitiva del diario y la reconstrucción desde evidencia canónica.

## Estrategia de tests

Matriz end-to-end con run elegible completo, elegible con `N/D`, fallo de integridad, duplicado,
clave inesperada, JSONL corrupto e incompatibilidad estructural.

## Criterios observables de aceptación

- [ ] Un run elegible puede producir informe oficial con `N/D`.
- [ ] Falta de componente requerido elimina el ranking global.
- [ ] Un evento de integridad solo permite diagnóstico no oficial y sin scores oficiales.
- [ ] Evidencia incompatible o corrupta no genera JSON, CSV, Markdown ni SVG.
- [ ] Un diagnóstico no valida contra el contrato de informe oficial.

## Riesgos

Usar “diagnóstico” para un informe oficial incompleto o generar parcialmente antes de validar.
Mitigar decidiendo el estado antes de escribir cualquier salida.

## Documentación que debe actualizarse

README, metodología, métricas y arquitectura: matriz de estados, `N/D`, scores y ranking.

## Comments
