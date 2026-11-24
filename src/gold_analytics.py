"""
GOLD layer - Mini Lakehouse (Datacycle, Unidad 2)

Issue #5: Ventas por cliente (ingresos totales)  -> data_lab/gold/sales_by_customer.csv
Issue #6: Ingresos por producto                  -> data_lab/gold/revenue_by_product.csv

Regla del lab: se lee SOLO de data_lab/silver/ (nunca de Bronze).
Se ejecuta desde la raiz del repo:  python src/gold_analytics.py
"""

from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
SILVER = ROOT / "data_lab" / "silver"
GOLD = ROOT / "data_lab" / "gold"
GOLD.mkdir(parents=True, exist_ok=True)


def find_col(df, candidates, what):
    """Devuelve la primera columna existente de `candidates` (nombres
    normalizados por Silver pueden variar entre companeros)."""
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"No encuentro la columna de {what}. Columnas: {list(df.columns)}")



# 1) Leer SOLO Silver
sales = pd.read_csv(SILVER / "clean_sales.csv")
customers = pd.read_csv(SILVER / "clean_customers.csv")

sales_id_col = find_col(sales, ["id_cliente", "customer_id", "id_customer"], "ID de cliente en ventas")
cust_id_col = find_col(customers, ["id_cliente", "customer_id", "id"], "ID de cliente en clientes")
amount_col = find_col(sales, ["importe", "amount", "total", "monto", "precio"], "importe")
product_col = find_col(sales, ["producto", "product"], "producto")
name_col = find_col(customers, ["nombre", "name"], "nombre")
country_col = find_col(customers, ["pais", "country"], "pais")


sales[amount_col] = pd.to_numeric(sales[amount_col], errors="coerce")
sales = sales.dropna(subset=[amount_col])

# 2) GOLD #5 - Ventas por cliente
#    Join y agrupacion por ID //NO por nombre//: 101 Ana y 111 Ana son clientes
#    distintos y agrupar por nombre mezclaria sus compras.
merged = sales.merge(
    customers[[cust_id_col, name_col, country_col]],
    left_on=sales_id_col,
    right_on=cust_id_col,
    how="inner", 
)

sales_by_customer = (
    merged.groupby([sales_id_col, name_col, country_col], as_index=False)
    .agg(num_pedidos=(amount_col, "count"), total_sales=(amount_col, "sum"))
    .rename(columns={sales_id_col: "id_cliente", name_col: "nombre", country_col: "pais"})
    .sort_values("total_sales", ascending=False)
)
sales_by_customer.to_csv(GOLD / "sales_by_customer.csv", index=False)

total_revenue_customers = sales_by_customer["total_sales"].sum()


# 3) GOLD #6 - Ingresos por producto //solo clean_sales.csv//
revenue_by_product = (
    sales.groupby(product_col, as_index=False)
    .agg(num_pedidos=(amount_col, "count"), total_revenue=(amount_col, "sum"))
    .rename(columns={product_col: "producto"})
    .sort_values("total_revenue", ascending=False)
)
revenue_by_product.to_csv(GOLD / "revenue_by_product.csv", index=False)

total_revenue_products = revenue_by_product["total_revenue"].sum()

# 4) Respuestas del lab
top_spend = sales_by_customer.iloc[0]
top_orders = sales_by_customer.sort_values(
    ["num_pedidos", "total_sales"], ascending=False).iloc[0]
top_product = revenue_by_product.iloc[0]

print("=== VENTAS POR CLIENTE ===")
print(sales_by_customer.to_string(index=False))
print(f"\nTotal revenue (clientes): {total_revenue_customers:.2f}")
print(f"Mayor comprador por gasto:   {top_spend['nombre']} "
      f"(id {top_spend['id_cliente']}) -> {top_spend['total_sales']:.2f}")
print(f"Mayor comprador por pedidos: {top_orders['nombre']} "
      f"(id {top_orders['id_cliente']}) -> {top_orders['num_pedidos']} pedidos / "
      f"{top_orders['total_sales']:.2f}")

print("\n=== INGRESOS POR PRODUCTO ===")
print(revenue_by_product.to_string(index=False))
print(f"\nTotal revenue (productos): {total_revenue_products:.2f}")
print(f"Producto que mas ingresa: {top_product['producto']} "
      f"-> {top_product['total_revenue']:.2f}")

# Comprobaciones de calidad //issue #6: que no quede "test" ni el 9999 de Debug//
assert "test" not in revenue_by_product["producto"].astype(str).str.lower().values, \
    "Producto 'test' sigue en Silver"
assert (sales[amount_col] != 9999).all(), "Importe 9999 (Debug) sigue en Silver"

# Si cuadran los dos totales, el join no perdio ventas validas
if abs(total_revenue_customers - total_revenue_products) > 0.01:
    print("\nAVISO: los totales difieren -> hay ventas sin cliente valido en Silver.")
