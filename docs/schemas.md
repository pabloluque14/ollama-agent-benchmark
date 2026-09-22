# Contratos de datos v3

Los JSON Schema versionados viven en `src/ollama_agent_benchmark/contracts/`. Cubren configuración,
lock, inputs metodológicos, plan, registros funcionales, rendimiento, TTFT, diario de integridad e
informe JSON.

El runtime usa un validador local sin dependencias obligatorias: rechaza campos desconocidos,
ausentes, tipos incorrectos y versiones incompatibles sin coerciones ni valores predeterminados
silenciosos. Después aplica invariantes semánticas como pesos, hashes, calendario, claves y relación
con el plan.

El extra `dev` instala `jsonschema` como oráculo diferencial, además de Hypothesis y statsmodels
para propiedades y oráculos estadísticos. Estas herramientas no forman parte del entorno mínimo y
`dependencies = []` permanece sin cambios.
