# Migración de 0.1.0 a 0.2.0

## Incompatibilidad deliberada

Los runs, locks, datasets, manifests, resúmenes e informes de 0.1.0 no son compatibles con 0.2.0.
No se convierten silenciosamente porque cambiaron la unidad estadística, matchers, cargas frías,
validación de workloads, TTFT, scoring y trazabilidad. Mezclarlos produciría conclusiones engañosas.

## Qué hacer

1. Conserva tus carpetas antiguas como archivo de solo lectura.
2. Instala v0.2.0 y ejecuta `oab init --force` solo después de respaldar tu configuración local.
3. Vuelve a introducir los modelos en el nuevo `benchmark.json` y revisa todos los campos.
4. Con Ollama disponible, crea un lock v2 nuevo y ejecuta preflight.
5. Ejecuta runners funcional y rendimiento completos con IDs nuevos.
6. Genera el informe únicamente con esos dos runs v2.

Un informe exploratorio con `--allow-incompatible` muestra una advertencia y omite el ranking oficial;
no convierte datos ni certifica comparabilidad.
