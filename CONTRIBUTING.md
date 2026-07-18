# Contribuir

1. Crea una rama.
2. Añade tests para cualquier cambio en evaluación o seguridad.
3. Ejecuta:

```bash
python -m unittest discover -s tests -v
oab validate
```

4. No cambies silenciosamente una respuesta esperada después de observar resultados. Versiona el dataset y documenta el motivo.
5. No añadas pesos de modelos, resultados privados ni `models.lock.json` personales.
