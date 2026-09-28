# El calendario se fija y equilibra por bloque

## Estado

Aceptada.

## Contexto

El orden de evaluación puede introducir sesgo por calentamiento, carga o posición. Una rotación
cíclica basada en el orden de `benchmark.json` solo se equilibra perfectamente para ciertas
combinaciones de modelos y repeticiones, y traslada el orden de configuración al experimento.

El blindaje de `0.3.0` debe controlar ese sesgo sin aumentar automáticamente el número de
repeticiones ni introducir optimización térmica o concurrencia nuevas.

## Decisión

El plan materializará un calendario determinista derivado de la seed y de identidades bloqueadas de
los modelos, preferiblemente nombre canónico y digest. El resultado no dependerá de la posición de
los modelos en la configuración.

El equilibrio se comprobará en el bloque experimental mínimo donde el orden pueda afectar a la
comparación:

- para la pista funcional, en cada caso a lo largo de sus repeticiones;
- para rendimiento, en cada combinación de workload y tipo `cold`, `hot` o `TTFT`.

Cada modelo ocupará cada posición el mismo número de veces cuando sea posible. En otro caso, las
frecuencias diferirán como máximo en uno y la seed decidirá las posiciones sobrantes. No se exigirán
todavía todas las parejas de precedencia.

El plan conservará la versión del algoritmo, seed, identidades, bloques y asignaciones suficientes
para reconstruir y verificar el calendario. Las invariantes se validarán antes de contactar con
Ollama y la reanudación usará siempre el calendario original.

## Consecuencias positivas

- El calendario es reproducible e independiente del orden de la configuración.
- El sesgo de posición se limita dentro de cada comparación relevante.
- El equilibrio puede comprobarse antes de consumir tiempo de inferencia.
- La reanudación no redistribuye posiciones según el estado parcial del run.
- No es necesario aumentar automáticamente el número de mediciones.

## Costes y limitaciones

- El planificador y sus propiedades serán más complejos que una rotación cíclica simple.
- Cuando el número de repeticiones no permita igualdad exacta persistirá una diferencia máxima de
  una posición.
- No se equilibran todavía todas las parejas de precedencia ni efectos térmicos más complejos.
- Cambiar el algoritmo en el futuro exigirá una nueva identidad versionada y no reinterpretará
  calendarios históricos.

## Alternativas rechazadas

- Utilizar directamente el orden de modelos de `benchmark.json`.
- Aplicar un barajado seeded sin garantía de equilibrio.
- Exigir que las repeticiones sean múltiplo del número de modelos.
- Aumentar automáticamente las repeticiones para forzar igualdad exacta.
- Recalcular dinámicamente el calendario durante una reanudación.
- Introducir en `0.3.0` balance completo de precedencias u optimización térmica avanzada.
