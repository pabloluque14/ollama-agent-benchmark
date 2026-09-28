# El protocolo falla cerrado

## Estado

Aceptada.

## Contexto

Un benchmark reproducible no puede resolver silenciosamente duplicados, ignorar líneas corruptas
ni agregar el prefijo aparentemente válido de un artefacto truncado. Tales recuperaciones hacen
imposible saber si el resultado observado corresponde al plan y pueden seleccionar datos
favorables.

Los cambios de `0.3.0` alteran reglas de aceptación y contratos. Por ello los runs de `0.2.0` no
podrán reanudarse, mezclarse, migrarse ni reinterpretarse silenciosamente como runs del protocolo
nuevo.

## Decisión

Un run estructuralmente completo contendrá el conjunto exacto de `execution_key` y
`measurement_key` previsto por el plan: cada clave aparecerá exactamente una vez y no habrá claves
inesperadas. Una ausencia, duplicado o clave ajena al plan hará que el run no pueda producir un
resultado oficial completo.

Las operaciones canónicas fallarán ante JSON o JSONL inválido, UTF-8 inválido, líneas vacías no
permitidas, registros truncados, tipos estructurales incorrectos o incompatibilidad con el plan.
El diagnóstico identificará el artefacto, la línea y la causa disponibles, sin modificar el
original.

La reanudación validará primero toda la evidencia existente y ejecutará únicamente claves esperadas
ausentes. No reescribirá claves completadas, no elegirá entre duplicados y no reintentará
automáticamente fallos terminales. Los registros canónicos seguirán siendo JSONL append-only en
`0.3.0`; una escritura parcial invalidará el run en vez de repararse.

## Consecuencias positivas

- Completitud e idempotencia tienen definiciones exactas y comprobables.
- Ninguna lectura best-effort puede ocultar pérdida, corrupción o duplicación de evidencia.
- Los datos defectuosos no participan en puntuaciones, rankings o comparaciones oficiales.
- Una reparación futura deberá ser explícita, auditable y producir una identidad de run nueva.
- La incompatibilidad con `0.2.0` queda visible y no contamina comparaciones nuevas.

## Costes y limitaciones

- Una última línea JSONL parcial puede inutilizar un run que conservaba un prefijo válido.
- Los fallos transitorios no se recuperan reintentando dentro del mismo experimento.
- Para repetir una medición será necesario iniciar un run nuevo.
- Una futura herramienta de reparación necesitará su propio protocolo y queda fuera de `0.3.0`.

## Alternativas rechazadas

- Ignorar automáticamente una última línea truncada.
- Saltar registros inválidos y continuar con el prefijo válido.
- Conservar el primer o último registro cuando una clave está duplicada.
- Reintentar una clave hasta obtener una respuesta válida.
- Reparar o sobrescribir el run original.
- Convertir silenciosamente runs de `0.2.0` al nuevo protocolo.
