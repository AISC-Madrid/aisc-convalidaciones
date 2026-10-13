"""Descarga las fichas HTML que usan los tests (no se suben al repo: contienen temarios).

Ejecutar desde la raíz del repositorio:

    python tests/fixtures/uc3m/descargar.py
"""

import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.scrapers.uc3m_client import PAUSA_SEGUNDOS, USER_AGENT, url_ficha  # noqa: E402

DESTINO = Path(__file__).resolve().parent

# (est, plan, asig, anio, idioma)
FICHAS = [
    (371, 456, 15363, 2026, "ES"),
    (371, 456, 15363, 2026, "EN"),
    (371, 456, 15363, 2024, "ES"),
    (218, 489, 13881, 2026, "ES"),
    (218, 489, 13881, 2026, "EN"),
    (351, 486, 17631, 2026, "ES"),
    (351, 486, 17631, 2026, "EN"),
    (371, 456, 11692, 2026, "ES"),
    (371, 456, 11692, 2026, "EN"),
    (206, 557, 13565, 2026, "ES"),
    (206, 557, 13565, 2026, "EN"),
]


def main() -> None:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    for est, plan, asig, anio, idioma in FICHAS:
        ruta = DESTINO / f"{asig}_{anio}_{idioma}.html"
        if ruta.exists() and ruta.stat().st_size:
            print(f"ya está: {ruta.name}")
            continue
        time.sleep(PAUSA_SEGUNDOS)
        respuesta = session.get(url_ficha(est, plan, asig, anio, idioma), timeout=30)
        respuesta.raise_for_status()
        ruta.write_bytes(respuesta.content)
        print(f"descargada: {ruta.name} ({len(respuesta.content)} bytes)")


if __name__ == "__main__":
    main()
