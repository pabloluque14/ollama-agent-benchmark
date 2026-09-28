# El plan y los registros son la evidencia canónica

## Estado

Aceptada.

## Contexto

La siguiente evolución del protocolo será Ollama Agent Benchmark `0.3.0` y utilizará
`schema_version: 3`. Su alcance se limita al blindaje interno: debe aumentar la fiabilidad y la
auditabilidad del benchmark actual sin ampliar las capacidades que pretende medir.

Hasta ahora, parte de la ejecución podía reconstruirse desde la configuración presente y el
informe podía consumir resúmenes persistidos. Esa mezcla permite que cambios posteriores en la
configuración, los pesos, los inputs o la lógica de agregación alteren la interpretación de un run
ya iniciado. También convierte caches y salidas de presentación en fuentes potencialmente
contradictorias.

## Decisión

Antes de la primera medición se materializará un plan del run completo e inmutable. El plan fijará
la identidad del protocolo, runner, modelos y digests; la versión esperada de Ollama; los parámetros
de generación; la seed; el algoritmo y calendario de planificación; los casos, workloads,
repeticiones y claves esperadas; los hashes de inputs; y las reglas de aceptación, agregación,
scoring, errores y datos ausentes.

La evidencia canónica estará formada exclusivamente por:

- el plan del run;
- los registros primarios funcionales, de rendimiento y TTFT;
- el diario canónico de integridad.

Los resúmenes, agregados, puntuaciones, rankings, CSV, Markdown, SVG e informe JSON serán artefactos
derivados y regenerables. Un derivado nunca podrá completar una clave, validar una muestra,
modificar la clasificación de un fallo ni contradecir la evidencia canónica. La reanudación y la
generación de informes partirán siempre del plan y de los registros primarios.

## Consecuencias positivas

- Cada run conserva una identidad experimental completa y auditable.
- La reanudación no depende de la configuración actual ni puede recalcular un calendario distinto.
- Los informes pueden regenerarse y contrastarse independientemente desde la evidencia primaria.
- Un cache obsoleto o manipulado no puede alterar la elegibilidad, puntuación o interpretación.
- La procedencia de inputs, reglas y algoritmos queda fijada antes de observar resultados.

## Costes y limitaciones

- El plan será un artefacto más amplio y deberá escribirse de forma durable antes de ejecutar.
- Regenerar derivados puede requerir más tiempo que confiar en resúmenes almacenados.
- La reproducción histórica exige una implementación compatible con las versiones registradas.
- Si la implementación actual no entiende fielmente un protocolo histórico, debe rechazar la
  regeneración en vez de aproximarla.

## Alternativas rechazadas

- Reconstruir el experimento desde `benchmark.json` al reanudar.
- Permitir que la configuración actual sustituya valores del plan original.
- Considerar canónicos los resúmenes o informes persistidos.
- Confiar en caches sin verificar su procedencia frente a la evidencia primaria.
- Reinterpretar un run histórico con pesos, reglas o algoritmos actuales.
