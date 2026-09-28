# 14 — Sellar compatibilidad, documentación y release 0.3.0

**Identificador:** OAB-0.3.0-14

**What to build:** Cerrar el protocolo 0.3.0 como release coherente, incompatible de forma explícita
con `0.2.0`, documentado en español y verificable en entornos mínimo y de desarrollo.

**Blocked by:** 11 — Aplicar los tres resultados normativos de informe; 12 — Cerrar los contratos
restantes y el corpus diferencial; 13 — Contrastar la estadística con oráculos independientes.

**Status:** ready-for-agent

## Objetivo

Aplicar la definición de terminado de `0.3.0` sin ampliar el benchmark ni depender del prototipo
experimental de Cosmic Ray.

## Contexto

Los formatos y reglas v3 son incompatibles con `0.2.0`. AGENTS.md exige tests, validación, Ruff,
Mypy, cobertura, documentación española y runtime sin dependencias.

## Requisitos cubiertos

`REQ-DERIVED-006`, `REQ-RUNTIME-001`, `REQ-RUNTIME-004`, `REQ-COMPAT-001`–`006`,
`REQ-DOC-001`–`007`, `REQ-TEST-001`–`006`, `REQ-TEST-009`–`011`, `REQ-TEST-014`–`016`.

## Criterios cubiertos

`ACC-024`, `ACC-026`, `ACC-028`–`032`, `ACC-048` y `ACC-049`. `ACC-027` queda expresamente fuera
de este cierre.

## Alcance

- Identidades `benchmark_version: 0.3.0` y `schema_version: 3`.
- Rechazo de reanudación, mezcla, migración e informe v3 sobre evidencia `0.2.0`.
- Prohibición de combinar protocolos o aproximar informes históricos.
- Inventario comparativo que confirme casos, herramientas, scorers, pesos y métricas sin cambios.
- Documentación española completa, incluido `docs/security.md`.
- Suite normal, `oab validate`, Ruff, Mypy, cobertura y jobs mínimo/dev.
- Confirmación de `dependencies = []` y cero Ollama real/red/GPU en tests.

## Fuera de alcance

Migradores, lectura reparadora, nuevos datasets/scorers/métricas, Inspect AI, GuideLLM y Cosmic Ray.

## Archivos o áreas probablemente afectadas

Metadata de paquete, compatibilidad de CLI/lectores/informe, CI, tests históricos, README y
documentación de arquitectura, metodología, métricas, limitaciones, migración, seguridad y schemas.

## Dependencias

Es el último ticket del camino crítico. No depende del ticket 15 y puede cerrar/publicar `0.3.0`
aunque la campaña Cosmic Ray no se haya ejecutado.

## Estrategia de tests

Fixtures históricos, instalación mínima, matriz mínimo/dev, fake Ollama completo, inventario de
inputs y ejecución de todos los comandos de definición de terminado de AGENTS.md.

## Criterios observables de aceptación

- [ ] Todo intento de usar `0.2.0` como `0.3.0` se rechaza explícitamente.
- [ ] No cambian casos, herramientas, scorers, confirmaciones, pesos ni métricas oficiales.
- [ ] `dependencies = []` permanece y el entorno mínimo ejecuta la CLI.
- [ ] Entorno mínimo y dev producen decisiones semánticamente idénticas.
- [ ] Tests, validación, Ruff, Mypy y cobertura pasan sin Ollama real ni red externa.
- [ ] Toda documentación de comportamiento está actualizada en español, incluido seguridad.

## Riesgos

Convertir el cierre en un refactor amplio o hacer depender release de herramientas experimentales.
Mitigar limitando cambios a compatibilidad, documentación y gates aprobados.

## Documentación que debe actualizarse

Toda la documentación normativa española afectada por v3, especialmente README, arquitectura,
metodología, métricas, limitaciones, migración, seguridad y contratos.

## Comments
