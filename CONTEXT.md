# Ollama Agent Benchmark

Este contexto define el lenguaje utilizado para planificar, ejecutar y auditar comparaciones
reproducibles de modelos locales como agentes con herramientas virtuales.

## Language

**Protocolo de benchmark**:
Conjunto versionado de reglas que determina las ejecuciones, su aceptación, agregación y forma de
interpretación.
_Avoid_: configuración, suite

**Run**:
Aplicación de una versión concreta del protocolo a un conjunto bloqueado de modelos y a un entorno
identificado.
_Avoid_: informe, ranking

**Plan del run**:
Descripción canónica e inmutable de todo lo previsto para un run, materializada antes de su primera
medición.
_Avoid_: configuración actual, resumen

**Identidad bloqueada del modelo**:
Nombre canónico y digest que identifican inequívocamente el artefacto evaluado.
_Avoid_: posición del modelo, alias sin digest

**Clave esperada**:
Identificador único de una ejecución o medición prevista por el plan.
_Avoid_: índice de fila

**Registro primario**:
Evidencia inmutable y estructuralmente válida del resultado terminal asociado con una clave
esperada.
_Avoid_: resumen, caché

**Evidencia canónica**:
Plan, registros primarios y diario de integridad suficientes para auditar y reconstruir un run.
_Avoid_: informe, CSV, ranking

**Artefacto derivado**:
Resultado regenerable calculado exclusivamente desde la evidencia canónica.
_Avoid_: fuente de verdad

**Fallo de ejecución**:
Resultado terminal atribuible al sistema evaluado cuando una ejecución correctamente planteada no
puede completarse válidamente.
_Avoid_: defecto del benchmark

**Fallo de integridad del benchmark**:
Situación en la que el harness no puede garantizar la validez de una medición, artefacto u
operación.
_Avoid_: fallo del modelo

**Bloque experimental**:
Unidad mínima dentro de la cual el orden de los modelos puede afectar a una comparación.
_Avoid_: pista completa

**Celda de rendimiento**:
Conjunto planificado de muestras de un modelo, workload, tipo de medición y métrica oficial.
_Avoid_: promedio parcial

**Run estructuralmente completo**:
Run que contiene cada clave esperada exactamente una vez y ninguna clave inesperada.
_Avoid_: run exitoso

**Run elegible**:
Run cuya evidencia canónica es íntegra y no contiene fallos de integridad que impidan un informe
oficial.
_Avoid_: run completo

**Ranking oficial**:
Clasificación producida únicamente cuando todos los componentes requeridos de todos los modelos
planificados están disponibles.
_Avoid_: análisis diagnóstico

**N/D**:
Ausencia explícita de un valor oficial utilizable; nunca equivale a cero ni autoriza
renormalización.
_Avoid_: cero, dato ignorado
