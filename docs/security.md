# Seguridad

## Principio central

El modelo nunca ejecuta directamente una herramienta. Solo solicita una llamada estructurada. El runner decide si la herramienta está permitida y devuelve un resultado simulado.

## Herramientas virtuales

- `simulated_terminal`
- `read_file`
- `write_file`
- `replace_text`
- `search_docs`
- `read_doc`

Los archivos y documentos existen únicamente en memoria y se reinician para cada caso.

## Protecciones evaluadas

- rutas absolutas y `..`;
- comandos o herramientas no permitidos;
- operaciones sensibles sin confirmación;
- sobrescritura de archivos;
- hash incorrecto antes de una modificación;
- texto a sustituir inexistente o no único;
- inyección dentro de archivos, listados, documentos y mensajes de error;
- intento de `sudo` o acción destructiva;
- resultados inventados.

## Qué no hace este proyecto

- No ofrece shell real al modelo.
- No lee tu directorio personal.
- No accede a llaveros, correo o navegador.
- No expone Ollama a la red.
- No instala OpenClaw.

## Paso posterior al benchmark

El ganador debe validarse de nuevo en un sandbox real con:

1. allowlist de comandos;
2. resolución canónica de rutas;
3. confirmación humana fuera del contexto del modelo;
4. timeouts y límites de salida;
5. registro de cada acción;
6. rechazo físico de rutas externas al sandbox.
