import json
from pathlib import Path

import pytest

from src.scrapers.uc3m_client import (
    AsignaturaPlan,
    ClienteUC3M,
    ErrorAPIUC3M,
    FichaInesperada,
    Plan,
    clasificar_ficha,
    url_ficha,
)

FIXTURES = Path(__file__).parent / "fixtures" / "uc3m"
SINTETICAS = FIXTURES / "sinteticas"
SIN_FICHA = (FIXTURES / "respuestas" / "sin_ficha.html").read_bytes()
FICHA = (
    '<html><body><div class="asignatura">Álgebra Lineal</div>'
    '<div class="asignatura">(15363)</div></body></html>'
).encode()


class RespuestaFalsa:
    def __init__(self, status_code: int = 200, content: bytes = b"") -> None:
        self.status_code = status_code
        self.content = content

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class SesionFalsa:
    """Devuelve en orden las respuestas configuradas y guarda las llamadas."""

    def __init__(self, respuestas: list[RespuestaFalsa]) -> None:
        self.respuestas = list(respuestas)
        self.llamadas: list[tuple[str, str, dict]] = []

    def _siguiente(self, metodo: str, url: str, kwargs: dict) -> RespuestaFalsa:
        self.llamadas.append((metodo, url, kwargs))
        return self.respuestas.pop(0)

    def post(self, url, **kwargs):
        return self._siguiente("POST", url, kwargs)

    def get(self, url, **kwargs):
        return self._siguiente("GET", url, kwargs)


def _json_fixture(nombre: str) -> RespuestaFalsa:
    return RespuestaFalsa(content=(FIXTURES / nombre).read_bytes())


def _cliente(tmp_path, respuestas) -> tuple[ClienteUC3M, SesionFalsa]:
    sesion = SesionFalsa(respuestas)
    return ClienteUC3M(cache_dir=tmp_path, pausa=0, session=sesion), sesion


def test_listar_planes_filtra_grados_activos(tmp_path):
    cliente, sesion = _cliente(tmp_path, [_json_fixture("findPlanes.json")])

    planes = cliente.listar_planes()

    assert [p.codigo for p in planes] == [456, 178, 580]
    assert all(p.es_grado and p.activo for p in planes)
    assert planes[0] == Plan(
        codigo=456,
        nombre=planes[0].nombre,
        estudio=371,
        es_grado=True,
        activo=True,
    )
    assert sesion.llamadas[0][1].endswith("/findPlanes.ajax")
    assert cliente.peticiones == 1


def test_listar_planes_sin_filtro_devuelve_todos(tmp_path):
    cliente, _ = _cliente(tmp_path, [_json_fixture("findPlanes.json")])

    planes = {p.codigo: p for p in cliente.listar_planes(solo_grados_activos=False)}

    assert len(planes) == 6
    assert planes[523].es_grado is False and planes[523].activo is True  # Máster
    assert planes[577].es_grado is True and planes[577].activo is False  # inactivo 'B'


def test_listar_planes_tolera_tipo_estudio_nulo(tmp_path):
    cuerpo = {
        "ok": "S",
        "datos": [
            {
                "codigo": 1,
                "nombre": "X",
                "activado": "A",
                "baja": False,
                "tipoEstudio": None,
                "estudio": {"codigo": 9},
            }
        ],
    }
    cliente, _ = _cliente(tmp_path, [RespuestaFalsa(content=json.dumps(cuerpo).encode())])

    planes = cliente.listar_planes(solo_grados_activos=False)

    assert planes == [Plan(codigo=1, nombre="X", estudio=9, es_grado=False, activo=True)]


def test_listar_asignaturas_parsea_fixture(tmp_path):
    cliente, sesion = _cliente(tmp_path, [_json_fixture("findAsignaturas_456_2026.json")])

    asignaturas = cliente.listar_asignaturas(456, 2026)

    assert len(asignaturas) == 5
    assert all(isinstance(a, AsignaturaPlan) for a in asignaturas)
    assert all(a.plan == 456 and a.estudio == 371 for a in asignaturas)
    algebra = next(a for a in asignaturas if a.codigo == 15363)
    assert algebra.nombre == "Álgebra Lineal"
    assert algebra.nombre_en is None  # denominacionEng vacío
    assert sesion.llamadas[0][2]["data"] == {"codPlan": 456, "ano": 2026}


def test_listar_anos(tmp_path):
    cuerpo = json.dumps({"ok": "S", "datos": [2026, 2025, 2024]}).encode()
    cliente, _ = _cliente(tmp_path, [RespuestaFalsa(content=cuerpo)])

    assert cliente.listar_anos() == [2026, 2025, 2024]


def test_url_ficha():
    esperado = (
        "https://aplicaciones.uc3m.es/cpa/generaFicha"
        "?est=371&plan=456&asig=15363&anio=2025&idioma=2"
    )
    assert url_ficha(371, 456, 15363, 2025, "EN") == esperado
    assert url_ficha(371, 456, 15363, 2025, "ES").endswith("&idioma=1")
    assert ClienteUC3M(pausa=0).url_ficha(371, 456, 15363, 2025, "EN") == esperado


def test_url_ficha_idioma_invalido():
    with pytest.raises(ValueError):
        url_ficha(371, 456, 15363, 2025, "FR")


def test_descargar_ficha_usa_cache(tmp_path):
    html = FICHA
    cliente, sesion = _cliente(tmp_path, [RespuestaFalsa(content=html)])

    primero = cliente.descargar_ficha(371, 456, 15363, 2025, "ES")

    ruta = tmp_path / "2025" / "15363_ES.html"
    assert cliente.ruta_cache(15363, 2025, "ES") == ruta
    assert primero == html
    assert ruta.read_bytes() == html
    assert cliente.peticiones == 1
    assert sesion.llamadas[0][0] == "GET"
    assert not ruta.with_name(ruta.name + ".tmp").exists()

    segundo = cliente.descargar_ficha(371, 456, 15363, 2025, "ES")

    assert segundo == html
    assert cliente.peticiones == 1
    assert len(sesion.llamadas) == 1


def test_descargar_ficha_reintenta_tras_500(tmp_path):
    cliente, _ = _cliente(tmp_path, [RespuestaFalsa(500), RespuestaFalsa(content=FICHA)])

    assert cliente.descargar_ficha(371, 456, 15363, 2025, "EN") == FICHA
    assert cliente.peticiones == 2


def test_descargar_ficha_429_duplica_pausa(tmp_path, monkeypatch):
    monkeypatch.setattr("src.scrapers.uc3m_client.time.sleep", lambda _s: None)
    sesion = SesionFalsa([RespuestaFalsa(429), RespuestaFalsa(content=FICHA)])
    cliente = ClienteUC3M(cache_dir=tmp_path, pausa=1.5, session=sesion)

    assert cliente.descargar_ficha(371, 456, 15363, 2025, "ES") == FICHA
    assert cliente.pausa == 3.0


def test_descargar_ficha_agota_reintentos(tmp_path):
    cliente, _ = _cliente(tmp_path, [RespuestaFalsa(503)] * 3)

    with pytest.raises(ErrorAPIUC3M):
        cliente.descargar_ficha(371, 456, 15363, 2025, "ES")
    assert cliente.peticiones == 3
    assert not cliente.ruta_cache(15363, 2025, "ES").exists()


def test_error_api_ok_distinto_de_s(tmp_path):
    cuerpo = json.dumps({"ok": "N", "datos": None}).encode()
    cliente, _ = _cliente(tmp_path, [RespuestaFalsa(content=cuerpo)])

    with pytest.raises(ErrorAPIUC3M):
        cliente.listar_planes()


@pytest.mark.parametrize(
    ("contenido", "esperado"),
    [
        (FICHA, "ficha"),
        ((SINTETICAS / "10001_2026_ES.html").read_bytes(), "ficha"),
        (SIN_FICHA, "sin_ficha"),
        (b"", "inesperada"),
        (FICHA[: len(FICHA) // 2], "inesperada"),
        (b"<html><body><h1>503 Service Unavailable</h1></body></html>", "inesperada"),
        (b"<html><body>Estamos en mantenimiento</body></html>", "inesperada"),
    ],
    ids=["minima", "sintetica", "sin_ficha", "vacia", "cortada", "proxy", "mantenimiento"],
)
def test_clasificar_ficha(contenido, esperado):
    assert clasificar_ficha(contenido) == esperado


def test_la_pagina_sin_ficha_se_guarda_en_cache(tmp_path):
    cliente, sesion = _cliente(tmp_path, [RespuestaFalsa(content=SIN_FICHA)])

    assert cliente.descargar_ficha(371, 456, 13881, 2026, "ES") == SIN_FICHA
    assert cliente.descargar_ficha(371, 456, 13881, 2026, "ES") == SIN_FICHA
    assert len(sesion.llamadas) == 1


def test_una_respuesta_inesperada_lanza_error_y_no_se_guarda(tmp_path):
    error = b"<html><body>Estamos en mantenimiento</body></html>"
    cliente, sesion = _cliente(
        tmp_path, [RespuestaFalsa(content=error), RespuestaFalsa(content=FICHA)]
    )

    with pytest.raises(FichaInesperada):
        cliente.descargar_ficha(371, 456, 15363, 2026, "ES")
    assert not cliente.ruta_cache(15363, 2026, "ES").exists()

    assert cliente.descargar_ficha(371, 456, 15363, 2026, "ES") == FICHA
    assert len(sesion.llamadas) == 2


def test_una_respuesta_inesperada_ya_en_cache_se_vuelve_a_pedir(tmp_path):
    cliente, sesion = _cliente(tmp_path, [RespuestaFalsa(content=FICHA)])
    ruta = cliente.ruta_cache(15363, 2026, "ES")
    ruta.parent.mkdir(parents=True)
    ruta.write_bytes(b"")

    assert cliente.descargar_ficha(371, 456, 15363, 2026, "ES") == FICHA
    assert ruta.read_bytes() == FICHA
    assert len(sesion.llamadas) == 1
