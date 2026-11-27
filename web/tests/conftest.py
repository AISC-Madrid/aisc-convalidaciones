"""Utilidades comunes de los tests de la web.

La web solo lee resultados de la MySQL del servidor. En los tests no hay MySQL: el fixture
``publicar`` sustituye las dos funciones de ``bd_resultados`` que usa la pantalla para que
devuelvan las combinaciones que diga cada test.
"""

import copy
import json
import sys
from pathlib import Path

import pytest

WEB_DIR = Path(__file__).resolve().parents[1]
RAIZ = WEB_DIR.parent
sys.path.insert(0, str(WEB_DIR))
import bd_resultados  # noqa: E402

EJEMPLO = RAIZ / "tests" / "fixtures" / "resultados" / "ejemplo.json"


def ejemplo():
    """Los resultados pequeños del contrato (5 propuestas, un grupo n:m)."""
    return json.loads(EJEMPLO.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def sin_mysql_real(monkeypatch):
    """Ningún test de la web se conecta a la MySQL, aunque haya variables MYSQL_* puestas."""
    for variable in ("MYSQL_HOST", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD"):
        monkeypatch.delenv(variable, raising=False)


@pytest.fixture
def publicar(monkeypatch):
    """``publicar(datos, ...)`` deja esas combinaciones como si estuvieran en la MySQL."""

    def _publicar(*conjuntos):
        por_clave = {(d["grado"], d["universidad"]): d for d in conjuntos}

        def combinaciones():
            return [{"grado": g, "universidad": u} for g, u in sorted(por_clave)]

        def cargar(grado, universidad):
            if (grado, universidad) not in por_clave:
                raise bd_resultados.SinResultados(
                    f"No hay resultados para {grado} · {universidad}."
                )
            return copy.deepcopy(por_clave[(grado, universidad)])

        monkeypatch.setattr(bd_resultados, "combinaciones", combinaciones)
        monkeypatch.setattr(bd_resultados, "cargar", cargar)

    return _publicar
