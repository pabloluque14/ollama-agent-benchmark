# Changelog

## 0.3.0

- Plan v3 inmutable antes de medir, con modo, overrides efectivos, identidades, políticas,
  calendario equilibrado y claves exactas.
- Registros primarios y diario de integridad append-only, durables y validados sin recuperación
  parcial de JSONL corrupto.
- Fallos de ejecución terminales separados de fallos de integridad del benchmark.
- Reanudación idempotente desde el plan original aunque cambien configuración o inputs actuales.
- TTFT condicionado a stream completo, reconstrucción y cumplimiento; celdas estrictas `N/D`.
- Informe v3 regenerable con estados oficial, diagnóstico no oficial y rechazo sin informe.
- Contratos locales para configuración, lock, datasets, plan, registros, diario e informe.
- Los runs `0.2.0` se rechazan: no se reanudan, mezclan, migran ni reinterpretan como `0.3.0`.

## 0.2.0

- Configuración schema 2 completa, validada y con `order_control.seed`.
- Infraestructura HTTP/JSON/plataforma centralizada y URL configurable consistente.
- Manifests v2 con hashes, identidad, scoring y resume compatible seguro; rechazo de 0.1.0.
- TTFT deduplicable, cargas frías verificadas y tres repeticiones frías predeterminadas.
- Matchers deterministas con diagnóstico; corrección del falso positivo numérico de T001.
- Estadística por caso: tasa bruta, mayoría estricta, consistencia, Wilson y McNemar pareado.
- Rendimiento por workload, cumplimiento de salida, TTFT ponderado y métricas ausentes `N/D`.
- Informe con validación de procedencia y modo exploratorio incompatible sin ranking oficial.
- Servidor Ollama falso, integrales, Ruff, Mypy, cobertura y CI macOS/Ubuntu 3.11/3.12.
- README español ampliado, documentación de arquitectura/metodología y guía de migración.

## 0.1.0

- Dataset inicial de 60 casos.
- Seis herramientas simuladas.
- Lock de modelos por digest y versión de Ollama.
- Benchmark funcional configurable y reanudable.
- Benchmark de rendimiento con runs fríos, calientes y TTFT.
- Captura de `/api/ps`, swap y snapshots del sistema.
- Informe Markdown, JSON, CSV y SVG.
- Configuración de ejemplo para M2 Pro con 16 GB.
- Scripts de instalación, publicación privada y copia de modelos.
