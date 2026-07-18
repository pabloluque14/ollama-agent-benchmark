# Contribuir

1. Crea una rama.
2. Añade tests para cualquier cambio en evaluación o seguridad.
3. Ejecuta:

```bash
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
oab validate
ruff check .
mypy
coverage run -m unittest discover -s tests
coverage report
```

4. No cambies silenciosamente una respuesta esperada después de observar resultados. Versiona el dataset y documenta el motivo.
5. No añadas pesos de modelos, resultados privados ni `models.lock.json` personales.
6. CI y tests deben usar el servidor falso; nunca Ollama real, modelos ni Internet.
7. Los cambios incompatibles requieren schema/dataset nuevo, migración y changelog.

La licencia del proyecto queda pendiente de una decisión expresa del propietario.
