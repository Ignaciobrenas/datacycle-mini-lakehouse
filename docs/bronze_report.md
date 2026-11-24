# Informe Capa Bronze — Análisis de Datos Crudos

Análisis automatizado de `data_lab/bronze/` mediante [`src/bronze_analysis.py`](../src/bronze_analysis.py) correspondiente a la **Parte 1 (Bronze)** de *Activity 3 – Building a Mini Lakehouse*.

> **Equivalencia de nombres respecto al PDF:** el enunciado menciona `sales.csv` y `customers.json`, pero el dataset entregado en el ZIP contiene `ventas.csv` y `clientes.json` (junto con `logs.txt`).

---

## 1. Tipo y estructura de cada fichero

| Fichero | Tipo / Formato | Tamaño | Líneas totales | Registros | Líneas en blanco | Estructura / Campos |
|---|---|---:|---:|---:|---:|---|
| `data_lab/bronze/ventas.csv` | CSV (tabular delimitado por comas) | 3.897 bytes | 218 | 200 pedidos | 17 | `id_pedido,id_cliente,producto,importe` |
| `data_lab/bronze/clientes.json` | JSON (array semiestructurado) | 12.599 bytes | 274 | 250 clientes | 22 | `id_cliente`, `nombre`, `pais` |
| `data_lab/bronze/logs.txt` | Texto plano (log clave=valor) | 6.109 bytes | 207 | 205 eventos | 2 | `[NIVEL] user=<id> action=<accion>` |

---

## 2. Problemas detectados por fichero

### 2.1 `ventas.csv`
- **17 líneas en blanco intercaladas** cada 10 registros a partir del pedido 30 (líneas `32, 43, 54, 65, 76, 87, 98, 109, 120, 131, 142, 153, 164, 175, 186, 197, 208`).
- **`id_cliente` vacío (faltante):** línea `16` → `id_pedido=15, id_cliente="", producto=raton, importe=20`.
- **`id_cliente` huérfano (integridad referencial rota):** línea `6` → `id_pedido=5, id_cliente=999, producto=monitor, importe=150` (el cliente `999` no existe en `clientes.json`).
- **`importe` negativo:** línea `7` → `id_pedido=6, id_cliente=104, producto=raton, importe=-10`.
- **`importe` no numérico:** línea `8` → `id_pedido=7, id_cliente=105, producto=teclado, importe=abc`.
- **`importe == 0` y producto de prueba:** línea `30` → `id_pedido=29, id_cliente=200, producto=test, importe=0` (asociado a `200 TestUser`).
- **`importe` outlier / de depuración (`9999`):** línea `31` → `id_pedido=30, id_cliente=201, producto=monitor, importe=9999` (asociado a `201 Debug`, muy por encima del rango habitual de monitores `150–300`).
- **Ventas adicionales ligadas a cuentas test/debug:** líneas `116` (`id_pedido=107, id_cliente=200, teclado, 30`) y `117` (`id_pedido=108, id_cliente=201, raton, 20`).
- **Pedidos con mismo contenido repetido (distinto `id_pedido`):** los pedidos `1`, `31` y `32` registran `(101, teclado, 30)`. No hay `id_pedido` duplicados, pero conviene revisarlo en analítica.

### 2.2 `clientes.json`
- **22 líneas en blanco intercaladas** dentro del array JSON (es JSON válido al parsear el documento completo, pero fallaría un lector línea a línea).
- **`id_cliente` con tipo incorrecto (`string` en lugar de `int`):** `id_cliente="120"` (`Eva`, `ES`).
- **`nombre` vacío:** `id_cliente=112` (`nombre=""`, `pais="ES"`).
- **`pais` nulo (`null`):** `id_cliente=117` (`nombre="Raul"`, `pais=null`).
- **`pais` con marcador inválido (`"??"`):** `id_cliente=138` (`user8`) y `id_cliente=200` (`TestUser`).
- **Cuentas no productivas (prueba / depuración):** `id_cliente=200` (`TestUser`, `pais="??"`) e `id_cliente=201` (`Debug`, `pais="ES"`).
- **Nombres repetidos entre IDs distintos:** el nombre `Ana` aparece en `id_cliente=101` y en `id_cliente=111`. En Gold es imprescindible agrupar por `id_cliente` y no por `nombre`.
- **Nombres sintéticos genéricos:** 218 clientes tienen nombre `user1`–`user218` (IDs `131–199` y `202–350`). No hay `id_cliente` duplicados (rango continuo `101–350`).

### 2.3 `logs.txt`
- **2 líneas en blanco:** líneas `155` y `186`.
- **Distribución de niveles (205 eventos):** `INFO` (`135`), `ERROR` (`35`), `WARN` (`31`), `DEBUG` (`4`).
- **Eventos `[ERROR]` (35 líneas) y `[DEBUG]` (4 líneas):**
  - Las líneas `[DEBUG]` (`25, 105, 106, 107`) corresponden a `action=test` (usuarios `122, 201, 202, 203`).
  - Los 35 `[ERROR]` incluyen usuarios inexistentes y no numéricos, además de 31 clientes reales de `clientes.json`.
- **Línea sin campo `user=`:** línea `22` → `[INFO] action=compra`.
- **Líneas con `user=` no numérico:** línea `15` (`[ERROR] user=abc action=login`) y línea `124` (`[ERROR] user=xyz action=compra`).
- **Líneas con `user=` huérfano:** línea `4` (`[ERROR] user=999 action=login`) y línea `27` (`[ERROR] user=999 action=compra`).
- **Líneas con `action=` vacío:** línea `23` (`[INFO] user=120 action=`) y línea `117` (`[INFO] user=213 action=`).

---

## 3. Respuestas a las preguntas del PDF

### ¿Qué datos no son fiables?
1. **Importes corruptos o no comerciales en `ventas.csv`:** el importe negativo (`-10`), el texto no numérico (`abc`), el importe cero de prueba (`0` en `producto=test`), y el outlier `9999` de la cuenta `Debug` (`id_pedido=30`), que por sí solo distorsionaría por completo el ranking de clientes y el total de ingresos en Gold.
2. **Ventas sin relación válida con un cliente real:** pedido `15` (sin `id_cliente`), pedido `5` (`id_cliente=999` inexistente) y pedidos `29, 30, 107, 108` vinculados a `TestUser`/`Debug`.
3. **Registros de log `[ERROR]`, `[DEBUG]` y malformados en `logs.txt`:** no representan actividad válida de negocio (incluyen IDs inexistentes como `999` o strings `abc`/`xyz`, falta de `user=` y `action=` vacío).
4. **Valores placeholder en `clientes.json`:** `pais="??"` (`138`, `200`), `TestUser`/`Debug` y nombres genéricos `user1..user218` (útiles para integridad de IDs, pero no representativos de nombres reales).

### ¿Qué información falta?
- **Faltante a nivel de registro:**
  - `id_cliente` en `ventas.csv` (pedido `15`).
  - `nombre` en `clientes.json` (`id_cliente=112`).
  - `pais` en `clientes.json` (`id_cliente=117` con `null`, más `138` y `200` con `"??"`).
  - `user=` en `logs.txt` (línea `22`) y `action=` en `logs.txt` (líneas `23` y `117`).
- **Faltante a nivel de modelo/contexto (ausente en el esquema):**
  - Fechas o marcas temporales (`timestamp`) tanto en ventas como en logs (impide análisis temporal o cruzar cada compra del log con una fecha de pedido).
  - Cantidad de unidades, identificador de producto o catálogo maestro de productos/precios (impide validar automáticamente si un `monitor` a `9999` es un error o una compra de varias unidades).

### ¿Qué registros son inválidos?
- **En `ventas.csv`:**
  - Directamente inválidos por esquema/tipo/integridad: pedidos **`5`** (`id_cliente=999`), **`6`** (`importe=-10`), **`7`** (`importe=abc`), **`15`** (`id_cliente` vacío) y **`29`** (`producto=test`, `importe=0`).
  - Inválidos por pertenecer a cuentas test/debug y/o valor atípico: pedido **`30`** (`id_cliente=201 Debug`, `importe=9999`), además de **`107`** (`200 TestUser`) y **`108`** (`201 Debug`) si en Silver se excluyen las cuentas de prueba/depuración.
- **En `clientes.json`:**
  - Cuentas no productivas: **`200`** (`TestUser`, `pais="??"`) y **`201`** (`Debug`, `pais="ES"`).
  - Formato incorrecto recuperable: **`120`** (`id_cliente` como string `"120"`).
- **En `logs.txt`:**
  - Las **35** líneas `[ERROR]` (incluyendo `user=999`, `user=abc`, `user=xyz`), las **4** líneas `[DEBUG]`, la línea `22` (sin `user=`), las líneas `23` y `117` (`action=` vacío) y las **2** líneas en blanco (`155`, `186`).

### ¿Qué clientes tienen información incompleta?
| `id_cliente` | `nombre` | `pais` | Problema |
|---:|---|---|---|
| `112` | `""` (vacío) | `ES` | Falta el nombre del cliente |
| `117` | `Raul` | `null` | Falta el país (`null`) |
| `138` | `user8` | `??` | País marcado como desconocido (`??`) |
| `200` | `TestUser` | `??` | Cuenta de prueba y país inválido (`??`) |
| `120` | `Eva` | `ES` | Completo en contenido, pero `id_cliente` viene como string (`"120"`) en lugar de entero |

---

## 4. Notas clave para Silver y Gold

1. **Silver (`clean_customers.csv`):** normalizar `id_cliente` a `int`, convertir `nombre` vacío y `pais` `null`/`"??"` a `desconocido`, deduplicar por `id_cliente` (nunca por `nombre`, por existir `101 Ana` y `111 Ana`) y excluir `200 TestUser` y `201 Debug`.
2. **Silver (`clean_logs.csv`):** descartar `[ERROR]`, `[DEBUG]`, líneas en blanco y malformadas, **sin eliminar de `clean_customers.csv` a los 31 clientes reales** que tienen algún evento `[ERROR]` en `logs.txt`.
3. **Silver (`clean_sales.csv`):** ignorar líneas en blanco, exigir `id_pedido` e `id_cliente` enteros válidos y existentes en `clean_customers.csv`, y mantener solo `importe > 0` excluyendo `test` y el outlier `9999` de `Debug`.
4. **Gold:** agrupar ventas por `id_cliente` antes de mostrar el nombre del cliente para no fusionar `101 Ana` y `111 Ana`.

---

## 5. Documentación de la implementación y verificación (Issue #1)

### ¿Qué se ha implementado?
En [`src/bronze_analysis.py`](../src/bronze_analysis.py) se ha desarrollado un analizador automatizado en Python puro (sin modificar los ficheros crudos de `data_lab/bronze/` y con comentarios explicativos de la lógica tal como exige el PDF):

- **Resolución de rutas desacoplada:** intenta importar `BRONZE_DIR` desde `common` / `src.common` (Issue #2) y hace fallback a `data_lab/bronze/` para funcionar de forma autónoma antes del merge de `common.py`.
- **`analyze_customers(path)`:** lee `clientes.json` preservando el conteo de líneas crudas y en blanco, detecta `id_cliente` no enteros (`"120"`), `nombre` vacío (`112`), `pais` `null`/`"??"` (`117`, `138`, `200`), cuentas de prueba/debug (`200`, `201`), nombres duplicados (`Ana`) y genera el conjunto de IDs conocidos para validación cruzada.
- **`analyze_sales(path, known_customer_ids, test_debug_ids)`:** recorre `ventas.csv` línea a línea conservando el número de línea original y detecta líneas en blanco, columnas malformadas, `id_cliente` vacío/no numérico/huérfano, importes no numéricos/negativos/cero/outliers (`> 1000.0`), producto `test`, ventas de cuentas `TestUser`/`Debug` y pedidos repetidos.
- **`analyze_logs(path, known_customer_ids)`:** parsea `logs.txt` mediante regex `^\[(?P<level>[A-Z]+)\]\s*(?P<body>.*)$`, contabiliza niveles y acciones, detecta líneas en blanco, ausencias de `user=`, usuarios no numéricos/huérfanos, `action=` vacío e identifica qué clientes válidos aparecen en líneas `[ERROR]`.
- **`print_report(...)`:** imprime un resumen completo por fichero y una síntesis automática con los totales de anomalías.

### Cómo ejecutarlo
```bash
python src/bronze_analysis.py
# o como módulo desde la raíz:
python -m src.bronze_analysis
```

### Verificación realizada
- Ejecución directa (`python src/bronze_analysis.py`) y como módulo (`python -m src.bronze_analysis`) finalizadas con código de salida `0`.
- Validados todos los conteos e índices sobre los tres ficheros de `data_lab/bronze/` (`ventas.csv`: 218 líneas / 200 registros / 6 anomalías directas + 4 ventas `TestUser`/`Debug`; `clientes.json`: 274 líneas / 250 registros / 1 nombre vacío / 3 países inválidos / 1 ID string; `logs.txt`: 207 líneas / 205 eventos / 35 `ERROR`, 31 `WARN`, 4 `DEBUG`).
