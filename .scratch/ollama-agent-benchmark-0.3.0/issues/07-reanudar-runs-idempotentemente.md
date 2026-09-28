# 07 — Reanudar runs de forma exacta e idempotente

**Identificador:** OAB-0.3.0-07

**What to build:** Reanudar ambas pistas exclusivamente desde el plan original y la evidencia
validada, ejecutando solo claves realmente ausentes.

**Blocked by:** 06 — Clasificar fallos y persistir el diario de integridad.

**Status:** ready-for-agent

## Objetivo

Hacer que cualquier reanudación válida sea equivalente a completar el mismo plan sin repetir,
sobrescribir ni seleccionar resultados.

## Contexto

La reanudación solo puede distinguir una clave terminal de un fallo de integridad después de que la
clasificación y el diario definitivos existan. Por eso este ticket sigue, y no precede, al 06.

## Requisitos cubiertos

`REQ-PLAN-004`, `REQ-MODE-004`, `REQ-COMPLETE-001`–`004`, `REQ-RESUME-001`–`006`,
`REQ-FAILCLOSED-001`, `REQ-FAILCLOSED-004`, `REQ-TEST-001`–`003`, `REQ-TEST-010` y
`REQ-TEST-014`.

## Criterios cubiertos

`ACC-007`–`009` y `ACC-035`.

## Alcance

- Carga y validación completa del plan, registros y diario antes de contactar con Ollama.
- Comparación exacta de multiconjuntos de claves.
- Ejecución exclusiva de ausencias en el orden original.
- `execution_failure` terminal no reintentado; evento de integridad sin clave completada.
- Rechazo de modo, overrides, calendario o identidad distintos.
- Rechazo de duplicados, inesperadas y corrupción sin reparación.

## Fuera de alcance

Reintentos automáticos, migración de `0.2.0`, reparación de evidencia y recalcular calendarios.

## Archivos o áreas probablemente afectadas

Runners funcional y de rendimiento, validación de evidencia compartida, CLI de resume y tests
stateful.

## Dependencias

Depende transitivamente de plan, claves, persistencia y preflight, y directamente de la taxonomía y
diario finales del ticket 06.

## Estrategia de tests

Propiedades stateful con prefijos y subconjuntos, run completo como no-op, overrides mutados,
duplicados contiguos/no contiguos, claves inesperadas, corrupción y conteo cero de llamadas fake al
rechazar.

## Criterios observables de aceptación

- [ ] Cualquier subconjunto válido termina con cada clave exactamente una vez.
- [ ] Reanudar un run completo no modifica bytes ni llama a Ollama.
- [ ] Un modo u override distinto falla antes de escribir.
- [ ] Duplicados, claves inesperadas, corrupción o diario de integridad detienen la operación.
- [ ] El calendario de pendientes coincide exactamente con el plan original.

## Riesgos

Reducir registros a un set y ocultar duplicados, o validar después de iniciar red/escritura. Mitigar
con multiconjunto exacto y una única puerta de validación previa.

## Documentación que debe actualizarse

README, metodología y limitaciones: semántica de resume, no-op, causas de rechazo y ausencia de
reparación.

## Comments
