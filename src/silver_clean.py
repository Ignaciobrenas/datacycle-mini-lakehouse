"""Limpieza y normalización de la capa Silver (Mini Lakehouse - Activity 3).

Transforma los datos crudos de ``data_lab/bronze/`` en datasets limpios,
tipados y normalizados dentro de ``data_lab/silver/`` sin edición manual.

Alcance actual:
- Issue #3 (``clean_sales``): limpieza, validación referencial, tipado y
  normalización de ``ventas.csv`` -> ``data_lab/silver/clean_sales.csv``.
- Punto de integración preparado para Issue #4 (``clean_customers`` y
  ``clean_logs``) en ``main()``.
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

# Reutilizamos las rutas comunes de src/common.py (Issue #2) soportando tanto
# ejecución directa (`python src/silver_clean.py`) como modular (`python -m src.silver_clean`).
try:
    from common import BRONZE_DIR, SILVER_DIR, ensure_output_dirs
except ImportError:
    from src.common import BRONZE_DIR, SILVER_DIR, ensure_output_dirs

# Contrato de columnas estándar para clean_sales.csv.
SALES_COLUMNS: tuple[str, ...] = ("id_pedido", "id_cliente", "producto", "importe")

# Cuentas y productos sintéticos de prueba/depuración detectados en Bronze.
TEST_DEBUG_CUSTOMER_NAMES: set[str] = {"testuser", "debug"}
EXCLUDED_PRODUCTS: set[str] = {"test"}

# En Bronze todos los importes legítimos están entre 20.0 y 300.0; el valor
# 9999 (id_pedido=30, cliente 201 Debug) es un outlier artificial de depuración.
MAX_VALID_AMOUNT: float = 1000.0


def _parse_positive_int(raw_value: Any) -> int | None:
    """Convierte un valor a entero estricto > 0; devuelve None si es inválido."""
    if raw_value is None or isinstance(raw_value, bool):
        return None
    text = str(raw_value).strip()
    if not text:
        return None
    try:
        value = int(text)
    except ValueError:
        return None
    return value if value > 0 else None


def _parse_positive_float(raw_value: Any) -> float | None:
    """Convierte un valor a float finito > 0; devuelve None si es inválido."""
    if raw_value is None or isinstance(raw_value, bool):
        return None
    text = str(raw_value).strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return value


def load_valid_customer_ids(
    silver_customers_path: Path = SILVER_DIR / "clean_customers.csv",
    bronze_customers_path: Path = BRONZE_DIR / "clientes.json",
) -> tuple[set[int], str]:
    """Obtiene el conjunto de ``id_cliente`` válidos para integridad referencial.

    Prioriza ``data_lab/silver/clean_customers.csv`` (generado por el Issue #4).
    Si todavía no existe en disco, utiliza ``data_lab/bronze/clientes.json``
    aplicando las mismas reglas base (ID entero y exclusión de cuentas
    ``TestUser`` / ``Debug``) para que ``clean_sales`` funcione de forma
    independiente desde ya.
    """
    valid_ids: set[int] = set()

    if silver_customers_path.is_file():
        with silver_customers_path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                cid = _parse_positive_int(row.get("id_cliente"))
                name = str(row.get("nombre") or "").strip().lower()
                if cid is not None and name not in TEST_DEBUG_CUSTOMER_NAMES:
                    valid_ids.add(cid)
        return valid_ids, str(silver_customers_path)

    # Fallback mientras no exista clean_customers.csv en Silver.
    customers = json.loads(bronze_customers_path.read_text(encoding="utf-8"))
    for record in customers:
        cid = _parse_positive_int(record.get("id_cliente"))
        name = str(record.get("nombre") or "").strip().lower()
        if cid is not None and name not in TEST_DEBUG_CUSTOMER_NAMES:
            valid_ids.add(cid)
    return valid_ids, f"{bronze_customers_path} (fallback sin TestUser/Debug)"


def clean_sales(
    sales_path: Path = BRONZE_DIR / "ventas.csv",
    output_path: Path = SILVER_DIR / "clean_sales.csv",
    valid_customer_ids: set[int] | None = None,
) -> dict[str, Any]:
    """Limpia y normaliza ``ventas.csv`` generando ``data_lab/silver/clean_sales.csv``.

    Reglas aplicadas:
    1. Ignora líneas en blanco intercaladas en el CSV crudo.
    2. Normaliza los nombres de cabecera (``strip().lower()``) y valida esquema.
    3. Descarta registros con ``id_pedido`` o ``id_cliente`` nulos, vacíos o no
       enteros positivos.
    4. Descarta importes no numéricos, ``<= 0`` o superiores al umbral de
       outlier artificial (``9999``).
    5. Descarta productos de prueba (``test``) y clientes inexistentes o
       pertenecientes a cuentas ``TestUser``/``Debug``.
    6. Normaliza ``producto`` (``strip().lower()``) y ``importe`` (``float``
       redondeado a 2 decimales), deduplica por ``id_pedido`` y ordena por
       ``id_pedido`` ascendente.
       Nota: los pedidos ``1``, ``31`` y ``32`` comparten cliente/producto/importe
       (``101, teclado, 30``), pero tienen distinto ``id_pedido``, por lo que
       representan compras distintas válidas y se conservan.
    """
    ensure_output_dirs()

    if valid_customer_ids is None:
        valid_customer_ids, customers_source = load_valid_customer_ids()
    else:
        customers_source = "parámetro explícito"

    raw_lines = sales_path.read_text(encoding="utf-8-sig").splitlines()
    blank_lines = 0
    header: list[str] | None = None
    data_rows = 0
    dropped_reasons: Counter[str] = Counter()
    seen_order_ids: set[int] = set()
    clean_rows: list[dict[str, Any]] = []

    for line_no, raw_line in enumerate(raw_lines, start=1):
        # Saltamos líneas completamente vacías antes de pasarlas al parser CSV.
        if not raw_line.strip():
            blank_lines += 1
            continue

        parsed = next(csv.reader([raw_line]))
        if header is None:
            # Estandarizamos nombres de columna a snake_case en minúsculas.
            header = [col.strip().lower() for col in parsed]
            if tuple(header) != SALES_COLUMNS:
                raise ValueError(
                    f"Cabecera inesperada en {sales_path} (línea {line_no}): {header}"
                )
            continue

        data_rows += 1
        if len(parsed) != len(header):
            dropped_reasons["columnas_invalidas"] += 1
            continue

        raw_row = dict(zip(header, parsed))

        order_id = _parse_positive_int(raw_row["id_pedido"])
        if order_id is None:
            dropped_reasons["id_pedido_invalido"] += 1
            continue

        customer_id = _parse_positive_int(raw_row["id_cliente"])
        if customer_id is None:
            dropped_reasons["id_cliente_vacio_o_invalido"] += 1
            continue

        product = raw_row["producto"].strip().lower()
        if not product:
            dropped_reasons["producto_vacio"] += 1
            continue
        if product in EXCLUDED_PRODUCTS:
            dropped_reasons["producto_test"] += 1
            continue

        amount = _parse_positive_float(raw_row["importe"])
        if amount is None:
            dropped_reasons["importe_no_numerico_o_no_positivo"] += 1
            continue
        if amount > MAX_VALID_AMOUNT:
            dropped_reasons["importe_outlier_debug"] += 1
            continue

        if customer_id not in valid_customer_ids:
            dropped_reasons["id_cliente_inexistente_o_test"] += 1
            continue

        if order_id in seen_order_ids:
            dropped_reasons["id_pedido_duplicado"] += 1
            continue

        seen_order_ids.add(order_id)
        clean_rows.append(
            {
                "id_pedido": order_id,
                "id_cliente": customer_id,
                "producto": product,
                "importe": round(amount, 2),
            }
        )

    # Orden determinista por clave primaria para facilitar revisiones y diffs.
    clean_rows.sort(key=lambda row: row["id_pedido"])

    with output_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SALES_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(clean_rows)

    return {
        "input_path": str(sales_path),
        "output_path": str(output_path),
        "customers_source": customers_source,
        "raw_lines": len(raw_lines),
        "blank_lines_skipped": blank_lines,
        "data_rows_read": data_rows,
        "clean_rows_written": len(clean_rows),
        "dropped_total": sum(dropped_reasons.values()),
        "dropped_reasons": dict(dropped_reasons),
    }


def main() -> None:
    """Ejecuta las transformaciones disponibles de la capa Silver."""
    ensure_output_dirs()

    # Nota para Issue #4: cuando se implementen clean_customers() y clean_logs(),
    # deben ejecutarse antes de clean_sales() para que clean_sales() tome los
    # IDs válidos directamente desde data_lab/silver/clean_customers.csv.
    sales_summary = clean_sales()

    print("=" * 68)
    print("SILVER LAYER - LIMPIEZA DE VENTAS (Issue #3)")
    print("=" * 68)
    print(f"Origen ventas       : {sales_summary['input_path']}")
    print(f"Fuente IDs clientes : {sales_summary['customers_source']}")
    print(f"Salida generada     : {sales_summary['output_path']}")
    print(
        f"Líneas crudas: {sales_summary['raw_lines']} | "
        f"En blanco ignoradas: {sales_summary['blank_lines_skipped']} | "
        f"Filas leídas: {sales_summary['data_rows_read']}"
    )
    print(
        f"Registros descartados: {sales_summary['dropped_total']} "
        f"{sales_summary['dropped_reasons']}"
    )
    print(f"Registros limpios escritos: {sales_summary['clean_rows_written']}")


if __name__ == "__main__":
    main()
