"""Análisis exploratorio de la capa Bronze (Parte 1 - Mini Lakehouse).

Inspecciona de forma automática los tres ficheros crudos de ``data_lab/bronze/``
(``ventas.csv``, ``clientes.json`` y ``logs.txt``), identifica su formato y
estructura, y cuantifica todos los errores, omisiones y anomalías de integridad
referencial entre fuentes.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# Intentamos reutilizar BRONZE_DIR desde src/common.py (Issue #2).
# Si aún no existe en la rama actual, resolvemos la ruta relativa al proyecto
# para que el script pueda ejecutarse de forma autónoma desde la raíz o src/.
try:
    from common import BRONZE_DIR
except ImportError:
    try:
        from src.common import BRONZE_DIR
    except ImportError:
        BRONZE_DIR = Path(__file__).resolve().parent.parent / "data_lab" / "bronze"

# Umbral heurístico para detectar importes atípicos frente al rango normal (20-300).
OUTLIER_AMOUNT_THRESHOLD = 1000.0
# Valores usados en los datos para indicar país inválido o cuentas no productivas.
INVALID_COUNTRY_MARKERS = {"??"}
TEST_DEBUG_NAMES = {"testuser", "debug"}
LOG_LINE_PATTERN = re.compile(r"^\[(?P<level>[A-Z]+)\]\s*(?P<body>.*)$")


def parse_int(value: Any) -> int | None:
    """Convierte un valor a entero estricto; devuelve None si está vacío o no es entero."""
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def parse_float(value: Any) -> float | None:
    """Convierte un valor a float; devuelve None si está vacío o no es numérico."""
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def analyze_customers(path: Path) -> dict[str, Any]:
    """Analiza ``clientes.json`` y devuelve métricas, anomalías e IDs conocidos."""
    raw_text = path.read_text(encoding="utf-8")
    raw_lines = raw_text.splitlines()
    blank_lines = [idx for idx, line in enumerate(raw_lines, start=1) if not line.strip()]

    # clientes.json es un array JSON válido (aunque con líneas en blanco intercaladas).
    records = json.loads(raw_text)

    non_int_ids: list[dict[str, Any]] = []
    empty_names: list[dict[str, Any]] = []
    invalid_countries: list[dict[str, Any]] = []
    test_debug_accounts: list[dict[str, Any]] = []
    generic_user_names = 0
    seen_ids: Counter[int] = Counter()
    names_to_ids: defaultdict[str, list[int]] = defaultdict(list)
    countries_dist: Counter[str] = Counter()
    all_keys: set[str] = set()

    for idx, record in enumerate(records, start=1):
        all_keys.update(record.keys())
        raw_id = record.get("id_cliente")
        parsed_id = parse_int(raw_id)

        # Detectamos si el ID viene serializado como cadena en vez de entero JSON.
        if not isinstance(raw_id, int) or isinstance(raw_id, bool):
            non_int_ids.append({"pos": idx, "record": record, "tipo": type(raw_id).__name__})

        if parsed_id is not None:
            seen_ids[parsed_id] += 1

        # Validamos presencia de nombre y si corresponde a cuentas de test/debug o genéricas.
        raw_name = record.get("nombre")
        clean_name = str(raw_name).strip() if raw_name is not None else ""
        if not clean_name:
            empty_names.append(record)
        else:
            if parsed_id is not None:
                names_to_ids[clean_name].append(parsed_id)
            if clean_name.lower() in TEST_DEBUG_NAMES:
                test_debug_accounts.append(record)
            if re.fullmatch(r"user\d+", clean_name, flags=re.IGNORECASE):
                generic_user_names += 1

        # Detectamos tanto valores nulos/vacíos como marcadores artificiales ("??").
        raw_country = record.get("pais")
        clean_country = str(raw_country).strip() if raw_country is not None else ""
        countries_dist[clean_country if clean_country else "<NULL/VACIO>"] += 1
        if not clean_country or clean_country in INVALID_COUNTRY_MARKERS:
            invalid_countries.append(record)

    duplicate_ids = {cid: count for cid, count in seen_ids.items() if count > 1}
    duplicate_names = {name: ids for name, ids in names_to_ids.items() if len(ids) > 1}
    test_debug_ids = {
        parse_int(rec["id_cliente"])
        for rec in test_debug_accounts
        if parse_int(rec.get("id_cliente")) is not None
    }

    return {
        "file_type": "JSON (array semiestructurado)",
        "size_bytes": path.stat().st_size,
        "total_lines": len(raw_lines),
        "blank_lines_count": len(blank_lines),
        "blank_lines": blank_lines,
        "fields": sorted(all_keys),
        "total_records": len(records),
        "valid_ids": set(seen_ids.keys()),
        "test_debug_ids": test_debug_ids,
        "non_int_ids": non_int_ids,
        "duplicate_ids": duplicate_ids,
        "empty_names": empty_names,
        "invalid_countries": invalid_countries,
        "test_debug_accounts": test_debug_accounts,
        "generic_user_names": generic_user_names,
        "duplicate_names": duplicate_names,
        "countries_dist": dict(countries_dist),
    }


def analyze_sales(
    path: Path,
    known_customer_ids: set[int],
    test_debug_ids: set[int],
) -> dict[str, Any]:
    """Analiza ``ventas.csv`` y cruza ``id_cliente`` con los IDs de ``clientes.json``."""
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    blank_lines = [idx for idx, line in enumerate(raw_lines, start=1) if not line.strip()]

    # Leemos fila a fila conservando el número de línea original del archivo
    # para poder localizar cada registro defectuoso con exactitud en el informe.
    header: list[str] = []
    data_rows = 0
    malformed_rows: list[tuple[int, list[str]]] = []
    seen_order_ids: Counter[int] = Counter()
    bad_order_ids: list[tuple[int, dict[str, str]]] = []
    missing_customer_ids: list[tuple[int, dict[str, str]]] = []
    non_int_customer_ids: list[tuple[int, dict[str, str]]] = []
    orphan_customer_ids: list[tuple[int, dict[str, str]]] = []
    non_numeric_amounts: list[tuple[int, dict[str, str]]] = []
    negative_amounts: list[tuple[int, dict[str, str]]] = []
    zero_amounts: list[tuple[int, dict[str, str]]] = []
    outlier_amounts: list[tuple[int, dict[str, str]]] = []
    test_product_rows: list[tuple[int, dict[str, str]]] = []
    test_debug_customer_sales: list[tuple[int, dict[str, str]]] = []
    products_dist: Counter[str] = Counter()
    repeated_content: defaultdict[tuple[str, str, str], list[int]] = defaultdict(list)

    for line_no, raw_line in enumerate(raw_lines, start=1):
        if not raw_line.strip():
            continue

        parsed = next(csv.reader([raw_line]))
        if not header:
            header = parsed
            continue

        data_rows += 1
        if len(parsed) != len(header):
            malformed_rows.append((line_no, parsed))
            continue

        row = dict(zip(header, parsed))
        products_dist[row["producto"].strip()] += 1
        repeated_content[
            (row["id_cliente"].strip(), row["producto"].strip(), row["importe"].strip())
        ].append(parse_int(row["id_pedido"]) or -1)

        order_id = parse_int(row["id_pedido"])
        if order_id is None:
            bad_order_ids.append((line_no, row))
        else:
            seen_order_ids[order_id] += 1

        # Evaluamos la validez sintáctica y referencial de id_cliente.
        raw_cid = row["id_cliente"].strip()
        cid = parse_int(raw_cid)
        if not raw_cid:
            missing_customer_ids.append((line_no, row))
        elif cid is None:
            non_int_customer_ids.append((line_no, row))
        else:
            if cid not in known_customer_ids:
                orphan_customer_ids.append((line_no, row))
            if cid in test_debug_ids:
                test_debug_customer_sales.append((line_no, row))

        # Evaluamos el importe: tipo numérico, signo, cero y posibles outliers.
        amount = parse_float(row["importe"])
        if amount is None:
            non_numeric_amounts.append((line_no, row))
        elif amount < 0:
            negative_amounts.append((line_no, row))
        elif amount == 0:
            zero_amounts.append((line_no, row))
        elif amount > OUTLIER_AMOUNT_THRESHOLD:
            outlier_amounts.append((line_no, row))

        if row["producto"].strip().lower() == "test":
            test_product_rows.append((line_no, row))

    duplicate_order_ids = {oid: cnt for oid, cnt in seen_order_ids.items() if cnt > 1}
    repeated_orders = {k: v for k, v in repeated_content.items() if len(v) > 1}

    return {
        "file_type": "CSV (tabular delimitado por comas)",
        "size_bytes": path.stat().st_size,
        "total_lines": len(raw_lines),
        "blank_lines_count": len(blank_lines),
        "blank_lines": blank_lines,
        "header": header,
        "data_rows": data_rows,
        "malformed_rows": malformed_rows,
        "bad_order_ids": bad_order_ids,
        "duplicate_order_ids": duplicate_order_ids,
        "missing_customer_ids": missing_customer_ids,
        "non_int_customer_ids": non_int_customer_ids,
        "orphan_customer_ids": orphan_customer_ids,
        "non_numeric_amounts": non_numeric_amounts,
        "negative_amounts": negative_amounts,
        "zero_amounts": zero_amounts,
        "outlier_amounts": outlier_amounts,
        "test_product_rows": test_product_rows,
        "test_debug_customer_sales": test_debug_customer_sales,
        "products_dist": dict(products_dist),
        "repeated_orders": repeated_orders,
    }


def analyze_logs(
    path: Path,
    known_customer_ids: set[int],
) -> dict[str, Any]:
    """Analiza ``logs.txt`` identificando niveles, campos faltantes e IDs inválidos."""
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    blank_lines: list[int] = []
    levels_dist: Counter[str] = Counter()
    actions_dist: Counter[str] = Counter()
    malformed_lines: list[tuple[int, str]] = []
    missing_user_field: list[tuple[int, str]] = []
    non_int_users: list[tuple[int, str, str]] = []
    orphan_users: list[tuple[int, str, int]] = []
    empty_actions: list[tuple[int, str]] = []
    error_lines: list[tuple[int, str]] = []
    warn_lines: list[tuple[int, str]] = []
    debug_lines: list[tuple[int, str]] = []
    valid_customers_with_error: set[int] = set()

    for line_no, raw_line in enumerate(raw_lines, start=1):
        stripped = raw_line.strip()
        if not stripped:
            blank_lines.append(line_no)
            continue

        match = LOG_LINE_PATTERN.match(stripped)
        if not match:
            malformed_lines.append((line_no, stripped))
            continue

        level = match.group("level")
        body = match.group("body")
        levels_dist[level] += 1

        if level == "ERROR":
            error_lines.append((line_no, stripped))
        elif level == "WARN":
            warn_lines.append((line_no, stripped))
        elif level == "DEBUG":
            debug_lines.append((line_no, stripped))

        # Parseamos pares clave=valor del cuerpo del log.
        kv_pairs: dict[str, str] = {}
        for token in body.split():
            if "=" in token:
                key, val = token.split("=", 1)
                kv_pairs[key] = val

        # Validamos presencia y tipo de user=.
        if "user" not in kv_pairs:
            missing_user_field.append((line_no, stripped))
        else:
            raw_user = kv_pairs["user"].strip()
            uid = parse_int(raw_user)
            if uid is None:
                non_int_users.append((line_no, stripped, raw_user))
            elif uid not in known_customer_ids:
                orphan_users.append((line_no, stripped, uid))
            elif level == "ERROR":
                valid_customers_with_error.add(uid)

        # Validamos presencia y contenido de action=.
        action_val = kv_pairs.get("action", "").strip()
        if "action" not in kv_pairs or not action_val:
            empty_actions.append((line_no, stripped))
        else:
            actions_dist[action_val] += 1

    return {
        "file_type": "TXT (log de eventos clave=valor semiestructurado)",
        "size_bytes": path.stat().st_size,
        "total_lines": len(raw_lines),
        "non_empty_lines": len(raw_lines) - len(blank_lines),
        "blank_lines_count": len(blank_lines),
        "blank_lines": blank_lines,
        "levels_dist": dict(levels_dist),
        "actions_dist": dict(actions_dist),
        "malformed_lines": malformed_lines,
        "missing_user_field": missing_user_field,
        "non_int_users": non_int_users,
        "orphan_users": orphan_users,
        "empty_actions": empty_actions,
        "error_lines_count": len(error_lines),
        "warn_lines_count": len(warn_lines),
        "debug_lines": debug_lines,
        "valid_customers_with_error": sorted(valid_customers_with_error),
    }


def print_report(
    customers_res: dict[str, Any],
    sales_res: dict[str, Any],
    logs_res: dict[str, Any],
) -> None:
    """Imprime en consola un resumen estructurado de los hallazgos de Bronze."""
    print("=" * 72)
    print("BRONZE LAYER ANALYSIS - MINI LAKEHOUSE (Activity 3)")
    print("=" * 72)
    print(f"Directorio Bronze: {BRONZE_DIR}")
    print(
        "Nota nombres PDF vs ZIP: sales.csv -> ventas.csv | "
        "customers.json -> clientes.json | logs.txt -> logs.txt"
    )

    print("\n--- 1. ventas.csv ---")
    print(f"Tipo: {sales_res['file_type']} | Tamaño: {sales_res['size_bytes']} bytes")
    print(f"Columnas: {sales_res['header']}")
    print(
        f"Líneas totales: {sales_res['total_lines']} | Registros de datos: {sales_res['data_rows']} | "
        f"Líneas en blanco: {sales_res['blank_lines_count']} (líneas {sales_res['blank_lines']})"
    )
    print(f"Distribución de productos: {sales_res['products_dist']}")
    print(f"  - filas malformadas (columnas != 4): {sales_res['malformed_rows']}")
    print(f"  - id_pedido inválido o duplicado: {sales_res['bad_order_ids']} | {sales_res['duplicate_order_ids']}")
    print(f"  - id_cliente vacío: {sales_res['missing_customer_ids']}")
    print(f"  - id_cliente no entero: {sales_res['non_int_customer_ids']}")
    print(f"  - id_cliente huérfano (no existe en clientes.json): {sales_res['orphan_customer_ids']}")
    print(f"  - importe no numérico: {sales_res['non_numeric_amounts']}")
    print(f"  - importe negativo: {sales_res['negative_amounts']}")
    print(f"  - importe == 0: {sales_res['zero_amounts']}")
    print(f"  - importe outlier (> {OUTLIER_AMOUNT_THRESHOLD}): {sales_res['outlier_amounts']}")
    print(f"  - producto 'test': {sales_res['test_product_rows']}")
    print(f"  - ventas de cuentas TestUser/Debug: {sales_res['test_debug_customer_sales']}")
    print(f"  - pedidos con contenido repetido (distinto id_pedido): {sales_res['repeated_orders']}")

    print("\n--- 2. clientes.json ---")
    print(f"Tipo: {customers_res['file_type']} | Tamaño: {customers_res['size_bytes']} bytes")
    print(f"Campos: {customers_res['fields']}")
    print(
        f"Líneas totales: {customers_res['total_lines']} | Registros: {customers_res['total_records']} | "
        f"Líneas en blanco intercaladas: {customers_res['blank_lines_count']}"
    )
    print(f"Distribución de países: {customers_res['countries_dist']}")
    print(f"  - id_cliente no int (string): {customers_res['non_int_ids']}")
    print(f"  - id_cliente duplicados: {customers_res['duplicate_ids']}")
    print(f"  - nombre vacío/null: {customers_res['empty_names']}")
    print(f"  - país null/vacío/'??': {customers_res['invalid_countries']}")
    print(f"  - cuentas TestUser/Debug: {customers_res['test_debug_accounts']}")
    print(f"  - nombres duplicados entre distintos IDs: {customers_res['duplicate_names']}")
    print(f"  - nombres genéricos (userN): {customers_res['generic_user_names']}")

    print("\n--- 3. logs.txt ---")
    print(f"Tipo: {logs_res['file_type']} | Tamaño: {logs_res['size_bytes']} bytes")
    print(
        f"Líneas totales: {logs_res['total_lines']} | Eventos: {logs_res['non_empty_lines']} | "
        f"Líneas en blanco: {logs_res['blank_lines_count']} (líneas {logs_res['blank_lines']})"
    )
    print(f"Niveles: {logs_res['levels_dist']} | Acciones válidas: {logs_res['actions_dist']}")
    print(f"  - líneas [ERROR]: {logs_res['error_lines_count']}")
    print(f"  - líneas [WARN]: {logs_res['warn_lines_count']}")
    print(f"  - líneas [DEBUG]: {logs_res['debug_lines']}")
    print(f"  - líneas malformadas (sin etiqueta [NIVEL]): {logs_res['malformed_lines']}")
    print(f"  - líneas sin campo user=: {logs_res['missing_user_field']}")
    print(f"  - líneas con user no numérico: {logs_res['non_int_users']}")
    print(f"  - líneas con user huérfano (no en clientes.json): {logs_res['orphan_users']}")
    print(f"  - líneas con action= vacío: {logs_res['empty_actions']}")
    print(
        f"  - clientes válidos con algún [ERROR] en logs "
        f"({len(logs_res['valid_customers_with_error'])}): {logs_res['valid_customers_with_error']}"
    )

    print("\n--- 4. SÍNTESIS AUTOMÁTICA PARA RESPONDER AL PDF ---")
    invalid_sales_total = (
        len(sales_res["missing_customer_ids"])
        + len(sales_res["non_int_customer_ids"])
        + len(sales_res["orphan_customer_ids"])
        + len(sales_res["non_numeric_amounts"])
        + len(sales_res["negative_amounts"])
        + len(sales_res["zero_amounts"])
        + len(sales_res["outlier_amounts"])
    )
    print(f"  * Registros de ventas con anomalías directas detectadas: {invalid_sales_total}")
    print(
        f"  * Clientes con campos faltantes/inválidos: "
        f"nombre vacío={len(customers_res['empty_names'])}, "
        f"país null/??={len(customers_res['invalid_countries'])}, "
        f"id no entero={len(customers_res['non_int_ids'])}"
    )
    print(
        f"  * Logs no fiables o incompletos: "
        f"ERROR={logs_res['error_lines_count']}, WARN={logs_res['warn_lines_count']}, "
        f"DEBUG={len(logs_res['debug_lines'])}, sin user={len(logs_res['missing_user_field'])}, "
        f"user no int={len(logs_res['non_int_users'])}, user huérfano={len(logs_res['orphan_users'])}, "
        f"action vacía={len(logs_res['empty_actions'])}"
    )


def main() -> None:
    """Ejecuta el análisis completo de la capa Bronze sobre los tres ficheros fuente."""
    customers_path = BRONZE_DIR / "clientes.json"
    sales_path = BRONZE_DIR / "ventas.csv"
    logs_path = BRONZE_DIR / "logs.txt"

    customers_res = analyze_customers(customers_path)
    sales_res = analyze_sales(
        sales_path,
        known_customer_ids=customers_res["valid_ids"],
        test_debug_ids=customers_res["test_debug_ids"],
    )
    logs_res = analyze_logs(
        logs_path,
        known_customer_ids=customers_res["valid_ids"],
    )
    print_report(customers_res, sales_res, logs_res)


if __name__ == "__main__":
    main()
