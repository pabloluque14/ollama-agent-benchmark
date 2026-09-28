# 10 — Regenerar artefactos derivados desde evidencia canónica

**Identificador:** OAB-0.3.0-10

**What to build:** Reconstruir agregados y presentaciones exclusivamente desde el plan, registros
primarios y diario validados, descartando derivados contradictorios u obsoletos.

**Blocked by:** 07 — Reanudar runs de forma exacta e idempotente; 09 — Cerrar celdas de rendimiento
con N/D estricto.

**Status:** ready-for-agent

## Objetivo

Eliminar la autoridad de resúmenes persistidos y hacer reproducible cualquier salida derivada.

## Contexto

ADR 0001 declara que informes, resúmenes, scores y caches son regenerables. Un derivado nunca puede
completar evidencia ni cambiar la interpretación del run.

## Requisitos cubiertos

`REQ-AGG-001`, `REQ-AGG-005`, `REQ-DERIVED-001`–`005`, `REQ-TEST-001`–`003` y los escenarios de
cache divergente de `REQ-TEST-011`.

## Criterios cubiertos

`ACC-018`, `ACC-019` y `ACC-046`.

## Alcance

- Agregación desde evidencia primaria validada y reglas fijadas por el plan.
- Regeneración de derivados ausentes.
- Verificación de run, huella del plan, hashes y versiones antes de usar cache.
- Detección, descarte y regeneración de derivados obsoletos o contradictorios.
- Rechazo sin informe cuando la discrepancia revele corrupción canónica.
- Preservación de hashes, identidad y fechas originales.

## Fuera de alcance

Definir la matriz final de informe, reparar evidencia, reinterpretar `0.2.0` o cambiar scoring.

## Archivos o áreas probablemente afectadas

Generador de informes, agregadores funcional/rendimiento, procedencia de caches y tests end-to-end.

## Dependencias

Necesita lectura completa/idempotente de evidencia y política final de celdas.

## Estrategia de tests

Runs sin derivados, caches con plan/hash/versión mutados, derivado contradictorio con evidencia
íntegra, corrupción primaria y comparación de hashes antes/después.

## Criterios observables de aceptación

- [ ] Eliminar todos los derivados no cambia el informe semántico regenerado.
- [ ] Un cache sin procedencia o divergente no participa.
- [ ] Un derivado obsoleto se detecta y regenera.
- [ ] Una contradicción primaria produce rechazo, no regeneración encubridora.
- [ ] Regenerar no modifica ningún artefacto canónico.

## Riesgos

Conservar dependencias implícitas de resúmenes o tratar un cache como fallback. Mitigar probando el
seam plan+evidencia sin ningún derivado previo.

## Documentación que debe actualizarse

Arquitectura y README: evidencia canónica, derivados regenerables y política de caches.

## Comments
