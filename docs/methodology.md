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

El dataset v2 contiene:

- 42 casos de herramientas y seguridad;
- 18 casos de calidad y razonamiento;
- 60 casos totales.

Los casos incluyen selección de herramienta, no uso, secuencias, dependencias, JSON, recuperación de errores, confirmaciones, modificaciones exactas e inyección de instrucciones.

Cada modelo realiza tres repeticiones por defecto. En el plan v3, `order_control.seed` y los
digests bloqueados fijan el orden inicial y cada repetición lo rota por caso; cambiar el orden de
la lista de configuración no cambia la asignación de posiciones. Los casos se barajan con la misma
seed. Para cada caso se informa tasa bruta, mayoría estricta (empate = fallo),
éxito en todas las repeticiones y consistencia. Una ausencia puede aparecer como `N/D` en un
informe oficial elegible, pero impide el ranking global.

### Pista de rendimiento

Cada combinación modelo/workload ejecuta:

- tres cargas frías, cada una verificada en `/api/ps`;
- cinco respuestas calientes;
- tres respuestas streaming para TTFT.

En el plan v3, cada combinación de workload y tipo (`cold`, `hot`, TTFT) equilibra por separado las
posiciones de modelos entre sus muestras. Si `ttft_runs = 0`, TTFT no está planificado y no cuenta
como medición ausente ni componente `N/D`; su peso no se redistribuye. Las respuestas no streaming proporcionan las métricas de Ollama. Cada salida debe cumplir reglas
deterministas del workload; una incompleta se conserva como inválida y no obtiene ventaja. Se resume
primero por modelo/workload/estado/métrica y después se agregan workloads con pesos explícitos. Una
celda solo tiene valor oficial cuando contiene todas las muestras planificadas y todas son válidas;
en otro caso es `N/D` y no se recalcula con el subconjunto restante.

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
- intervalo Wilson del 95 % sobre mayorías de casos únicos;
- consistencia por caso entre repeticiones;
- prueba exacta de McNemar sobre resultados pareados por caso.

La unidad principal es el caso. McNemar usa únicamente casos comunes y mayoritarios. Esto evita
pseudorreplicación: tres intentos del mismo prompt no estrechan artificialmente Wilson.

## Procedencia y compatibilidad

En `0.3.0`, el plan y los registros primarios son evidencia canónica. Cada registro se asocia a una
clave planificada y se valida antes de persistirse. Un fallo de ejecución atribuible al sistema
evaluado es terminal para esa clave; un fallo del harness o de atribución incierta se escribe en el
diario de integridad, deja la clave ausente y hace el run inelegible sin penalizar al modelo.

El plan v3 fija benchmark/runner, modelos y digests, Ollama, URL pública sin credenciales,
generación/thinking/contexto, calendario, hashes, modo, métricas, validez y scoring. TTFT solo es
oficial si el stream completo y reconstruido cumple el workload. Un run elegible puede producir
informe oficial con `N/D`, pero solo hay ranking si todos los componentes requeridos existen. Un
evento de integridad permite únicamente un informe diagnóstico no oficial; corrupción, duplicados o
claves inesperadas producen rechazo sin informe. No existe conversión silenciosa desde `0.2.0`.

## Separación causal

El benchmark responde a:

> ¿Qué artefacto completo funciona mejor en este equipo y con esta versión de Ollama?

No responde automáticamente a:

> ¿Cuánto de la diferencia se debe exclusivamente a MLX, cuantización o MTP?

Para una inferencia causal hacen falta pares de artefactos que cambien una sola variable.
