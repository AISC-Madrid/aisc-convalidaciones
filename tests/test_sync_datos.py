import json
import shutil
import sqlite3
import zipfile
from contextlib import closing
from pathlib import Path

import pytest

from src.scrapers.uc3m import create_database
from src.sync.datos import (
    MANIFIESTO,
    PAQUETES,
    REPO_DATOS,
    descargar,
    empaquetar,
    extraer,
    publicar,
)


class GhFalso:
    """Simula ``gh release create/download`` guardando los assets en una carpeta."""

    def __init__(self, almacen: Path):
        self.almacen = almacen
        self.llamadas: list[list[str]] = []

    def __call__(self, args: list[str]) -> None:
        self.llamadas.append(args)
        assert args[args.index("--repo") + 1] == REPO_DATOS
        if args[:2] == ["release", "create"]:
            destino = self.almacen / args[2]
            destino.mkdir(parents=True)
            for asset in args[args.index("--notes") + 2:]:
                shutil.copy(asset, destino)
        elif args[:2] == ["release", "download"]:
            tag = args[2] if not args[2].startswith("--") else sorted(
                p.name for p in self.almacen.iterdir())[-1]
            dir_ = Path(args[args.index("--dir") + 1])
            patrones = [args[i + 1] for i, a in enumerate(args) if a == "--pattern"]
            for patron in patrones:
                shutil.copy(self.almacen / tag / patron, dir_)


def _repo_con_datos(raiz: Path) -> Path:
    bd = create_database(raiz / "data" / "processed" / "uc3m.sqlite")
    with closing(sqlite3.connect(bd)) as connection, connection:
        connection.execute(
            "INSERT INTO subjects (codigo, curso_academico, idioma, nombre) "
            "VALUES ('15363', '2026/2027', 'ES', 'Álgebra Lineal')")
        connection.execute(
            "INSERT INTO descargas VALUES ('2026/2027', '456', 'ES+EN', 'completo', 'hoy')")
    cache = raiz / "data" / "raw" / "uc3m" / "2026"
    cache.mkdir(parents=True)
    (cache / "15363_ES.html").write_text("<html>ficha</html>", "utf-8")
    fixtures = raiz / "tests" / "fixtures" / "uc3m"
    fixtures.mkdir(parents=True)
    (fixtures / "15363_2026_ES.html").write_text("<html>fixture</html>", "utf-8")
    (fixtures / "README.md").write_text("no va en el zip", "utf-8")
    return raiz


def test_publicar_y_descargar_ida_y_vuelta(tmp_path):
    origen = _repo_con_datos(tmp_path / "origen")
    gh = GhFalso(tmp_path / "releases")

    manifiesto = publicar("uc3m-prueba", raiz=origen, ejecutar=gh)

    assert set(manifiesto["paquetes"]) == set(PAQUETES)
    assert manifiesto["bd"]["fichas_por_curso"] == {"2026/2027": 1}
    assert manifiesto["bd"]["descargas_por_estado"] == {"completo": 1}

    destino = tmp_path / "destino"
    destino.mkdir()
    extraidos = descargar(paquetes=list(PAQUETES), raiz=destino, ejecutar=gh)

    relativos = {p.relative_to(destino.resolve()).as_posix() for p in extraidos}
    assert relativos == {
        "data/processed/uc3m.sqlite",
        "data/raw/uc3m/2026/15363_ES.html",
        "tests/fixtures/uc3m/15363_2026_ES.html",
    }
    with closing(sqlite3.connect(destino / "data/processed/uc3m.sqlite")) as connection:
        assert connection.execute("SELECT nombre FROM subjects").fetchone() == ("Álgebra Lineal",)


def test_descargar_por_defecto_solo_baja_la_bd_del_ultimo_release(tmp_path):
    origen = _repo_con_datos(tmp_path / "origen")
    gh = GhFalso(tmp_path / "releases")
    publicar("uc3m-prueba", raiz=origen, ejecutar=gh)
    destino = tmp_path / "destino"

    extraidos = descargar(raiz=destino, ejecutar=gh)

    assert [p.name for p in extraidos] == ["uc3m.sqlite"]
    descarga = gh.llamadas[-1]
    assert descarga[:3] == ["release", "download", "--repo"]
    assert "uc3m_cache_html.zip" not in descarga


def test_descargar_no_pisa_la_bd_local_sin_forzar(tmp_path):
    origen = _repo_con_datos(tmp_path / "origen")
    gh = GhFalso(tmp_path / "releases")
    publicar("uc3m-prueba", raiz=origen, ejecutar=gh)

    with pytest.raises(FileExistsError):
        descargar(raiz=origen, ejecutar=gh)
    assert descargar(raiz=origen, forzar=True, ejecutar=gh)


def test_descargar_detecta_un_zip_corrupto(tmp_path):
    origen = _repo_con_datos(tmp_path / "origen")
    gh = GhFalso(tmp_path / "releases")
    publicar("uc3m-prueba", raiz=origen, ejecutar=gh)
    (tmp_path / "releases" / "uc3m-prueba" / "uc3m_sqlite.zip").write_bytes(b"roto")

    with pytest.raises(ValueError, match="SHA-256"):
        descargar(raiz=tmp_path / "destino", ejecutar=gh)


def test_publicar_salta_paquetes_vacios(tmp_path):
    raiz = tmp_path / "repo"
    create_database(raiz / "data" / "processed" / "uc3m.sqlite")
    gh = GhFalso(tmp_path / "releases")

    manifiesto = publicar("solo-bd", raiz=raiz, ejecutar=gh)

    assert set(manifiesto["paquetes"]) == {"bd"}
    subido = json.loads((tmp_path / "releases" / "solo-bd" / MANIFIESTO).read_text("utf-8"))
    assert subido == manifiesto


def test_empaquetar_fixtures_solo_incluye_html(tmp_path):
    raiz = _repo_con_datos(tmp_path)

    zip_path = empaquetar(PAQUETES["fixtures"], raiz, tmp_path)

    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == ["tests/fixtures/uc3m/15363_2026_ES.html"]


def test_extraer_rechaza_rutas_fuera_del_repo(tmp_path):
    zip_path = tmp_path / "malo.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../fuera.txt", "x")

    with pytest.raises(ValueError, match="fuera del repo"):
        extraer(zip_path, tmp_path / "repo")
