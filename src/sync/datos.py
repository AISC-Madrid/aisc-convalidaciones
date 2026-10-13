"""Comparte los datos scrapeados entre el equipo mediante un repo privado de la organización.

Los datos (BD con temarios, caché HTML, fichas de los tests) no pueden ir al repo público. Se
publican como *assets* de un Release de ``AISC-Madrid/aisc-convalidaciones-data`` (privado), que
solo ven los miembros de la organización. Hace falta ``gh`` con sesión iniciada (``gh auth login``).

Ejecutar desde la raíz del repositorio:

    python -m src.sync.datos descargar                    # la BD del último release
    python -m src.sync.datos descargar --todo             # BD + caché HTML + fichas de los tests
    python -m src.sync.datos publicar uc3m-2026-10-12     # sube los datos locales como release
"""

import argparse
import hashlib
import json
import logging
import shutil
import sqlite3
import subprocess
import tempfile
import zipfile
from collections.abc import Callable, Sequence
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_DATOS = "AISC-Madrid/aisc-convalidaciones-data"
RAIZ = Path(__file__).resolve().parents[2]
MANIFIESTO = "manifest.json"


@dataclass(frozen=True)
class Paquete:
    nombre: str
    asset: str
    ruta: str
    patron: str | None = None  # si es carpeta: qué ficheros incluir


PAQUETES = {
    "bd": Paquete("bd", "uc3m_sqlite.zip", "data/processed/uc3m.sqlite"),
    "cache": Paquete("cache", "uc3m_cache_html.zip", "data/raw/uc3m", "**/*"),
    "fixtures": Paquete("fixtures", "fixtures_uc3m_html.zip", "tests/fixtures/uc3m", "*.html"),
}

Ejecutar = Callable[[list[str]], None]


def _gh(args: list[str]) -> None:
    subprocess.run(["gh", *args], check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            digest.update(bloque)
    return digest.hexdigest()


def copia_consistente(origen: Path, destino: Path) -> Path:
    """Copia la BD con ``VACUUM INTO``: no se corrompe aunque otro proceso la tenga abierta."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.unlink(missing_ok=True)
    with closing(sqlite3.connect(origen)) as connection:
        connection.execute("VACUUM INTO ?", (str(destino),))
    return destino


def resumen_bd(path: Path) -> dict:
    with closing(sqlite3.connect(path)) as connection:
        fichas = dict(connection.execute(
            "SELECT curso_academico, COUNT(*) FROM subjects GROUP BY 1 ORDER BY 1"))
        estados = dict(connection.execute("SELECT estado, COUNT(*) FROM descargas GROUP BY 1"))
    return {"fichas_por_curso": fichas, "descargas_por_estado": estados}


def _ficheros(paquete: Paquete, raiz: Path) -> list[Path]:
    base = raiz / paquete.ruta
    if paquete.patron is None:
        return [base] if base.is_file() else []
    return sorted(p for p in base.glob(paquete.patron) if p.is_file())


def empaquetar(paquete: Paquete, raiz: Path, destino: Path) -> Path | None:
    """Crea el zip del paquete con rutas relativas a la raíz del repo. ``None`` si está vacío."""
    ficheros = _ficheros(paquete, raiz)
    if not ficheros:
        return None
    zip_path = destino / paquete.asset
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for fichero in ficheros:
                origen = fichero
                if fichero.suffix == ".sqlite":
                    origen = copia_consistente(fichero, Path(tmp) / fichero.name)
                zf.write(origen, fichero.relative_to(raiz).as_posix())
    return zip_path


def extraer(zip_path: Path, raiz: Path, forzar: bool = False) -> list[Path]:
    """Descomprime en la raíz del repo. No pisa una BD local salvo con ``forzar``."""
    raiz = raiz.resolve()
    extraidos = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            destino = (raiz / info.filename).resolve()
            if not destino.is_relative_to(raiz):
                raise ValueError(f"Ruta fuera del repo en {zip_path.name}: {info.filename}")
            if destino.suffix == ".sqlite" and destino.exists() and not forzar:
                raise FileExistsError(
                    f"{destino.relative_to(raiz)} ya existe; usa --forzar para sustituirla")
            destino.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, destino.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            extraidos.append(destino)
    return extraidos


def publicar(
    tag: str,
    paquetes: Sequence[str] = tuple(PAQUETES),
    raiz: Path = RAIZ,
    notas: str = "",
    ejecutar: Ejecutar = _gh,
) -> dict:
    """Empaqueta los datos locales y crea el release ``tag`` en el repo privado."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        manifiesto: dict = {"tag": tag, "paquetes": {}}
        assets = []
        for nombre in paquetes:
            zip_path = empaquetar(PAQUETES[nombre], raiz, tmp_path)
            if zip_path is None:
                logger.warning("Paquete %s vacío: no se publica", nombre)
                continue
            manifiesto["paquetes"][nombre] = {
                "asset": zip_path.name, "sha256": sha256(zip_path),
                "bytes": zip_path.stat().st_size,
            }
            assets.append(zip_path)
            logger.info("%s: %.1f MB", zip_path.name, zip_path.stat().st_size / 2**20)
        bd = raiz / PAQUETES["bd"].ruta
        if "bd" in manifiesto["paquetes"]:
            manifiesto["bd"] = resumen_bd(bd)
        manifiesto_path = tmp_path / MANIFIESTO
        manifiesto_path.write_text(json.dumps(manifiesto, indent=2, ensure_ascii=False), "utf-8")
        cuerpo = notas or "```json\n" + manifiesto_path.read_text("utf-8") + "\n```"
        ejecutar(["release", "create", tag, "--repo", REPO_DATOS, "--title", tag,
                  "--notes", cuerpo, str(manifiesto_path), *map(str, assets)])
    return manifiesto


def descargar(
    tag: str | None = None,
    paquetes: Sequence[str] = ("bd",),
    raiz: Path = RAIZ,
    forzar: bool = False,
    ejecutar: Ejecutar = _gh,
) -> list[Path]:
    """Descarga los paquetes del release ``tag`` (o del último), comprueba el SHA-256 y extrae."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        assets = [MANIFIESTO, *(PAQUETES[n].asset for n in paquetes)]
        patrones = [arg for asset in assets for arg in ("--pattern", asset)]
        ejecutar(["release", "download", *([tag] if tag else []), "--repo", REPO_DATOS,
                  "--dir", str(tmp_path), *patrones])
        manifiesto = json.loads((tmp_path / MANIFIESTO).read_text("utf-8"))
        extraidos = []
        for nombre in paquetes:
            info = manifiesto["paquetes"].get(nombre)
            if info is None:
                raise KeyError(f"El release {manifiesto['tag']} no tiene el paquete {nombre}")
            zip_path = tmp_path / info["asset"]
            if sha256(zip_path) != info["sha256"]:
                raise ValueError(f"SHA-256 incorrecto en {info['asset']}: descarga corrupta")
            nuevos = extraer(zip_path, raiz, forzar=forzar)
            extraidos += nuevos
            logger.info("%s (%s): %d ficheros", nombre, manifiesto["tag"], len(nuevos))
    return extraidos


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Comparte los datos scrapeados del equipo.")
    sub = parser.add_subparsers(dest="accion", required=True)

    bajar = sub.add_parser("descargar", help="Baja los datos del repo privado")
    bajar.add_argument("--tag", help="Release concreto (por defecto, el último)")
    bajar.add_argument("--paquete", nargs="+", choices=PAQUETES, default=["bd"])
    bajar.add_argument("--todo", action="store_true", help="BD + caché HTML + fichas de los tests")
    bajar.add_argument("--forzar", action="store_true", help="Sustituye la BD local si existe")

    subir = sub.add_parser("publicar", help="Sube los datos locales como un release nuevo")
    subir.add_argument("tag", help="Nombre del release, p. ej. uc3m-2026-10-12")
    subir.add_argument("--paquete", nargs="+", choices=PAQUETES, default=list(PAQUETES))

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.accion == "descargar":
        paquetes = list(PAQUETES) if args.todo else args.paquete
        descargar(args.tag, paquetes, forzar=args.forzar)
    else:
        publicar(args.tag, args.paquete)


if __name__ == "__main__":
    main()
