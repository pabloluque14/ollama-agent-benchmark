# Limitaciones

- Los resultados son específicos del hardware, sistema operativo, versión de Ollama y artefactos bloqueados.
- La cuantización, backend, tokenizer, plantilla y arquitectura pueden cambiar a la vez.
- Los workloads de rendimiento no representan todas las cargas posibles.
- `size_vram` no equivale al tamaño en disco ni a toda la memoria del proceso.
- El TTFT se mide mediante una llamada streaming separada.
- Una seed fija no garantiza determinismo bit a bit en todos los backends.
- Los tests funcionales son representativos del uso como agente, pero no sustituyen evaluaciones del dominio concreto del usuario.
- No se prueban visión ni audio en la versión inicial.
- No se conectan herramientas reales.
