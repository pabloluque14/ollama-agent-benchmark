# Configuración de modelos

## Lista de modelos

Edita `config/benchmark.json`:

```json
{
  "models": [
    "modelo-a:tag",
    "modelo-b:tag",
    "modelo-c:tag"
  ]
}
```

El orden se usa como punto inicial. El runner lo rota entre repeticiones.

`order_control.seed` controla el barajado de casos. `speed_weights` y `workload_weights` deben sumar
1.0. Tres cargas frías son el valor oficial predeterminado; reducirlas cambia el experimento.

## Requisitos

Cada nombre debe aparecer exactamente en:

```bash
ollama list
```

El proyecto no descarga modelos automáticamente. Esta decisión evita sustituir un tag sin guardar antes la identidad del artefacto local.

## Crear el lock

```bash
oab lock
```

Para regenerarlo después de modificar la lista:

```bash
oab lock --force
```

## Tags mutables

Un tag como `modelo:latest` puede apuntar a un artefacto diferente en el futuro. El lock guarda el digest actual y bloquea el run si cambia.

El digest permite detectar la diferencia, pero no garantiza que el artefacto antiguo pueda volver a descargarse. Para una repetición exacta conserva también los blobs de Ollama en un almacenamiento externo.

## Parámetros de generación

La sección `generation` controla el experimento base:

```json
{
  "num_ctx": 8192,
  "temperature": 0,
  "seed": 42,
  "top_k": 1,
  "top_p": 1.0,
  "min_p": 0.0,
  "repeat_penalty": 1.0,
  "presence_penalty": 0.0,
  "num_predict": 1024,
  "think": false
}
```

No todas las familias implementan todos los parámetros de manera idéntica. Los resultados describen el comportamiento observado bajo Ollama, no una garantía de equivalencia interna.

## Contexto

El contexto inicial de 8192 tokens reduce el riesgo de presión de memoria en equipos de 16 GB. Las pruebas de 16K y 32K deben hacerse como pistas separadas y solo con candidatos que hayan demostrado estabilidad en 8K.

## Thinking

No mezcles runs con `think: false` y `think: true`. Copia la configuración y utiliza identificadores de run diferentes.

La URL `ollama.base_url` es obligatoria y debe ser localhost. Lock, preflight, runners, snapshots y
descarga utilizan exactamente esa URL.
