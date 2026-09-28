# 06 — Clasificar fallos y persistir el diario de integridad

**Identificador:** OAB-0.3.0-06

**What to build:** Aplicar la clasificación definitiva entre fallos de ejecución y fallos de
integridad, persistiendo estos últimos en un diario canónico saneado.

**Blocked by:** 04 — Persistir registros funcionales canónicos con fallo cerrado; 05 — Persistir
registros de rendimiento y TTFT canónicos.

**Status:** ready-for-agent

## Objetivo

Evitar tanto penalizar a un modelo por defectos del harness como ocultar fallos medidos del sistema
evaluado.

## Contexto

ADR 0003 fija dos categorías y prohíbe políticas intermedias. Este ticket conecta de una vez la
clasificación final a ambas pistas y entrega el contrato definitivo del diario.

## Requisitos cubiertos

`REQ-STORAGE-006`, `REQ-STORAGE-007`, `REQ-ERROR-001`–`007`, `REQ-RESUME-005`,
`REQ-SCHEMA-001`–`006`, `REQ-SCHEMA-008`–`010`, `REQ-RUNTIME-002`, `REQ-RUNTIME-003`,
`REQ-RUNTIME-005`, `REQ-TEST-002`, `REQ-TEST-009`, `REQ-TEST-010` y `REQ-TEST-015`.

## Criterios cubiertos

`ACC-012`, `ACC-013`, `ACC-043` y `ACC-044`; contribuye a `ACC-026`.

## Alcance

- Tabla de decisión común y conservadora para ambas pistas.
- `execution_failure` como registro terminal que satisface clave y no aporta métricas positivas.
- `benchmark_integrity_failure` como evento que no satisface clave ni penaliza al modelo.
- Schema y validador definitivos del diario, unicidad y append-only.
- Códigos/fases estables, componente, operación, clave opcional y compromiso de persistencia.
- Redacción de credenciales, tokens, URLs con secretos y contenido privado.
- Fallo no cero y ninguna clave completada si no puede persistirse el evento.

## Fuera de alcance

Reanudación exacta, reintentos, reparación, agregación, TTFT completo y política de informe.

## Archivos o áreas probablemente afectadas

Infraestructura común de errores/persistencia, runners funcional y de rendimiento, contratos del
diario, fake Ollama, fault injection y tests de seguridad.

## Dependencias

Requiere que ambos tipos de registro ya puedan validarse y persistirse. El ticket 07 no puede
comenzar hasta que esta semántica final esté integrada.

## Estrategia de tests

Tabla parametrizada de clasificación, HTTP error/timeout/desconexión, defectos del harness,
duplicación/corrupción del diario, secretos ficticios y fallo inyectado en su append.

## Criterios observables de aceptación

- [ ] Cada escenario obtiene exactamente una categoría normativa.
- [ ] Un fallo de ejecución satisface su clave y nunca mejora métricas.
- [ ] Un fallo de integridad deja la clave ausente y hace inelegible el run.
- [ ] Ningún secreto aparece en stderr, diagnóstico o diario.
- [ ] Fallar al guardar el evento termina con código no cero y sin clave completada.

## Riesgos

Clasificar como fallo del modelo una causa ambigua o completar una clave antes de asegurar su
persistencia. Mitigar con clasificación conservadora y orden de escritura probado.

## Documentación que debe actualizarse

Arquitectura, metodología y seguridad: categorías, diario, efectos sobre claves y política de
saneamiento.

## Comments
