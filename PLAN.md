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
- `clean_sales.csv`: `id_pedido,id_cliente,producto,importe` (`id_pedido`, `id_cliente` int; `importe` float > 0; sin registros de prueba `test`/outlier `9999` ni clientes inexistentes/test/debug)
- `clean_customers.csv`: `id_cliente,nombre,pais` (`id_cliente` int; `nombre` vacío/null y `pais` `null`/vacío/`??` = `desconocido`; sin cuentas `TestUser`/`Debug`)
- `clean_logs.csv`: `nivel,id_cliente,action` (sin `[ERROR]`, `[DEBUG]`, líneas en blanco o malformadas; sin eliminar clientes válidos de `clean_customers.csv`)
- Gold lee SOLO de `data_lab/silver/`, agrupando ventas por `id_cliente` (hay dos clientes `Ana`: `101` y `111`). C puede empezar con un CSV de ejemplo hasta que B haga merge.

## Hallazgos preliminares en Bronze
- `ventas.csv`: 17 líneas en blanco; `id_cliente` vacío (pedido `15`); cliente `999` inexistente (pedido `5`); importe `-10` (pedido `6`), `abc` (pedido `7`), `0` con producto `test` (pedido `29`) y outlier `9999` del cliente `201 Debug` (pedido `30`); pedidos repetidos (`id_pedido` 1, 31, 32).
- `clientes.json`: `nombre` vacío (`112`), `pais` `null` (`117`) y `"??"` (`138`, `200`), `id_cliente` como string (`"120"`), cuentas de prueba/debug (`200 TestUser`, `201 Debug`), nombre duplicado (`Ana` en `101` y `111`), líneas en blanco intercaladas en el array JSON.
- `logs.txt`: 2 líneas en blanco; `[ERROR]` (35, incl. `user=999`, `user=abc`, `user=xyz`), `[WARN]` (31), `[DEBUG]` (4); línea sin `user=` (22) y con `action=` vacío (23, 117).
- Nota: el PDF habla de `sales.csv`/`customers.json`, pero el ZIP trae `ventas.csv`/`clientes.json`. Usamos los del ZIP y lo documentamos.

## Reglas de trabajo
1. Una rama por issue: `feat/bronze-*`, `feat/silver-*`, `feat/gold-*`. PR a `main`, revisa otra persona.
2. Nadie edita archivos de otra capa; cambios al contrato -> comentar en el issue.
3. Procesamiento automático (sin editar CSV a mano) y Python con comentarios explicando la lógica (requisito del PDF). Si se usa IA: guardar prompts, herramienta y salidas en `docs/ai_usage.md`.
