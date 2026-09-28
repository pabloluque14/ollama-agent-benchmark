# Los fallos medidos y los fallos de integridad son distintos

## Estado

Aceptada.

## Contexto

El campo histórico `runner_error` puede mezclar fallos observables del sistema evaluado con defectos
del propio harness. Penalizar ambos al modelo falsearía la comparación; ignorarlos o reintentarlos
podría ocultar inestabilidad o seleccionar un intento favorable.

También hay fallos en los que el benchmark no puede asegurar que una clave se ejecutó o persistió
correctamente. Esos defectos no pueden representarse como un resultado normal de la medición.

## Decisión

El protocolo distinguirá dos categorías mínimas:

- `execution_failure`: resultado terminal de una ejecución correctamente planteada atribuible al
  sistema evaluado, como un error de Ollama, timeout, desconexión o imposibilidad de obtener una
  respuesta válida. Satisface su clave, no se reintenta, no aporta métricas positivas y cuenta
  negativamente cuando corresponda.
- `benchmark_integrity_failure`: situación en la que el harness no puede garantizar la validez de
  una medición, artefacto u operación. No penaliza al modelo, no satisface ninguna clave y hace
  inelegible el run.

Los fallos de integridad se conservarán en un diario canónico, inmutable y append-only separado de
los registros de medición. Cada evento registrará una identidad, fase, código estable, descripción
saneada, componente afectado y clave relacionada cuando exista. El diario no contendrá
credenciales ni información privada innecesaria.

Si falla la persistencia del propio evento, el proceso terminará con error y declarará que no pudo
conservar evidencia completa. Ningún log general sustituirá el diario canónico.

## Consecuencias positivas

- Los modelos solo reciben consecuencias por resultados atribuibles al sistema evaluado.
- Un defecto del scorer, persistencia, manifest o harness no puede alterar el ranking.
- La evidencia explica por qué un run es inelegible sin fingir que una clave fue completada.
- Los fallos medidos siguen capturando estabilidad operativa sin reintentos selectivos.
- La clasificación puede validarse estructural y semánticamente.

## Costes y limitaciones

- Será necesario definir códigos y fases estables, además de la frontera entre ambas categorías.
- Aparece un nuevo artefacto canónico con sus propias reglas de schema, unicidad y corrupción.
- Algunos fallos límite exigirán una clasificación conservadora como defecto de integridad.
- No siempre será posible persistir evidencia estructurada si falla el propio mecanismo de
  almacenamiento.

## Alternativas rechazadas

- Tratar todos los errores como fallos del modelo.
- Hacer inelegible cualquier run que contenga un fallo de ejecución medido.
- Registrar un fallo de integridad como si completara la clave afectada.
- Reintentar automáticamente los fallos dentro del mismo run.
- Conservar los defectos de integridad únicamente en stderr o logs generales.
