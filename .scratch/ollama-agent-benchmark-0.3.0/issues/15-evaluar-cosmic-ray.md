# 15 — Evaluar Cosmic Ray mediante una campaña manual

**Identificador:** OAB-0.3.0-15

**What to build:** Ejecutar, después de estabilizar la suite, un prototipo manual y reproducible de
mutation testing sobre lógica pura crítica.

**Blocked by:** 13 — Contrastar la estadística con oráculos independientes.

**Status:** ready-for-agent

## Objetivo

Medir si Cosmic Ray descubre huecos útiles antes de considerar cualquier adopción futura.

## Contexto

ADR 0004 y la especificación lo definen como experimento sin umbral ni gate. La aprobación del
desglose aclara que no forma parte de la definición de terminado ni del camino crítico de `0.3.0`.

## Requisitos cubiertos

`REQ-TEST-012` y `REQ-TEST-013`.

## Criterios cubiertos

`ACC-027`, únicamente como aceptación de este ticket experimental y no como gate del release.

## Alcance

- Selección pequeña de lógica pura crítica ya estabilizada.
- Registro de versión, comandos, alcance, coste, mutantes y supervivientes.
- Clasificación de supervivientes como huecos reales, equivalentes o incompatibles.
- Informe reproducible de la campaña manual.
- Confirmación explícita de que no existe score mínimo ni gate de CI.

## Fuera de alcance

Bloquear publicación, modificar la definición de terminado, mutar runners con red/disco, adoptar
otra herramienta sin aprobación o añadir dependencias de runtime.

## Archivos o áreas probablemente afectadas

Configuración experimental de desarrollo y un informe de campaña no canónico; no toca el protocolo
ni los artefactos de un run.

## Dependencias

Solo requiere la suite estabilizada por el ticket 13. No bloquea el ticket 14, el cierre ni la
publicación de `0.3.0`; ambos pueden avanzar en paralelo una vez satisfechos sus blockers.

## Estrategia de tests

La campaña es la evidencia. Debe poder repetirse con versión y selección fijadas, sin red, Ollama,
GPU ni modelos, y dejar intacta la suite cuando no se ejecuta.

## Criterios observables de aceptación

- [ ] Existe un informe con versión, alcance, comandos, duración y resultados.
- [ ] Los supervivientes están clasificados y los huecos reales son accionables.
- [ ] La ausencia o fallo de Cosmic Ray no afecta CI ni release.
- [ ] No se establece score mínimo.
- [ ] `dependencies = []` permanece.

## Riesgos

Coste alto, mutantes equivalentes o incompatibilidad con Python. Mitigar limitando el alcance y
documentando el resultado sin sustituir la herramienta por otra.

## Documentación que debe actualizarse

Solo documentación de desarrollo o el informe experimental; ninguna afirmación normativa del
protocolo cambia.

## Comments
