# 01 — Materializar el plan del run v3 y los modos efectivos

**Identificador:** OAB-0.3.0-01

**What to build:** Materializar y validar el plan del run v3 antes de cualquier medición, fijando el
modo y todos los valores efectivos sin convertir `dry-run` en evidencia de ejecución.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

## Objetivo

Disponer de una única descripción durable, inmutable y auditable de lo que ejecutará un run.

## Contexto

ADR 0001 hace canónico el plan y prohíbe reconstruirlo desde la configuración actual. El contrato y
el validador necesarios deben quedar cerrados en este ticket; no se admite un manifest provisional.

## Requisitos cubiertos

`REQ-PLAN-001`–`003`, `REQ-PLAN-006`, `REQ-MODE-001`, `REQ-MODE-002`, `REQ-MODE-005`,
`REQ-STORAGE-001`, `REQ-SCHEMA-001`, `REQ-SCHEMA-002`, `REQ-SCHEMA-004`–`006`,
`REQ-SCHEMA-008`–`010`, `REQ-RUNTIME-002`, `REQ-RUNTIME-003`, `REQ-RUNTIME-005`,
`REQ-TEST-001`, `REQ-TEST-003`, `REQ-TEST-004` y `REQ-TEST-014`.

## Criterios cubiertos

`ACC-001`, `ACC-002`, `ACC-033`, `ACC-034`, `ACC-036` y `ACC-047`.

## Alcance

- Contrato JSON Schema v3 y validador runtime definitivos para inputs de planificación y plan.
- Resolución de defaults, configuración y overrides antes de calcular el plan.
- Identidades de protocolo, implementación y algoritmos; hashes y valores metodológicos efectivos.
- Escritura atómica y durable del plan oficial, con rechazo de sobrescritura.
- Previsualización `dry-run` no reanudable, sin registros ni diario de ejecución.

## Fuera de alcance

Calendario y claves, preflight, registros primarios, reanudación, agregación y cualquier cambio de
dataset, scorer, pesos o métricas.

## Archivos o áreas probablemente afectadas

CLI funcional y de rendimiento, infraestructura común de JSON, nuevos contratos locales, tests de
planificación y documentación de configuración.

## Dependencias

Ninguna. Abre el frontier de implementación de `0.3.0`.

## Estrategia de tests

Unitarios y propiedades sobre materialización, round-trip, campos ausentes/extra y orden de
resolución; integración CLI que demuestre cero mediciones en `dry-run`. Todo offline.

## Criterios observables de aceptación

- [ ] Ninguna ruta de medición puede comenzar sin un plan v3 válido y durable.
- [ ] Repetir la materialización no altera los bytes originales.
- [ ] El plan conserva modo, valores efectivos, procedencia, versiones y hashes requeridos.
- [ ] `dry-run` no crea evidencia canónica de ejecución ni contacta con Ollama para medir.
- [ ] Schema y runtime rechazan datos sin coerciones, defaults silenciosos o campos desconocidos.

## Riesgos

Omitir un valor que cambie la interpretación o hacer depender el plan del orden de serialización.
Mitigar con inventario normativo, serialización estable y fixtures positivos/negativos.

## Documentación que debe actualizarse

README, arquitectura y configuración de modelos: ciclo de vida del plan, modos y semántica de
`dry-run`.

## Comments
