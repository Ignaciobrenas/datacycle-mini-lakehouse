# Plan: Mini Lakehouse (Datacycle - Unidad 2, Activity 3)

Repo: **datacycle-mini-lakehouse**

Flujo: `data_lab/bronze` (raw) -> `src/silver_clean.py` -> `data_lab/silver` -> `src/gold_analytics.py` -> `data_lab/gold`.

## Reparto (1 capa por persona, carpetas distintas = sin conflictos)
| Persona | Capa | Archivos que SOLO toca esta persona |
|---|---|---|
| A | Bronze | `src/common.py`, `src/bronze_analysis.py`, `docs/bronze_report.md`, `data_lab/bronze/` |
| B | Silver | `src/silver_clean.py`, `data_lab/silver/` |
| C | Gold + entrega | `src/gold_analytics.py`, `data_lab/gold/`, `README.md`, `docs/final_report.md`, `docs/ai_usage.md` |

## Contrato Silver (para que B y C trabajen en paralelo)
- `clean_sales.csv`: `id_pedido,id_cliente,producto,importe` (ints; importe float > 0)
- `clean_customers.csv`: `id_cliente,nombre,pais` (id_cliente int; nombre/pais vacios = `desconocido`)
- Gold lee SOLO de `data_lab/silver/`. C puede empezar con un CSV de ejemplo hasta que B haga merge.

## Hallazgos preliminares en Bronze
- ventas.csv: importe `-10` y `abc`; cliente `999` inexistente en clientes.
- clientes.json: `nombre` vacio (112), `pais` null (117), `id_cliente` como string ("120"), linea en blanco.
- logs.txt: lineas `[ERROR]` / `[WARN]`.
- Nota: el PDF habla de sales.csv/customers.json, pero el ZIP trae ventas.csv/clientes.json. Usamos los del ZIP.

## Reglas de trabajo
1. Una rama por issue: `feat/bronze-*`, `feat/silver-*`, `feat/gold-*`. PR a `main`, revisa otra persona.
2. Nadie edita archivos de otra capa; cambios al contrato -> comentar en el issue.
3. Python con comentarios explicando la logica (requisito del PDF). Si se usa IA: guardar prompts, herramienta y salidas en `docs/ai_usage.md`.
