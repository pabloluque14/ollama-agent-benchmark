# 08 — Validar íntegramente el stream TTFT

**Identificador:** OAB-0.3.0-08

**What to build:** Reconstruir y validar todo el stream NDJSON antes de considerar oficial el TTFT
observado.

**Blocked by:** 05 — Persistir registros de rendimiento y TTFT canónicos; 06 — Clasificar fallos y
persistir el diario de integridad.

**Status:** ready-for-agent

## Objetivo

Impedir que un primer fragmento rápido obtenga ventaja cuando la respuesta final es truncada,
malformada o incumple el workload.

## Contexto

TTFT comparte contrato de cumplimiento con la respuesta no streaming. Una anomalía debe usar la
clasificación final del ticket 06, no un estado específico improvisado.

## Requisitos cubiertos

`REQ-TTFT-001`–`006`, la parte streaming de `REQ-ERROR-001` y `REQ-ERROR-002`,
`REQ-TEST-001`, `REQ-TEST-002` y `REQ-TEST-009`.

## Criterios cubiertos

`ACC-016` y `ACC-017`; contribuye a `ACC-026`.

## Alcance

- Primer payload significativo: contenido, thinking o tool calls.
- Lectura completa de NDJSON y exigencia de señal final.
- Reconstrucción determinista de respuesta y métricas finales.
- Reutilización de las reglas del workload no streaming.
- TTFT oficial solo cuando la muestra completa sea válida.
- Conservación diagnóstica explícitamente no oficial de tiempos parciales.

## Fuera de alcance

Nuevas métricas de streaming, ITL, throughput, goodput, percentiles o cambios de workloads.

## Archivos o áreas probablemente afectadas

Streaming del runner de rendimiento, validación de workloads, fake Ollama, contrato TTFT y tests de
integración.

## Dependencias

Necesita el formato persistido del ticket 05 y la clasificación definitiva del ticket 06. Puede
avanzar en paralelo con la reanudación del ticket 07.

## Estrategia de tests

Streams fake con líneas vacías, metadatos, payload tardío, tool calls, final aislado, truncamiento,
NDJSON malformado, final ausente e incumplimiento diferencial stream/no-stream.

## Criterios observables de aceptación

- [ ] Solo un payload significativo detiene el reloj TTFT.
- [ ] Un stream truncado, malformado o sin final nunca produce TTFT oficial.
- [ ] La respuesta reconstruida conserva orden y datos observables.
- [ ] Un stream rápido pero incumplidor queda fuera de mediana y score.
- [ ] Ningún test abre red externa ni usa tiempos reales frágiles.

## Riesgos

Detener la lectura tras el primer chunk o duplicar reglas de cumplimiento. Mitigar consumiendo el
stream completo y llamando al validador compartido.

## Documentación que debe actualizarse

Metodología y métricas: payload significativo, validez final, diagnóstico parcial y límites de
TTFT.

## Comments
