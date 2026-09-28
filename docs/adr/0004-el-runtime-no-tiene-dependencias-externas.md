# El runtime no tiene dependencias externas

## Estado

Aceptada.

## Contexto

El proyecto mantiene un runtime ligero y offline con `dependencies = []`. El blindaje de `0.3.0`
necesita contratos formales, pruebas generativas y oráculos independientes, pero incorporar toda esa
pila al runtime aumentaría instalación, superficie de fallo y acoplamiento sin mejorar la ejecución
normal de `oab`.

Esta versión se limita a la integridad del protocolo actual. Inspect AI, GuideLLM, la ampliación del
dataset funcional, nuevos scorers, concurrencia, throughput y nuevas métricas estadísticas
oficiales quedan fuera de alcance.

## Decisión

Los formatos canónicos se definirán mediante JSON Schema local, estricto y versionado. El runtime
mantendrá validadores propios y ligeros que rechacen campos ausentes o inesperados, tipos o límites
incorrectos, versiones incompatibles y las invariantes semánticas que JSON Schema no pueda
expresar. No habrá coerciones, defaults silenciosos ni eliminación de datos desconocidos.

Las herramientas externas se limitarán a desarrollo:

- `jsonschema` será el oráculo diferencial de los contratos estructurales;
- Hypothesis probará propiedades puras, deterministas y rápidas en CI;
- statsmodels comprobará Wilson y McNemar en un job de oráculos separado;
- Cosmic Ray se evaluará mediante un prototipo manual posterior a la estabilización de la suite.

Ninguna de estas dependencias será necesaria para instalar el paquete, ejecutar, reanudar o generar
informes. La presencia de un entorno de desarrollo no cambiará el comportamiento canónico.

## Consecuencias positivas

- Los usuarios conservan una instalación mínima, local y sin dependencias obligatorias.
- Los contratos pueden auditarse con un estándar independiente sin crear dos runtimes distintos.
- Las fórmulas y validadores propios se contrastan contra oráculos externos reproducibles.
- Hypothesis amplía la cobertura combinatoria sin generar el dataset oficial.
- El coste del mutation testing se mide antes de convertirlo en obligación permanente.

## Costes y limitaciones

- Los validadores runtime y los schemas formales deben mantenerse sincronizados.
- La suite necesita un corpus diferencial positivo y negativo suficientemente amplio.
- El job de statsmodels instala una pila científica pesada aunque no afecte a usuarios.
- Cosmic Ray puede producir mutantes equivalentes o incompatibilidades y no tendrá inicialmente un
  umbral de aceptación.

## Alternativas rechazadas

- Añadir `jsonschema` o statsmodels como dependencias de runtime.
- Habilitar validación distinta cuando una dependencia opcional esté instalada.
- Delegar la estadística oficial a statsmodels.
- Sustituir tests diseñados por generación automática de casos funcionales.
- Convertir mutation testing en gate de CI antes de completar el prototipo.
- Integrar frameworks externos o ampliar el dataset dentro de `0.3.0`.
