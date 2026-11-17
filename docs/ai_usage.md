# Evidencia de uso de IA — Activity 3: Building a Mini Lakehouse

Documento de trazabilidad del uso de Inteligencia Artificial para la entrega de **Datacycle (Unidad 2 · Curso 2026-27)**, recogiendo la herramienta empleada, los prompts utilizados y las salidas obtenidas durante el desarrollo de la práctica.

- **Herramienta de IA empleada:** Google Antigravity (asistente de desarrollo en VS Code)
- **Modelo:** Gemini 4 Hydrogen

---

## 1. Capa Bronze — `@Ignaciobrenas`

### Fase A · Análisis del enunciado, contraste con el dataset y planificación
- **Objetivo:** Validar que la estructura del repositorio, los datos de `data_lab/bronze/` y la planificación del equipo cubriesen todos los requisitos de *Activity 3*.
- **Prompt utilizado:**
  > Revisa el enunciado de la práctica (*Activity 3 – Building a Mini Lakehouse*) y comprueba que la estructura del repositorio, el plan de trabajo, el README y los issues de planificación cubren correctamente todos los requisitos de las capas Bronze, Silver y Gold frente a los ficheros reales de `data_lab/bronze/`. Actualiza los issues detectando posibles omisiones o casos límite.
- **Salida generada:**
  - Contraste del enunciado con los ficheros reales (`ventas.csv` en lugar de `sales.csv` y `clientes.json` en lugar de `customers.json`).
  - Detección de anomalías adicionales en Bronze no contempladas inicialmente: `id_cliente` vacío (pedido `15`), `importe=0` con `producto=test` (pedido `29`), importe atípico `9999` (pedido `30`, cliente `201 Debug`), `pais="??"` (`138`, `200`), duplicidad de nombre `Ana` (`101` y `111`), líneas en blanco en los tres ficheros, eventos `[DEBUG]`, línea sin `user=` (`22`) y `action=` vacío (`23`, `117`) en `logs.txt`.
  - Actualización de `PLAN.md`, `README.md` y de los 7 issues del repositorio con criterios claros de limpieza, contrato Silver y agrupación por `id_cliente` en Gold.

---

### Fase B · Issue #1 — Análisis de tipos de fichero y problemas en Bronze
- **Objetivo:** Desarrollar el análisis automatizado de `data_lab/bronze/` y responder a todas las preguntas de la Parte 1 en `docs/bronze_report.md`.
- **Prompt utilizado:**
  > Implementa el Issue #1 en `src/bronze_analysis.py` y `docs/bronze_report.md`: analiza de forma automática `ventas.csv`, `clientes.json` y `logs.txt`, identifica el tipo y estructura de cada fichero, detecta y cuantifica todas las anomalías de datos e integridad referencial, comenta el código explicando la lógica y documenta las respuestas a las preguntas del enunciado junto con la descripción de lo implementado.
- **Salida generada:**
  - Script `src/bronze_analysis.py` (Python estándar, modular y comentado explicando la lógica) con funciones `analyze_customers()`, `analyze_sales()`, `analyze_logs()` y `print_report()`.
  - Informe `docs/bronze_report.md` con tabla de tipos/estructura, detalle por fichero con número de línea e ID, respuestas completas a las preguntas del PDF, notas técnicas para Silver/Gold y documentación de uso.
  - Resultados obtenidos al ejecutar `python src/bronze_analysis.py` y `python -m src.bronze_analysis` (código de salida `0`):
    - `ventas.csv`: 218 líneas totales, 200 registros, 17 líneas en blanco, 6 anomalías directas (`id_cliente` vacío, huérfano `999`, importe `abc`, negativo `-10`, `0`, outlier `9999`), 4 registros asociados a `TestUser`/`Debug` y 3 pedidos repetidos (`1, 31, 32`).
    - `clientes.json`: 274 líneas totales, 250 registros, 22 líneas en blanco intercaladas, 1 `nombre` vacío (`112`), 3 países inválidos (`117` `null`, `138` y `200` `"??"`), 1 `id_cliente` como cadena (`"120"`), cuentas `TestUser`/`Debug` (`200`, `201`) y nombre duplicado `Ana` (`[101, 111]`).
    - `logs.txt`: 207 líneas totales, 205 eventos (`135` `INFO`, `35` `ERROR`, `31` `WARN`, `4` `DEBUG`), 2 líneas en blanco, 1 sin `user=`, 2 `user` no numéricos (`abc`, `xyz`), 2 `user` huérfanos (`999`), 2 `action=` vacío y 31 clientes válidos con algún `[ERROR]` en log.

---

### Fase C · Issue #2 — Estructura base del repositorio y rutas comunes
- **Objetivo:** Centralizar las rutas del pipeline (`BRONZE_DIR`, `SILVER_DIR`, `GOLD_DIR`) y verificar la estructura base para desbloquear el desarrollo paralelo de Silver y Gold.
- **Prompt utilizado:**
  > Revisa el Issue #2 con `gh` e implementa la estructura común del repositorio en `src/common.py` (y `src/__init__.py`) usando `pathlib.Path`, con utilidades para crear los directorios de salida, código comentado explicando la lógica, revisión de `.gitignore` y `requirements.txt`, y documentación de los prompts empleados en `docs/ai_usage.md`. Verifica la ejecución directa y como módulo desde la raíz sin hacer commit todavía.
- **Salida generada:**
  - Creación de `src/__init__.py` y `src/common.py` con `BASE_DIR`, `DATA_DIR`, `BRONZE_DIR`, `SILVER_DIR`, `GOLD_DIR`, `DOCS_DIR`, `ensure_dir()`, `ensure_output_dirs()` y `verify_project_structure()`.
  - Revisión de `requirements.txt` (`pandas`) y ampliación de `.gitignore` (`__pycache__/`, `*.py[cod]`, `.venv/`, `.pytest_cache/`, `.DS_Store`, `Thumbs.db`).
  - Creación de `docs/ai_usage.md` con la trazabilidad de uso de IA de la capa Bronze y plantilla para las capas restantes.
  - Verificación ejecutando `python src/common.py`, `python -m src.common` y pruebas de importación directa y como paquete desde la raíz (todas con salida `0`).

---

## 2. Capa Silver — `@MauroPB30` *(Issues #3 y #4 — por completar)*
- **Herramienta y modelo utilizados:** *(indicar herramienta/modelo si se utiliza IA)*
- **Prompts utilizados:** *(añadir aquí)*
- **Salidas generadas:** *(añadir aquí)*

---

## 3. Capa Gold — `@gorkarmz` *(Issues #5, #6 y #7 — por completar)*
- **Herramienta y modelo utilizados:** *(indicar herramienta/modelo si se utiliza IA)*
- **Prompts utilizados:** *(añadir aquí)*
- **Salidas generadas:** *(añadir aquí)*
