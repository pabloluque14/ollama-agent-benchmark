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

## Evidencia y diagnósticos de `0.3.0`

Los registros primarios se validan completos antes de añadirse y los JSONL corruptos se rechazan
sin consumir su prefijo ni modificar el archivo. Los fallos atribuibles a la ejecución satisfacen
su clave como resultado terminal; un defecto incierto o del harness se conserva en el diario de
integridad y no penaliza al modelo.

Antes de mostrar o persistir errores se redactan credenciales, tokens, cabeceras de autorización y
URLs que puedan contener secretos. Si el propio diario no puede persistirse, el proceso termina con
error y no completa la clave afectada. Los diagnósticos saneados ayudan a localizar el componente,
pero no sustituyen un almacén externo seguro para trazas privadas.

## Paso posterior al benchmark

El ganador debe validarse de nuevo en un sandbox real con:

1. allowlist de comandos;
2. resolución canónica de rutas;
3. confirmación humana fuera del contexto del modelo;
4. timeouts y límites de salida;
5. registro de cada acción;
6. rechazo físico de rutas externas al sandbox.

Una frase de confirmación dentro del prompt solo permite evaluar si el modelo reconoce la política.
En producción, la autorización debe capturarse fuera del texto controlable por el modelo, asociarse
a una acción concreta y caducar. Conectar OpenClaw u otro orquestador exige esa capa adicional.
