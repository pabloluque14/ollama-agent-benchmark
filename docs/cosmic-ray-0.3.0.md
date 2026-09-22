# Campaña manual de Cosmic Ray para 0.3.0

## Carácter del experimento

Esta campaña es informativa. No forma parte de la definición de terminado, no bloquea publicación,
no se ejecuta en CI y no establece un score mínimo. Cosmic Ray pertenece exclusivamente al extra
`mutation`; el runtime conserva `dependencies = []`.

## Entorno y alcance

- Fecha: 2026-09-22.
- Cosmic Ray: 8.7.0.
- Python: 3.11.
- Distribuidor: local, un mutante cada vez.
- Módulo: `src/ollama_agent_benchmark/aggregation.py`.
- Tests: `python -m unittest tests.test_aggregation -v`.
- Timeout por mutante: 10 segundos.
- Commit base: `51d33ba0893335fe51314cb05690878f553321dd`.
- Hash del módulo: `f7af5b7ced63b16e8e8f03963ac07334847bff8b15f5d4aec93c7a9f73bd3e21`.
- Hash de los tests: `885c455d49900b24ee98c6c51b51ab4d8a8a76d324b2751ea3db024c0dda33c5`.
- Hash de la configuración: `8f2aba2fc9c120e495a8dc4766172a82e30825fa891bf60928b19d8c5f685d04`.

La configuración versionada es `cosmic-ray.toml`. La sesión SQLite es deliberadamente temporal y
no es evidencia del benchmark.

## Reproducción

```bash
python -m pip install -e '.[dev,mutation]'
cosmic-ray baseline --session-file /tmp/oab-cosmic-ray-baseline.sqlite cosmic-ray.toml
cosmic-ray init cosmic-ray.toml /tmp/oab-cosmic-ray.sqlite
cosmic-ray exec cosmic-ray.toml /tmp/oab-cosmic-ray.sqlite
cr-report /tmp/oab-cosmic-ray.sqlite
cosmic-ray dump /tmp/oab-cosmic-ray.sqlite
```

Los comandos siguen el ciclo recomendado de configuración, baseline, inicialización, ejecución y
reporte descrito por la [documentación oficial de Cosmic Ray](https://cosmic-ray.readthedocs.io/en/latest/tutorials/intro/).

## Resultado

| Dato | Resultado |
|---|---:|
| Baseline | correcto |
| Inicialización | 0,59 s |
| Ejecución | 18,14 s |
| Mutantes totales | 139 |
| Eliminados por tests | 53 |
| Supervivientes | 86 |
| Incompatibles/incompetentes | 0 |

El 38,13 % de mutantes fue eliminado. Este porcentaje describe solo el prototipo y no es un umbral
de calidad ni un gate.

## Clasificación de supervivientes

| Clase | Cantidad | Interpretación |
|---|---:|---|
| Equivalentes o inertes | 22 | Mutaciones de `|` dentro de anotaciones pospuestas; no cambian el runtime. |
| Huecos de tests | 64 | Cambian estadísticas, filtros, validez o contadores sin que la selección actual los detecte. |
| Incompatibles | 0 | Ningún worker falló ni agotó el timeout. |

Los huecos quedan agrupados como acciones futuras, no como cambios de `0.3.0`:

1. añadir matrices con varios modelos y workloads para proteger los filtros de calendario y
   registros;
2. verificar exactamente contadores de errores, registros válidos e inválidos;
3. ampliar casos de `_stats` para vacío, una muestra y tres o más muestras;
4. cubrir `model_ps` ausente y las combinaciones de descarga fría, cumplimiento y tipos booleanos.

No se corrigen estos supervivientes dentro de la campaña: el ticket evalúa la utilidad de la
herramienta y mantiene separado cualquier trabajo posterior.
