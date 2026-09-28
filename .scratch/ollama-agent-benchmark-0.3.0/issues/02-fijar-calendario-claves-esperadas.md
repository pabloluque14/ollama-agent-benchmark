# 02 — Fijar el calendario equilibrado y las claves esperadas

**Identificador:** OAB-0.3.0-02

**What to build:** Completar el plan con un calendario determinista por bloque experimental y con
el conjunto exacto de claves esperadas para ambas pistas.

**Blocked by:** 01 — Materializar el plan del run v3 y los modos efectivos.

**Status:** ready-for-agent

## Objetivo

Eliminar el sesgo dependiente del orden configurado y convertir completitud e idempotencia en
propiedades reconstruibles.

## Contexto

ADR 0005 exige equilibrio por caso o por combinación workload/tipo. ADR 0002 exige comparar el
multiconjunto observado con claves planificadas, no con el número de filas.

## Requisitos cubiertos

`REQ-MODE-003`, `REQ-SCHEDULE-001`–`006`, `REQ-KEY-001`, `REQ-KEY-002`, `REQ-TEST-001`,
`REQ-TEST-003`, `REQ-TEST-004` y la parte de planificación de `REQ-TEST-014`.

## Criterios cubiertos

`ACC-003`–`006` y `ACC-039`.

## Alcance

- Función pura y versionada para calendario funcional, rendimiento y TTFT.
- Equilibrio exacto cuando sea posible y diferencia máxima de uno en otro caso.
- Seed para posiciones sobrantes, sin aumentar repeticiones.
- Claves sin colisiones que incorporen identidad, caso/workload, repetición, tipo y posición.
- Reconstrucción y validación independiente desde el plan.
- Ausencia total de claves y celdas TTFT cuando `ttft_runs = 0`.

## Fuera de alcance

Balance completo de precedencias, optimización térmica, ejecución, persistencia y reanudación.

## Archivos o áreas probablemente afectadas

Planificación compartida, runners funcional y de rendimiento, contratos del plan y tests de
propiedades.

## Dependencias

Requiere el contrato definitivo y la materialización del plan entregados por el ticket 01.

## Estrategia de tests

Propiedades sobre permutación de modelos, determinismo, cotas de frecuencia, unicidad de claves,
tamaños pequeños exhaustivos y conteos con cero TTFT.

## Criterios observables de aceptación

- [ ] Misma seed e identidades producen el mismo calendario.
- [ ] Permutar la configuración no cambia asignaciones por identidad.
- [ ] Cada bloque cumple igualdad posible o diferencia máxima de uno.
- [ ] Un validador independiente reconstruye exactamente las claves del plan.
- [ ] Un calendario mutado se rechaza antes de cualquier petición HTTP.

## Riesgos

Confundir equilibrio global con equilibrio por bloque o incorporar la posición configurada a la
identidad. Mitigar con propiedades nombradas en términos del dominio.

## Documentación que debe actualizarse

Metodología y arquitectura: bloque experimental, algoritmo versionado, seed, claves y límites del
equilibrio.

## Comments
