"""Limpieza y normalización de la capa Silver (Mini Lakehouse - Activity 3).

Transforma los datos crudos de ``data_lab/bronze/`` en datasets limpios,
tipados y normalizados dentro de ``data_lab/silver/`` sin edición manual.

Alcance:
- Issue #3 (``clean_sales``): limpieza, validación referencial, tipado y
  normalización de ``ventas.csv`` -> ``data_lab/silver/clean_sales.csv``.
- Issue #4 (``clean_customers``): parseo de ``clientes.json``, tipado de ``id_cliente``,
  normalización de valores faltantes/inválidos ("desconocido", formato mayúsculas),
  filtrado de cuentas de prueba/debug y deduplicación por ID -> ``data_lab/silver/clean_customers.csv``.
- Issue #4 (``clean_logs``): depuración de ``logs.txt``, descarte de niveles
  ERROR/DEBUG, líneas malformadas o campos vacíos, filtrado de usuarios no numéricos/huérfanos
  y estandarización de columnas -> ``data_lab/silver/clean_logs.csv``.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

# Reutilizamos las rutas comunes de src/common.py (Issue #2) soportando tanto
# ejecución directa (`python src/silver_clean.py`) como modular (`python -m src.silver_clean`).
try:
    from common import BRONZE_DIR, SILVER_DIR, ensure_output_dirs
except ImportError:
    from src.common import BRONZE_DIR, SILVER_DIR, ensure_output_dirs

# Contratos de columnas estándar para los datasets de la capa Silver.
SALES_COLUMNS: tuple[str, ...] = ("id_pedido", "id_cliente", "producto", "importe")
CUSTOMERS_COLUMNS: tuple[str, ...] = ("id_cliente", "nombre", "pais")
LOGS_COLUMNS: tuple[str, ...] = ("nivel", "id_cliente", "action")

# Cuentas y productos sintéticos de prueba/depuración detectados en Bronze.
# Se descartan para evitar sesgar las métricas de negocio en la capa Gold.
TEST_DEBUG_CUSTOMER_NAMES: set[str] = {"testuser", "debug"}
TEST_DEBUG_CUSTOMER_IDS: set[int] = {200, 201}
EXCLUDED_PRODUCTS: set[str] = {"test"}

# En Bronze todos los importes legítimos están entre 20.0 y 300.0; el valor
# 9999 (id_pedido=30, cliente 201 Debug) es un outlier artificial de depuración.
MAX_VALID_AMOUNT: float = 1000.0

# Marcadores de valores faltantes o corruptos para clientes.
INVALID_COUNTRY_MARKERS: set[str] = {"??", "null", "none"}
UNKNOWN_VALUE: str = "desconocido"

# Niveles de log a excluir: ERROR (anomalías/fallos) y DEBUG (eventos de testing).
EXCLUDED_LOG_LEVELS: set[str] = {"ERROR", "DEBUG"}

# Patrón regex para parsear eventos estructurados en logs.txt: [NIVEL] clave=valor ...
LOG_LINE_PATTERN: re.Pattern[str] = re.compile(r"^\[(?P<level>[A-Z]+)\]\s*(?P<body>.*)$")


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
    ``TestUser`` / ``Debug``) como respaldo seguro.
    """
    valid_ids: set[int] = set()

    if silver_customers_path.is_file():
        with silver_customers_path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                cid = _parse_positive_int(row.get("id_cliente"))
                name = str(row.get("nombre") or "").strip().lower()
                if (
                    cid is not None
                    and name not in TEST_DEBUG_CUSTOMER_NAMES
                    and cid not in TEST_DEBUG_CUSTOMER_IDS
                ):
                    valid_ids.add(cid)
        return valid_ids, str(silver_customers_path)

    # Fallback mientras no exista clean_customers.csv en Silver.
    customers = json.loads(bronze_customers_path.read_text(encoding="utf-8"))
    for record in customers:
        cid = _parse_positive_int(record.get("id_cliente"))
        name = str(record.get("nombre") or "").strip().lower()
        if (
            cid is not None
            and name not in TEST_DEBUG_CUSTOMER_NAMES
            and cid not in TEST_DEBUG_CUSTOMER_IDS
        ):
            valid_ids.add(cid)
    return valid_ids, f"{bronze_customers_path} (fallback sin TestUser/Debug)"


def clean_customers(
    customers_path: Path = BRONZE_DIR / "clientes.json",
    output_path: Path = SILVER_DIR / "clean_customers.csv",
) -> dict[str, Any]:
    """Limpia y normaliza ``clientes.json`` generando ``data_lab/silver/clean_customers.csv``.

    Reglas aplicadas:
    1. Parseo automático de JSON tolerando líneas en blanco intercaladas en el array.
    2. Conversión estricta de ``id_cliente`` a entero positivo (ej. ``"120"`` -> ``120``).
    3. Normalización de valores faltantes o inválidos:
       - ``nombre`` vacío/null (ej. cliente 112) -> ``"desconocido"``.
       - ``pais`` null, vacío o marcador inválido (``"??"``, ej. 117, 138, 200) -> ``"desconocido"``.
       - Limpieza de espacios en blanco y estandarización a mayúsculas (salvo ``"desconocido"``).
    4. Exclusión de cuentas sintéticas de test/debug (``200 TestUser``, ``201 Debug``)
       para no distorsionar las métricas de Gold (coordinado con Issue #3).
    5. Deduplicación por ``id_cliente`` (conservando clientes homónimos como ``101 Ana``
       y ``111 Ana`` por tratarse de clientes distintos con diferente ID).
    6. Orden determinista por ``id_cliente`` ascendente y exportación a CSV con
       columnas (``id_cliente,nombre,pais``).
    """
    ensure_output_dirs()

    raw_text = customers_path.read_text(encoding="utf-8")
    raw_lines = raw_text.splitlines()
    blank_lines = sum(1 for line in raw_lines if not line.strip())

    records = json.loads(raw_text)
    if not isinstance(records, list):
        raise ValueError(
            f"Se esperaba una lista JSON en {customers_path}, pero se obtuvo {type(records).__name__}"
        )

    dropped_reasons: Counter[str] = Counter()
    seen_customer_ids: set[int] = set()
    clean_rows: list[dict[str, Any]] = []

    for record in records:
        if not isinstance(record, dict):
            dropped_reasons["registro_no_objeto"] += 1
            continue

        customer_id = _parse_positive_int(record.get("id_cliente"))
        if customer_id is None:
            dropped_reasons["id_cliente_invalido"] += 1
            continue

        # Normalizamos nombre: si viene vacío o null, se asigna "desconocido".
        raw_name = record.get("nombre")
        name = str(raw_name).strip() if raw_name is not None else ""
        if not name:
            name = UNKNOWN_VALUE

        # Filtramos cuentas de prueba o depuración (200 TestUser, 201 Debug).
        if (
            name.lower() in TEST_DEBUG_CUSTOMER_NAMES
            or customer_id in TEST_DEBUG_CUSTOMER_IDS
        ):
            dropped_reasons["cuenta_test_o_debug"] += 1
            continue

        # Normalizamos país: null, vacío o "??" -> "desconocido".
        # Si es un país válido, se pasa a mayúsculas (ej. "ES", "FR", "DE").
        raw_country = record.get("pais")
        country = str(raw_country).strip() if raw_country is not None else ""
        if (
            not country
            or country.lower() in INVALID_COUNTRY_MARKERS
            or country.lower() == UNKNOWN_VALUE
        ):
            country = UNKNOWN_VALUE
        else:
            country = country.upper()

        # Deduplicamos por id_cliente (nunca por nombre, respetando clientes homónimos).
        if customer_id in seen_customer_ids:
            dropped_reasons["id_cliente_duplicado"] += 1
            continue

        seen_customer_ids.add(customer_id)
        clean_rows.append(
            {
                "id_cliente": customer_id,
                "nombre": name,
                "pais": country,
            }
        )

    # Orden determinista por clave primaria para facilitar auditorías y diffs.
    clean_rows.sort(key=lambda row: row["id_cliente"])

    with output_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CUSTOMERS_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(clean_rows)

    return {
        "input_path": str(customers_path),
        "output_path": str(output_path),
        "raw_lines": len(raw_lines),
        "blank_lines_skipped": blank_lines,
        "records_read": len(records),
        "clean_rows_written": len(clean_rows),
        "dropped_total": sum(dropped_reasons.values()),
        "dropped_reasons": dict(dropped_reasons),
    }


def clean_logs(
    logs_path: Path = BRONZE_DIR / "logs.txt",
    output_path: Path = SILVER_DIR / "clean_logs.csv",
    valid_customer_ids: set[int] | None = None,
) -> dict[str, Any]:
    """Limpia y normaliza ``logs.txt`` generando ``data_lab/silver/clean_logs.csv``.

    Reglas aplicadas:
    1. Descarta líneas en blanco y registros no conformes con el formato ``[NIVEL] ...``.
    2. Descarta eventos con nivel ``[ERROR]`` y ``[DEBUG]`` (ej. ``action=test``).
    3. Descarta líneas malformadas sin campo ``user=`` (ej. línea 22) o con ``action=``
       vacío (ej. líneas 23 y 117).
    4. Descarta eventos asociados a usuarios no numéricos (``abc``, ``xyz``) o
       inexistentes en la dimensión limpia de clientes (``999`` o cuentas test/debug).
    5. Estandariza el campo de usuario a ``id_cliente`` (entero positivo) y normaliza
       la acción en minúsculas.
    6. Exporta el dataset ordenado conservando la secuencia de logs a CSV con
       columnas (``nivel,id_cliente,action``).

    Nota de negocio: no elimina clientes reales de ``clean_customers.csv`` por
    haber experimentado eventos de error en los logs crudos.
    """
    ensure_output_dirs()

    if valid_customer_ids is None:
        valid_customer_ids, customers_source = load_valid_customer_ids()
    else:
        customers_source = "parámetro explícito"

    raw_lines = logs_path.read_text(encoding="utf-8").splitlines()
    dropped_reasons: Counter[str] = Counter()
    clean_rows: list[dict[str, Any]] = []

    for raw_line in raw_lines:
        stripped = raw_line.strip()
        if not stripped:
            dropped_reasons["linea_en_blanco"] += 1
            continue

        match = LOG_LINE_PATTERN.match(stripped)
        if not match:
            dropped_reasons["linea_malformada"] += 1
            continue

        level = match.group("level").upper()
        if level in EXCLUDED_LOG_LEVELS:
            if level == "ERROR":
                dropped_reasons["nivel_error"] += 1
            else:
                dropped_reasons["nivel_debug"] += 1
            continue

        body = match.group("body")
        kv_pairs: dict[str, str] = {}
        for token in body.split():
            if "=" in token:
                k, v = token.split("=", 1)
                kv_pairs[k.strip().lower()] = v.strip()

        if "user" not in kv_pairs or not kv_pairs["user"]:
            dropped_reasons["sin_user"] += 1
            continue

        customer_id = _parse_positive_int(kv_pairs["user"])
        if customer_id is None:
            dropped_reasons["user_no_numerico"] += 1
            continue

        if customer_id not in valid_customer_ids:
            dropped_reasons["user_inexistente_o_test"] += 1
            continue

        if "action" not in kv_pairs or not kv_pairs["action"]:
            dropped_reasons["action_vacio"] += 1
            continue

        action = kv_pairs["action"].strip().lower()
        if not action:
            dropped_reasons["action_vacio"] += 1
            continue

        clean_rows.append(
            {
                "nivel": level,
                "id_cliente": customer_id,
                "action": action,
            }
        )

    with output_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=LOGS_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(clean_rows)

    return {
        "input_path": str(logs_path),
        "output_path": str(output_path),
        "customers_source": customers_source,
        "raw_lines": len(raw_lines),
        "clean_rows_written": len(clean_rows),
        "dropped_total": sum(dropped_reasons.values()),
        "dropped_reasons": dict(dropped_reasons),
    }


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
    """Ejecuta el pipeline completo de transformación de la capa Silver (Issues #3 y #4)."""
    ensure_output_dirs()

    print("=" * 68)
    print("SILVER LAYER - PIPELINE DE LIMPIEZA (Issues #3 y #4)")
    print("=" * 68)

    # 1. Clientes primero: define la dimensión de entidades válidas.
    customers_summary = clean_customers()
    print("\n[1/3] LIMPIEZA DE CLIENTES (Issue #4)")
    print(f"  Origen             : {customers_summary['input_path']}")
    print(f"  Salida generada    : {customers_summary['output_path']}")
    print(
        f"  Registros leídos   : {customers_summary['records_read']} "
        f"(en blanco ignoradas: {customers_summary['blank_lines_skipped']})"
    )
    print(
        f"  Descartados        : {customers_summary['dropped_total']} "
        f"{customers_summary['dropped_reasons']}"
    )
    print(f"  Escritos (limpios) : {customers_summary['clean_rows_written']}")

    # 2. Cargar IDs válidos directamente desde el nuevo clean_customers.csv.
    valid_customer_ids, cust_source = load_valid_customer_ids()

    # 3. Logs: limpia eventos y valida contra el conjunto de clientes limpios.
    logs_summary = clean_logs(valid_customer_ids=valid_customer_ids)
    print("\n[2/3] LIMPIEZA DE LOGS (Issue #4)")
    print(f"  Origen             : {logs_summary['input_path']}")
    print(f"  Fuente clientes    : {logs_summary['customers_source']}")
    print(f"  Salida generada    : {logs_summary['output_path']}")
    print(f"  Líneas procesadas  : {logs_summary['raw_lines']}")
    print(
        f"  Descartados        : {logs_summary['dropped_total']} "
        f"{logs_summary['dropped_reasons']}"
    )
    print(f"  Escritos (limpios) : {logs_summary['clean_rows_written']}")

    # 4. Ventas: limpia transacciones y valida contra el conjunto de clientes limpios.
    sales_summary = clean_sales(valid_customer_ids=valid_customer_ids)
    print("\n[3/3] LIMPIEZA DE VENTAS (Issue #3)")
    print(f"  Origen             : {sales_summary['input_path']}")
    print(f"  Fuente clientes    : {sales_summary['customers_source']}")
    print(f"  Salida generada    : {sales_summary['output_path']}")
    print(
        f"  Líneas crudas      : {sales_summary['raw_lines']} "
        f"(en blanco ignoradas: {sales_summary['blank_lines_skipped']})"
    )
    print(f"  Filas leídas       : {sales_summary['data_rows_read']}")
    print(
        f"  Descartados        : {sales_summary['dropped_total']} "
        f"{sales_summary['dropped_reasons']}"
    )
    print(f"  Escritos (limpios) : {sales_summary['clean_rows_written']}")
    print("\n" + "=" * 68)
    print("PIPELINE SILVER COMPLETADO CON ÉXITO")
    print("=" * 68)


if __name__ == "__main__":
    main()
