# Recuperación después de formatear

## Qué debe estar en GitHub

- código fuente;
- datasets y herramientas;
- configuración de ejemplo;
- documentación;
- tests y workflow de CI.

Los resultados pueden guardarse en otro repositorio privado o en un release comprimido, pero no se incluyen por defecto para evitar crecer indefinidamente.

## Qué debe guardarse fuera de GitHub

- pesos y blobs de Ollama;
- resultados que contengan información privada;
- backups grandes;
- cualquier credencial.

## Copia antes de formatear

### Metadatos

```bash
./scripts/backup_ollama_models.sh \
  --output-dir /Volumes/MI_DISCO/ollama-backup
```

### Pesos exactos

```bash
./scripts/backup_ollama_models.sh \
  --include-weights \
  --confirm-large-backup \
  --output-dir /Volumes/MI_DISCO/ollama-backup
```

Revisa primero el tamaño de `~/.ollama/models`:

```bash
du -sh ~/.ollama/models
```

## Restauración

1. Instala Ollama.
2. Clona el repositorio.
3. Ejecuta `scripts/bootstrap_macos.sh`.
4. Restaura los modelos o vuelve a descargarlos.
5. Copia y edita `config/benchmark.json`.
6. Ejecuta `oab lock`.
7. Compara el nuevo lock con el antiguo.
8. Ejecuta `oab preflight` y un smoke test.

GitHub no recupera `.venv`, configuración/locks locales, runs ignorados, credenciales ni pesos. Guarda
fuera del repositorio los manifests, digests y blobs necesarios. Los pesos no deben subirse a GitHub:
son grandes y su redistribución depende de la licencia del modelo.

## Repetición exacta frente a repetición metodológica

- **Exacta:** mismos blobs, digest, versión de Ollama, configuración y hardware.
- **Metodológica:** mismo código y protocolo, pero modelos o versiones actuales.

Ambas son útiles, pero deben etiquetarse de forma diferente.
