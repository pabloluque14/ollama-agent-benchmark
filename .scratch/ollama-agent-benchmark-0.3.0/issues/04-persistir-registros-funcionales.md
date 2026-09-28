# 04 — Persistir registros funcionales canónicos con fallo cerrado

**Identificador:** OAB-0.3.0-04

**What to build:** Persistir y leer registros funcionales v3 válidos mediante un almacenamiento
append-only que rechace corrupción sin reparar ni reinterpretar evidencia.

**Blocked by:** 02 — Fijar el calendario equilibrado y las claves esperadas; 03 — Bloquear el
preflight contra la identidad materializada.

**Status:** ready-for-agent

## Objetivo

Crear el primer tracer bullet de registro primario canónico y la infraestructura compartida de
persistencia fail-closed.

## Contexto

ADR 0001 convierte los registros en evidencia canónica; ADR 0002 prohíbe lecturas best-effort. Este
ticket cierra el formato funcional, pero no inventa una clasificación transitoria de excepciones.

## Requisitos cubiertos

`REQ-MODE-006`, `REQ-MODE-007`, `REQ-KEY-003`, `REQ-KEY-004`, `REQ-STORAGE-002`–`005`,
`REQ-FAILCLOSED-001`–`005`, `REQ-SCHEMA-001`, `REQ-SCHEMA-002`,
`REQ-SCHEMA-004`–`006`, `REQ-SCHEMA-008`–`010`, `REQ-RUNTIME-002`,
`REQ-RUNTIME-003`, `REQ-RUNTIME-005`, `REQ-TEST-001`–`003` y la parte de persistencia de
`REQ-TEST-010`.

## Criterios cubiertos

`ACC-010`, `ACC-011`, `ACC-033`, `ACC-037`, `ACC-038` y `ACC-047`.

## Alcance

- Schema y validador runtime definitivos del registro funcional v3.
- Validación y serialización completas antes de append; flush y `fsync` tras escribir.
- Asociación inequívoca con plan y clave esperada.
- Parser uniforme para JSON/JSONL inválido, UTF-8, líneas vacías y truncamiento.
- Diagnóstico con artefacto, línea y causa disponibles sin modificar el original.
- Resultados `smoke` funcionales no oficiales y evidencia potencialmente elegible solo en
  `official-functional`.
- El almacenamiento acepta estados terminales explícitos y rechaza errores sin clasificar.

## Fuera de alcance

Mapear excepciones a `execution_failure` o `benchmark_integrity_failure`, crear el diario, reanudar,
agregar resultados o reparar JSONL.

## Archivos o áreas probablemente afectadas

Infraestructura común de JSON/JSONL, runner funcional, contratos de registros, tests funcionales y
fault injection.

## Dependencias

Necesita claves finales del ticket 02 y preflight bloqueante del ticket 03. El ticket 06 conectará
la política definitiva de errores; no se añade `runner_error` v3 ni otro formato provisional.

## Estrategia de tests

Corpus positivo/negativo, append durable simulado, corrupción por clase, preservación de bytes y
tracer funcional exitoso con fake Ollama.

## Criterios observables de aceptación

- [ ] Un resultado funcional válido queda asociado a una única clave del plan.
- [ ] Un objeto inválido nunca inicia el append.
- [ ] Una línea parcial invalida la lectura y no se consume el prefijo.
- [ ] El rechazo informa ubicación y conserva exactamente el artefacto original.
- [ ] `smoke` funcional nunca produce evidencia oficial y `official-functional` conserva su modo.
- [ ] No existe una política de errores provisional ni coerción de registros.

## Riesgos

Compartir utilidades que sigan aceptando silenciosamente diccionarios incompletos o mezclar el
formato histórico. Mitigar haciendo del validador v3 la única entrada al append canónico.

## Documentación que debe actualizarse

Arquitectura, metodología y limitaciones: registro primario funcional, append-only y coste del
fallo cerrado.

## Comments
