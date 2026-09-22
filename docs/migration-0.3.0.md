# Migración de 0.2.0 a 0.3.0

No existe migración de evidencia. `0.3.0` cambia el plan canónico, los schemas, las claves, la
persistencia, la validez de muestras y los estados del informe. Convertir un run anterior daría una
apariencia de comparabilidad que la evidencia no sostiene.

Para usar `0.3.0`:

1. conserva por separado cualquier run `0.2.0` que necesites auditar;
2. instala `0.3.0` y crea una configuración schema 3;
3. genera un lock nuevo;
4. inicia runs funcional y de rendimiento nuevos.

Un run `0.2.0` se rechaza al reanudar, mezclar o generar un informe `0.3.0`. No copies registros ni
manifests antiguos dentro de un plan v3.
