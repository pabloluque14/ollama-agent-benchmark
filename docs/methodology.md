# Metodología

## Objetivo

Seleccionar el modelo local que ofrezca el mejor equilibrio para operar como agente con herramientas, no simplemente el que genere más tokens por segundo.

## Diseño experimental

### Identidad de los modelos

`oab lock` consulta `/api/tags` y `/api/show` y guarda:

- nombre y digest exacto;
- tamaño descargado;
- formato y cuantización;
- familia y número de parámetros declarado;
- capacidades;
- arquitectura y contexto declarado;
- hashes de plantilla y Modelfile;
- versión del servidor Ollama.

Un run oficial se detiene si los digests o la versión de Ollama no coinciden con el lock.

### Pista funcional

El dataset v1 contiene:

- 42 casos de herramientas y seguridad;
- 18 casos de calidad y razonamiento;
- 60 casos totales.

Los casos incluyen selección de herramienta, no uso, secuencias, dependencias, JSON, recuperación de errores, confirmaciones, modificaciones exactas e inyección de instrucciones.

Cada modelo realiza tres repeticiones por defecto. El orden de los modelos rota para repartir el posible sesgo de posición.

### Pista de rendimiento

Cada combinación modelo/workload ejecuta:

- una carga fría;
- cinco respuestas calientes;
- tres respuestas streaming para TTFT.

Las respuestas no streaming proporcionan las métricas oficiales de Ollama. El TTFT se mide separadamente con reloj monotónico hasta el primer fragmento que contiene contenido, thinking o una tool call.

### Parámetros controlados

La configuración inicial usa:

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
  "think": false
}
```

Cambiar estos valores crea un experimento distinto. Deben guardarse junto con los resultados.

## Puntuación

La configuración inicial aplica:

```text
Fiabilidad de herramientas: 40 %
Calidad y razonamiento:     25 %
Velocidad:                  20 %
Memoria y estabilidad:      15 %
```

Las dos primeras categorías son tasas absolutas de éxito. Velocidad y memoria se normalizan respecto al mejor modelo del mismo run.

## Estadística

El informe calcula:

- media, mediana, desviación estándar, mínimo y máximo para rendimiento;
- intervalo Wilson del 95 % para tasas de éxito;
- consistencia por caso entre repeticiones;
- prueba exacta de McNemar sobre resultados pareados por caso.

La unidad principal es el caso de prueba. Las repeticiones ayudan a estimar consistencia, pero no se tratan como casos independientes para las comparaciones pareadas.

## Separación causal

El benchmark responde a:

> ¿Qué artefacto completo funciona mejor en este equipo y con esta versión de Ollama?

No responde automáticamente a:

> ¿Cuánto de la diferencia se debe exclusivamente a MLX, cuantización o MTP?

Para una inferencia causal hacen falta pares de artefactos que cambien una sola variable.
