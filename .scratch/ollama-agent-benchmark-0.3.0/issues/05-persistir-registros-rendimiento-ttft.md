# 05 — Persistir registros de rendimiento y TTFT canónicos

**Identificador:** OAB-0.3.0-05

**What to build:** Extender la persistencia canónica a rendimiento y TTFT con contratos definitivos
y claves calculadas desde workloads y cantidades efectivas.

**Blocked by:** 02 — Fijar el calendario equilibrado y las claves esperadas; 03 — Bloquear el
preflight contra la identidad materializada; 04 — Persistir registros funcionales canónicos con
fallo cerrado.

**Status:** ready-for-agent

## Objetivo

Completar la base de registros primarios v3 reutilizando exactamente la semántica fail-closed ya
probada en la pista funcional.

## Contexto

Rendimiento y TTFT tienen claves y payloads distintos, pero no justifican otro almacenamiento ni
otra política de corrupción. Los contratos deben existir antes de integrar clasificación y resume.

## Requisitos cubiertos

`REQ-MODE-003`, `REQ-MODE-006`, `REQ-MODE-007`, `REQ-KEY-003`, `REQ-KEY-004`,
`REQ-STORAGE-002`–`005`, `REQ-SCHEMA-001`, `REQ-SCHEMA-002`, `REQ-SCHEMA-004`–`006`,
`REQ-SCHEMA-008`–`010`, `REQ-RUNTIME-002`, `REQ-RUNTIME-003`, `REQ-TEST-001`–`003` y la parte de
modos/persistencia de `REQ-TEST-014`.

## Criterios cubiertos

`ACC-033`, `ACC-037`–`039` y `ACC-047`.

## Alcance

- Schemas y validadores runtime definitivos de registros de rendimiento y TTFT.
- Persistencia compartida con funcional, sin lectores permisivos alternativos.
- Workloads y conteos efectivos fijados por el plan.
- Evidencia exploratoria marcada como no oficial en `smoke`.
- Evidencia potencialmente elegible solo en `official-performance`.
- Cero claves, registros o celdas TTFT planificadas cuando `ttft_runs = 0`.

## Fuera de alcance

Clasificación de excepciones, diario de integridad, validación completa del stream, agregación por
celda, scoring e informes.

## Archivos o áreas probablemente afectadas

Runner de rendimiento, infraestructura común, contratos de rendimiento/TTFT, fake Ollama y tests de
integración.

## Dependencias

Reutiliza plan/claves de 02, preflight de 03 y almacenamiento fail-closed de 04. No introduce
campos o validadores de error destinados a ser sustituidos.

## Estrategia de tests

Integración fake para cold/hot/TTFT persistidos, contratos negativos, conteos efectivos, separación
smoke/official y caso `ttft_runs = 0`.

## Criterios observables de aceptación

- [ ] Cada registro referencia plan, clave y tipo de medición compatibles.
- [ ] Rendimiento y TTFT usan el mismo fallo cerrado que funcional.
- [ ] `smoke` queda inequívocamente no oficial.
- [ ] Solo `official-performance` produce evidencia potencialmente elegible.
- [ ] `ttft_runs = 0` no crea ausencia, fallo ni `N/D`.

## Riesgos

Duplicar el parser funcional o adelantar las reglas de validez TTFT. Mitigar reutilizando la
persistencia común y dejando la semántica streaming al ticket 08.

## Documentación que debe actualizarse

Arquitectura, metodología y métricas: formatos primarios, modos y efecto exacto de
`ttft_runs = 0`.

## Comments
