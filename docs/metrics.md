# Métricas e interpretación

## Métricas oficiales de Ollama

### `total_duration`

Tiempo total que Ollama atribuye a la respuesta. Se expresa en nanosegundos.

### `load_duration`

Tiempo dedicado a cargar el modelo. Es especialmente relevante en ejecuciones frías.

### `prompt_eval_count`

Número de tokens de entrada realmente procesados. Es más fiable que estimar tokens por caracteres.

### `prompt_eval_duration`

Tiempo dedicado a procesar la entrada.

### `eval_count`

Tokens generados en la salida.

### `eval_duration`

Tiempo dedicado a generar esos tokens.

## Métricas derivadas

### Prompt tokens por segundo

```text
prompt_eval_count / prompt_eval_duration
```

Mide la lectura/procesamiento del prompt. No debe confundirse con la velocidad de generación.

### Generation tokens por segundo

```text
eval_count / eval_duration
```

Mide la velocidad de producción de tokens de salida.

### TTFT

Tiempo hasta el primer fragmento observable en streaming. Se mide con una llamada separada porque una respuesta no streaming solo llega al final.

### Memoria

El runner consulta `/api/ps` y guarda `size_vram` y `context_length` cuando están disponibles.

En Apple Silicon, la memoria es unificada. La cifra de Ollama describe la asignación del modelo en el subsistema de aceleración, pero no debe interpretarse como memoria física exclusivamente separada de la CPU.

### Swap

Se captura antes y después de cada ejecución en macOS. Un aumento sostenido puede indicar presión de memoria, pero un valor de swap ya utilizado al comenzar no implica por sí solo presión activa.

## Puntuación de velocidad

Componentes iniciales:

- generation tok/s: 45 %;
- prompt tok/s: 20 %;
- latencia caliente: 20 %;
- carga fría: 15 %.

Los componentes se expresan en relación con el mejor modelo del mismo run.

## Puntuación de memoria y estabilidad

Componentes iniciales:

- memoria relativa: 60 %;
- incremento de swap: 20 %;
- ausencia de errores del runner: 20 %.

## Intervalo Wilson

El intervalo Wilson expresa la incertidumbre de una proporción. Es más estable que `p ± 1.96·error` cuando hay pocos casos o tasas cercanas a 0 o 100 %.

## McNemar

Compara dos modelos sobre los mismos casos. Solo cuentan los casos discordantes:

- A supera y B falla;
- A falla y B supera.

Un promedio superior no garantiza una diferencia consistente. McNemar ayuda a distinguir una ventaja repetida de una diferencia producida por pocos casos.

## Consistencia

Se informa cuántos casos fueron superados en todas las repeticiones. Un modelo con 90 % de media pero resultados cambiantes puede ser menos adecuado para un agente que otro con una media ligeramente inferior y comportamiento estable.
