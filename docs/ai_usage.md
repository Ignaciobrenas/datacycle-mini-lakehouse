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

## 2. Capa Silver — `@Ignaciobrenas` (Issue #3) y `@gorkarmz` (Issue #4)

### Issue #3 — Limpieza y normalización de ventas (`@Ignaciobrenas`)
- **Herramienta y modelo utilizados:** Google Antigravity (`Gemini 4 Hydrogen`)
- **Prompt utilizado:**
  > Implementa el Issue #3 en `src/silver_clean.py` (`clean_sales`) y genera automáticamente `data_lab/silver/clean_sales.csv`: ignora las líneas en blanco de `ventas.csv`, filtra IDs nulos/vacíos/no válidos, importes no numéricos o `<= 0`, registros de prueba/debug y outliers artificiales (`producto=test`, `importe=9999`, cuentas `TestUser`/`Debug`) y clientes inexistentes; normaliza nombres y tipos (`id_pedido` e `id_cliente` `int`, `producto` en minúsculas, `importe` `float`), deduplica por `id_pedido`, comenta la lógica del script y verifica el resultado.
- **Salidas generadas:**
  - Implementación comentada de `src/silver_clean.py` (`_parse_positive_int`, `_parse_positive_float`, `load_valid_customer_ids`, `clean_sales`, `main`), preparada para integrarse con `clean_customers()` y `clean_logs()` en el Issue #4.
  - Generación automática de `data_lab/silver/clean_sales.csv` tras ejecutar `python src/silver_clean.py` y `python -m src.silver_clean` (código de salida `0`):
    - Líneas crudas leídas: `218` (`17` líneas en blanco ignoradas, `200` filas de datos).
    - Registros descartados: `8` (`id_pedido` `5, 6, 7, 15, 29, 30, 107, 108`).
    - Registros limpios escritos en `clean_sales.csv`: `192` (`id_pedido,id_cliente,producto,importe`), ordenados por `id_pedido` ascendente y validados mediante aserciones de esquema, tipos e integridad referencial.

### Issue #4 — Limpieza de clientes y logs (`@gorkarmz`)
- **Herramienta y modelo utilizados:** Google Antigravity (`Gemini 3.8 Flash`)
- **Prompt utilizado:**
  > Revisa en la rama `4-silver-limpiar-clientes-y-logs---clean_customerscsv` la Issue #4 e implementa todo lo requerido:
  > - Parsear `data_lab/bronze/clientes.json` (array JSON con líneas en blanco intercaladas) y convertir `id_cliente` a `int` (ej. `"120"` -> `120`).
  > - Normalizar valores faltantes o inválidos: `nombre` vacío/null (`112`) -> `desconocido`; `pais` null, vacío o `"??"` (`117`, `138`, `200`) -> `desconocido`; limpiar espacios y estandarizar formato (país en mayúsculas salvo `desconocido`).
  > - Filtrar cuentas de prueba/debug (`200 TestUser`, `201 Debug`) para evitar distorsiones en Gold.
  > - Deduplicar clientes por `id_cliente` (sin deduplicar por `nombre`, preservando `101 Ana` y `111 Ana`).
  > - Limpiar `data_lab/bronze/logs.txt` (`clean_logs`): descartar líneas en blanco, eventos `[ERROR]`, eventos `[DEBUG]` (`action=test`), líneas sin `user=` (línea 22) o con `action=` vacío (líneas 23, 117), y usuarios no numéricos o inexistentes (`abc`, `xyz`, `999`); estandarizar `user` a `id_cliente` (`int`) y exportar `clean_logs.csv` (`nivel,id_cliente,action`) sin eliminar clientes reales con errores en log de `clean_customers.csv`.
  > - Procesamiento 100% automático en Python en `src/silver_clean.py` comentado explicando la lógica y trazabilidad en `docs/ai_usage.md`.
- **Salidas generadas:**
  - Implementación completa, tipada y comentada de `clean_customers()` y `clean_logs()` en `src/silver_clean.py`, actualizando `main()` para ejecutar la secuencia completa de la capa Silver (`clean_customers` -> `clean_logs` -> `clean_sales`).
  - Generación de `data_lab/silver/clean_customers.csv` (`248` registros limpios, `id_cliente,nombre,pais`):
    - 250 registros procesados desde `clientes.json` (22 líneas en blanco ignoradas).
    - Conversión de `id_cliente` `"120"` a entero `120`.
    - Normalización de cliente `112` con `nombre` vacío a `desconocido`.
    - Normalización de país en cliente `117` (`null`) y `138` (`"??"`) a `desconocido`.
    - Conversión de países válidos a mayúsculas (`ES`, `FR`, `IT`, `PT`, `DE`, `UK`).
    - Exclusión de cuentas sintéticas `200 TestUser` y `201 Debug`.
    - Preservación de clientes homónimos `101 Ana` y `111 Ana`.
    - Orden determinista por `id_cliente` ascendente.
  - Generación de `data_lab/silver/clean_logs.csv` (`162` registros limpios, `nivel,id_cliente,action`):
    - 207 líneas analizadas de `logs.txt`.
    - Descarte de 45 registros defectuosos o excluidos: 2 líneas en blanco, 35 eventos `[ERROR]` (incluyendo `user=999`, `user=abc`, `user=xyz`), 4 eventos `[DEBUG]` (`action=test`, incluyendo `user=201`), 1 línea sin `user=` (línea 22), 2 líneas con `action=` vacío (líneas 23 y 117) y 1 evento de cuenta test/debug (`user=200`, línea 104).
    - Estandarización de `user` a `id_cliente` (`int`) y preservación de niveles legítimos (`INFO`, `WARN`).
    - Validación de que los 31 clientes reales con errores en los logs se mantienen intactos en `clean_customers.csv`.
  - Verificación exitosa mediante ejecución directa `python src/silver_clean.py` y como módulo `python -m src.silver_clean` con código de salida `0` y aserciones completas de integridad.

---

## 3. Capa Gold — `@gorkarmz` *(Issues #5, #6 y #7 — por completar)*
- **Herramienta y modelo utilizados:** *(indicar herramienta/modelo si se utiliza IA)*
- **Prompts utilizados:** *(añadir aquí)*
- **Salidas generadas:** *(añadir aquí)*
