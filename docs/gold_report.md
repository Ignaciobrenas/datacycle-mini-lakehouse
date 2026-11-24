# Informe Capa Gold — Valor Analítico

Análisis automatizado de `data_lab/silver/` mediante [`src/gold_analytics.py`](../src/gold_analytics.py) correspondiente a la **Parte 3 (Gold)** de *Activity 3 – Building a Mini Lakehouse* (issues #5 y #6).

> La capa Gold lee **solo** de `data_lab/silver/` (`clean_sales.csv` y `clean_customers.csv`) y no toca Bronze.

---

## 1. Datasets generados

| Fichero | Contenido | Orden |
|---|---|---|
| `data_lab/gold/sales_by_customer.csv` | `id_cliente,nombre,pais,num_pedidos,total_sales` (1 fila por cliente con ventas) | `total_sales` descendente |
| `data_lab/gold/revenue_by_product.csv` | `producto,num_pedidos,total_revenue` (1 fila por producto) | `total_revenue` descendente |

## 2. Lógica aplicada

1. **Join por `id_cliente`** entre `clean_sales.csv` y `clean_customers.csv` (`inner`, de modo que no entran ventas de clientes inexistentes o de cuentas excluidas en Silver como `201 Debug`).
2. **Agrupación por `id_cliente`, no por `nombre`:** `101 Ana` y `111 Ana` son clientes distintos y agrupar por nombre mezclaría sus compras.
3. **Ingresos por producto** calculados solo desde `clean_sales.csv`.
4. **Comprobaciones automáticas** en el script: no queda el producto `test` ni el importe `9999`, y el total por clientes coincide con el total por productos.

## 3. Resultados

### Ventas por cliente (primeras filas)

| `id_cliente` | `nombre` | `pais` | `num_pedidos` | `total_sales` |
|---:|---|---|---:|---:|
| `106` | Pedro | PT | 1 | 300.0 |
| `101` | Ana | ES | 4 | 290.0 |
| `109` | Elena | FR | 1 | 220.0 |
| `112` | desconocido | ES | 1 | 210.0 |
| `120` | Eva | ES | 1 | 210.0 |

`111 Ana` aparece en una fila aparte (1 pedido, `30.0`).

### Ingresos por producto

| `producto` | `num_pedidos` | `total_revenue` | % del total |
|---|---:|---:|---:|
| `monitor` | 64 | 13190.0 | 80,4 % |
| `teclado` | 66 | 1980.0 | 12,1 % |
| `raton` | 62 | 1245.0 | 7,6 % |

**Total revenue global:** `16415.00` (coincide al sumar por clientes y por productos, lo que confirma que el join no perdió ventas).

---

## 4. Respuestas a las preguntas del PDF

### ¿Quién es el mayor comprador? ¿Qué cliente genera más ingresos?
- **Por gasto total:** **Pedro** (`id_cliente=106`, `PT`) con **300.0** en un único pedido.
- **Por número de pedidos:** **Ana** (`id_cliente=101`, `ES`) con **4 pedidos** y **290.0** (pedidos `1`, `3`, `31` y `32`).
- Si se agrupara por nombre, `Ana` sumaría `101` + `111` (320.0) y pasaría a primer puesto por error. Por eso se agrupa por `id_cliente`.

### ¿Qué producto genera más ingresos?
- **`monitor`**, con **13190.0** (el 80,4 % del total), pese a no ser el producto con más pedidos (`teclado` tiene 66 frente a 64).
- No quedan en Silver el producto `test` ni el importe `9999` de `Debug`, que habrían distorsionado el ranking.

### ¿Hay clientes con información faltante?
Sí, y se conservan en Gold con el valor `desconocido`: el cliente `112` (nombre) y los clientes `117` y `138` (país).

---

## 5. Cómo ejecutarlo

```bash
py src/gold_analytics.py
```

Requiere `pandas` (incluido en `requirements.txt`) y que existan los ficheros de `data_lab/silver/`.