# 12 — Cerrar los contratos restantes y el corpus diferencial

**Identificador:** OAB-0.3.0-12

**What to build:** Formalizar los inputs restantes y demostrar que schemas y validadores runtime
toman las mismas decisiones estructurales sin cambiar el comportamiento en entorno de desarrollo.

**Blocked by:** 11 — Aplicar los tres resultados normativos de informe.

**Status:** ready-for-agent

## Objetivo

Completar la cobertura contractual v3 sin sustituir los validadores definitivos entregados por
tickets anteriores.

## Contexto

ADR 0004 exige JSON Schema local como contrato y validación propia cero-deps en runtime. El oráculo
de desarrollo solo contrasta; nunca participa en operaciones canónicas.

## Requisitos cubiertos

`REQ-SCHEMA-001`–`006`, `REQ-SCHEMA-008`–`010`, `REQ-RUNTIME-002`–`005`,
`REQ-TEST-005`, `REQ-TEST-006`, `REQ-TEST-016` y `REQ-DOC-006`.

## Criterios cubiertos

`ACC-021`–`023`, `ACC-033`, `ACC-047` y `ACC-048`.

## Alcance

- Contratos finales para configuración, lock, casos, fixtures, herramientas y workloads restantes.
- Definiciones compartidas que no fueron necesarias antes.
- Inventario automático de artefactos cubiertos y referencias exclusivamente locales.
- Corpus positivo/negativo estructural y semántico.
- Comparación runtime frente a `jsonschema` solo en desarrollo.
- Paridad de aceptación y salida entre entorno mínimo y entorno dev.

## Fuera de alcance

Modificar contenido de datasets, herramientas, scorers, workloads, reglas de evaluación o añadir
`jsonschema` al runtime.

## Archivos o áreas probablemente afectadas

Contratos locales, validación de inputs y lock, `oab validate`, fixtures de contrato, CI de
desarrollo y documentación de schemas.

## Dependencias

Se ejecuta después de cerrar contratos de plan, registros, diario e informe. Solo completa cobertura
y corpus; no reemplaza su semántica.

## Estrategia de tests

Corpus versionado con ausencias, extras, tipos, límites, versiones, bool/int, null, strings
numéricos, incoherencias cruzadas y ejecución comparativa mínimo/dev totalmente offline.

## Criterios observables de aceptación

- [ ] Todo artefacto acordado tiene schema local identificable y ejemplos positivos/negativos.
- [ ] Runtime y `jsonschema` coinciden en el corpus estructural comparable.
- [ ] Las incoherencias semánticas son rechazadas por la capa runtime correcta.
- [ ] Ningún validador coerciona, completa o elimina datos.
- [ ] Instalar extras de desarrollo no cambia ninguna decisión canónica.

## Riesgos

Crear dos runtimes o alterar contratos ya usados para acomodar el oráculo. Mitigar ejecutando el
mismo corpus y tratando el runtime existente como comportamiento canónico cuando cumple el spec.

## Documentación que debe actualizarse

Documentación de schemas, arquitectura y desarrollo: inventario, estructura frente a semántica y
uso offline del oráculo.

## Comments
