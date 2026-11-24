"""Analítica de negocio de la capa Gold (Mini Lakehouse - Activity 3).

Issue #5: Ventas por cliente (ingresos totales) -> data_lab/gold/sales_by_customer.csv
Issue #6: Ingresos por producto                 -> data_lab/gold/revenue_by_product.csv

Regla de arquitectura Medallion: lee EXCLUSIVAMENTE de ``data_lab/silver/``
(nunca de Bronze). Puede ejecutarse directamente (``python src/gold_analytics.py``)
o como módulo (``python -m src.gold_analytics``) desde la raíz del repositorio.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

# Reutilizamos las rutas centralizadas de src/common.py (Issue #2) con fallback
# seguro por si el script se ejecuta de forma aislada.
try:
    from common import GOLD_DIR, SILVER_DIR, ensure_output_dirs
except ImportError:
    try:
        from src.common import GOLD_DIR, SILVER_DIR, ensure_output_dirs
    except ImportError:
        ROOT = Path(__file__).resolve().parent.parent
        SILVER_DIR = ROOT / "data_lab" / "silver"
        GOLD_DIR = ROOT / "data_lab" / "gold"

        def ensure_output_dirs() -> tuple[Path, Path]:
            SILVER_DIR.mkdir(parents=True, exist_ok=True)
            GOLD_DIR.mkdir(parents=True, exist_ok=True)
            return SILVER_DIR, GOLD_DIR


def find_col(df: pd.DataFrame, candidates: list[str], what: str) -> str:
    """Devuelve la primera columna existente en ``df`` dentro de ``candidates``."""
    for col in candidates:
        if col in df.columns:
            return col
    raise KeyError(f"No encuentro la columna de {what}. Columnas: {list(df.columns)}")


def main() -> None:
    """Calcula las tablas agregadas de la capa Gold y valida su consistencia."""
    ensure_output_dirs()

    # 1) Leer SOLO de la capa Silver (clean_sales.csv y clean_customers.csv).
    sales = pd.read_csv(SILVER_DIR / "clean_sales.csv")
    customers = pd.read_csv(SILVER_DIR / "clean_customers.csv")

    sales_id_col = find_col(sales, ["id_cliente", "customer_id", "id_customer"], "ID de cliente en ventas")
    cust_id_col = find_col(customers, ["id_cliente", "customer_id", "id"], "ID de cliente en clientes")
    amount_col = find_col(sales, ["importe", "amount", "total", "monto", "precio"], "importe")
    product_col = find_col(sales, ["producto", "product"], "producto")
    name_col = find_col(customers, ["nombre", "name"], "nombre")
    country_col = find_col(customers, ["pais", "country"], "pais")

    # Aseguramos tipo numérico en el importe antes de agregar.
    sales[amount_col] = pd.to_numeric(sales[amount_col], errors="coerce")
    sales = sales.dropna(subset=[amount_col])

    # 2) GOLD #5 - Ventas por cliente
    # Join y agrupación por id_cliente (NUNCA solo por nombre): 101 Ana y 111 Ana
    # son clientas distintas y agrupar por nombre mezclaría sus compras.
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
    sales_by_customer.to_csv(GOLD_DIR / "sales_by_customer.csv", index=False, lineterminator="\n")

    total_revenue_customers = float(sales_by_customer["total_sales"].sum())

    # 3) GOLD #6 - Ingresos por producto (desde clean_sales.csv)
    revenue_by_product = (
        sales.groupby(product_col, as_index=False)
        .agg(num_pedidos=(amount_col, "count"), total_revenue=(amount_col, "sum"))
        .rename(columns={product_col: "producto"})
        .sort_values("total_revenue", ascending=False)
    )
    revenue_by_product.to_csv(GOLD_DIR / "revenue_by_product.csv", index=False, lineterminator="\n")

    total_revenue_products = float(revenue_by_product["total_revenue"].sum())

    # 4) Respuestas a las preguntas de negocio del laboratorio
    top_spend = sales_by_customer.iloc[0]
    top_orders = sales_by_customer.sort_values(
        ["num_pedidos", "total_sales"], ascending=False
    ).iloc[0]
    top_product = revenue_by_product.iloc[0]

    print("=== VENTAS POR CLIENTE ===")
    print(sales_by_customer.to_string(index=False))
    print(f"\nTotal revenue (clientes): {total_revenue_customers:.2f}")
    print(
        f"Mayor comprador por gasto:   {top_spend['nombre']} "
        f"(id {top_spend['id_cliente']}) -> {top_spend['total_sales']:.2f}"
    )
    print(
        f"Mayor comprador por pedidos: {top_orders['nombre']} "
        f"(id {top_orders['id_cliente']}) -> {top_orders['num_pedidos']} pedidos / "
        f"{top_orders['total_sales']:.2f}"
    )

    print("\n=== INGRESOS POR PRODUCTO ===")
    print(revenue_by_product.to_string(index=False))
    print(f"\nTotal revenue (productos): {total_revenue_products:.2f}")
    print(
        f"Producto que mas ingresa: {top_product['producto']} "
        f"-> {top_product['total_revenue']:.2f}"
    )

    # Comprobaciones de calidad (Issue #6: que no quede "test" ni el 9999 de Debug).
    assert "test" not in revenue_by_product["producto"].astype(str).str.lower().values, (
        "Producto 'test' sigue en Silver"
    )
    assert (sales[amount_col] != 9999).all(), "Importe 9999 (Debug) sigue en Silver"

    # Si cuadran los dos totales, el inner join no perdió ventas válidas.
    if abs(total_revenue_customers - total_revenue_products) > 0.01:
        print("\nAVISO: los totales difieren -> hay ventas sin cliente valido en Silver.")


if __name__ == "__main__":
    main()
