# 13 — Contrastar la estadística con oráculos independientes

**Identificador:** OAB-0.3.0-13

**What to build:** Verificar las implementaciones existentes de Wilson y McNemar exacto frente a
statsmodels sin delegarle la política oficial.

**Blocked by:** 09 — Cerrar celdas de rendimiento con N/D estricto; 12 — Cerrar los contratos
restantes y el corpus diferencial.

**Status:** ready-for-agent

## Objetivo

Detectar errores conceptuales en las fórmulas manteniendo la biblioteca estándar como runtime.

## Contexto

ADR 0004 permite statsmodels únicamente en un job de desarrollo separado. Los casos dorados y las
propiedades locales siguen definiendo el comportamiento esperado.

## Requisitos cubiertos

`REQ-TEST-007` y `REQ-TEST-008`; completa la cobertura estadística de `REQ-TEST-001`.

## Criterios cubiertos

`ACC-025`.

## Alcance

- Rejillas y extremos de Wilson.
- Simetría, discordancias y casos sin observaciones de McNemar exacto.
- Tolerancias explícitas y diagnósticos con inputs/diferencias.
- Casos dorados independientes del oráculo.
- Job de desarrollo separado, offline y no requerido por el paquete.

## Fuera de alcance

Cambiar fórmulas oficiales, añadir métricas, Holm, bootstrap, tamaños de efecto o dependencias de
runtime.

## Archivos o áreas probablemente afectadas

Tests estadísticos, configuración del job de oráculos y extras exclusivamente de desarrollo.

## Dependencias

Necesita la política final de disponibilidad y el entorno de contratos/oráculos ya establecido.

## Estrategia de tests

Comparación parametrizada contra statsmodels, extremos exactos, simetrías y golden tests ejecutables
sin statsmodels en la suite mínima.

## Criterios observables de aceptación

- [ ] Wilson coincide dentro de tolerancias declaradas en rejillas y extremos.
- [ ] McNemar coincide en casos discordantes, simétricos y sin observaciones.
- [ ] Un fallo informa inputs, resultado propio, resultado del oráculo y diferencia.
- [ ] La suite mínima conserva golden tests sin instalar statsmodels.
- [ ] `dependencies = []` no cambia.

## Riesgos

Convertir una diferencia de versión del oráculo en cambio automático del protocolo. Mitigar
manteniendo expectativas doradas y revisión explícita de divergencias.

## Documentación que debe actualizarse

Metodología de desarrollo y referencias: alcance, versión, tolerancias y carácter no normativo del
oráculo.

## Comments
