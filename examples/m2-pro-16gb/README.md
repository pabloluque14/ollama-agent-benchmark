# Ejemplo: MacBook Pro M2 Pro con 16 GB

Configuración conservadora para comparar:

- `gemma4:12b-mlx`
- `gemma4:12b-it-qat`
- `qwen3.5:9b-mlx`

Características:

- contexto inicial de 8192 tokens;
- paralelismo asumido de 1;
- thinking desactivado;
- tres cargas frías verificadas y cinco calientes;
- 60 casos funcionales con tres repeticiones;
- benchmark oficial únicamente conectado a corriente.

Copia `benchmark.json` a `config/benchmark.json`, revisa los nombres con `ollama list` y ejecuta `oab lock`.
