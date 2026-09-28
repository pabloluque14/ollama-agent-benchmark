# 03 — Bloquear el preflight contra la identidad materializada

**Identificador:** OAB-0.3.0-03

**What to build:** Verificar contra el plan la versión de Ollama y las identidades bloqueadas de los
modelos antes de permitir una medición.

**Blocked by:** 01 — Materializar el plan del run v3 y los modos efectivos.

**Status:** ready-for-agent

## Objetivo

Impedir que un run mida un servidor o artefacto distinto del aprobado en su plan.

## Contexto

El lock deja de ser una referencia consultada libremente durante la ejecución: el preflight debe
comparar el estado observable con la identidad ya materializada.

## Requisitos cubiertos

`REQ-PLAN-005`, la validación previa de `REQ-PLAN-001`, `REQ-TEST-009` y la parte de preflight de
`REQ-TEST-014`.

## Criterios cubiertos

`ACC-045`; contribuye a `ACC-026` y `ACC-032`.

## Alcance

- Comparación de versión de Ollama y digest/nombre canónico de cada modelo contra el plan.
- Rechazo antes de medir o completar claves.
- Diagnóstico localizable y saneado.
- Integración exclusivamente con fake Ollama y URL localhost efímera.

## Fuera de alcance

Crear locks, consultar Ollama real, corregir identidades, reanudar runs o clasificar fallos
posteriores al preflight.

## Archivos o áreas probablemente afectadas

Preflight, integración de CLI/runners, fake Ollama y tests de identidad.

## Dependencias

Solo necesita el plan v3 del ticket 01; puede desarrollarse en paralelo con el ticket 02.

## Estrategia de tests

Matriz fake con versión correcta/incorrecta, digest correcto/incorrecto, modelo ausente y cero
peticiones de medición tras el rechazo.

## Criterios observables de aceptación

- [ ] Una versión distinta devuelve error antes de medir.
- [ ] Un digest distinto devuelve error antes de medir.
- [ ] Ningún rechazo completa claves o modifica el plan.
- [ ] Los tests no requieren Ollama real, red externa, GPU ni modelos.

## Riesgos

Comparar contra configuración actual o filtrar una URL con secretos en el diagnóstico. Mitigar
leyendo solo el plan y reutilizando el saneamiento público de URL.

## Documentación que debe actualizarse

Metodología, README y seguridad: preflight bloqueante, identidad exacta y uso exclusivo de fake
Ollama en pruebas.

## Comments
