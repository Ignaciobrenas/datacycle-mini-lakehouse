"""Rutas comunes y utilidades de estructura para el Mini Lakehouse.

Centraliza la resolución de directorios de las capas Bronze, Silver y Gold
usando ``pathlib.Path`` para que todos los scripts del equipo (Bronze, Silver y
Gold) funcionen de forma portable independientemente del sistema operativo o
del directorio desde el que se invoque Python.

Ejemplo de uso desde cualquier script en ``src/``::

    from common import BRONZE_DIR, SILVER_DIR, ensure_output_dirs
"""

from __future__ import annotations

from pathlib import Path

# Calculamos la raíz del repositorio subiendo un nivel desde src/common.py.
# Usar __file__ garantiza rutas estables tanto al ejecutar `python src/x.py`
# como `python -m src.x`.
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Directorio raíz de datos y rutas específicas de la arquitectura Medallion.
DATA_DIR: Path = BASE_DIR / "data_lab"
BRONZE_DIR: Path = DATA_DIR / "bronze"
SILVER_DIR: Path = DATA_DIR / "silver"
GOLD_DIR: Path = DATA_DIR / "gold"

# Carpeta de documentación e informes del proyecto.
DOCS_DIR: Path = BASE_DIR / "docs"


def ensure_dir(path: Path) -> Path:
    """Crea un directorio (y sus padres) si aún no existe y devuelve la ruta.

    Se usa para evitar errores al escribir CSVs en ``silver/`` o ``gold/`` en
    entornos recién clonados donde las carpetas de salida están vacías.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_output_dirs() -> tuple[Path, Path]:
    """Asegura que existan los directorios de salida ``SILVER_DIR`` y ``GOLD_DIR``.

    No crea ni modifica ``BRONZE_DIR`` porque los datos crudos deben existir
    previamente y permanecer inmutables.
    """
    return ensure_dir(SILVER_DIR), ensure_dir(GOLD_DIR)


def verify_project_structure() -> dict[str, bool]:
    """Comprueba la existencia de los directorios base del proyecto."""
    return {
        "base": BASE_DIR.is_dir(),
        "bronze": BRONZE_DIR.is_dir(),
        "silver": SILVER_DIR.is_dir(),
        "gold": GOLD_DIR.is_dir(),
    }


def main() -> None:
    """Ejecuta una comprobación rápida de rutas y directorios de salida."""
    ensure_output_dirs()
    status = verify_project_structure()
    print(f"BASE_DIR   : {BASE_DIR} (ok={status['base']})")
    print(f"BRONZE_DIR : {BRONZE_DIR} (ok={status['bronze']})")
    print(f"SILVER_DIR : {SILVER_DIR} (ok={status['silver']})")
    print(f"GOLD_DIR   : {GOLD_DIR} (ok={status['gold']})")


if __name__ == "__main__":
    main()
