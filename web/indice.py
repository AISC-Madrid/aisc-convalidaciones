"""Índice de combinaciones grado × universidad publicadas en public/data."""

import json
from json import JSONDecodeError
from pathlib import Path

DIR_DATOS = Path(__file__).resolve().parent.parent / "public" / "data"
RUTA_INDICE = DIR_DATOS / "index.json"
CAMPOS = ("grado", "universidad", "archivo")


def cargar_indice(ruta=RUTA_INDICE):
    """Lee index.json y devuelve la lista de combinaciones validada."""
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, JSONDecodeError) as error:
        raise ValueError(f"No se puede leer el índice de combinaciones: {error}") from error

    combinaciones = datos.get("combinaciones") if isinstance(datos, dict) else None
    if not isinstance(combinaciones, list) or not combinaciones:
        raise ValueError("El índice no tiene ninguna combinación de grado y universidad.")

    vistas = set()
    for combinacion in combinaciones:
        if not isinstance(combinacion, dict) or not all(
            isinstance(combinacion.get(campo), str) and combinacion[campo].strip()
            for campo in CAMPOS
        ):
            raise ValueError("Hay una combinación sin grado, universidad o archivo.")
        if Path(combinacion["archivo"]).name != combinacion["archivo"]:
            raise ValueError(
                f"El archivo {combinacion['archivo']!r} debe estar en public/data, sin carpetas."
            )
        clave = (combinacion["grado"], combinacion["universidad"])
        if clave in vistas:
            raise ValueError(f"La combinación {clave[0]} · {clave[1]} está repetida.")
        vistas.add(clave)

    return combinaciones


def grados(combinaciones):
    """Grados disponibles, en orden alfabético y sin repetir."""
    return sorted({c["grado"] for c in combinaciones})


def universidades(combinaciones, grado):
    """Universidades que tienen resultados para ese grado."""
    return sorted(c["universidad"] for c in combinaciones if c["grado"] == grado)


def ruta_resultados(combinaciones, grado, universidad, dir_datos=DIR_DATOS):
    """Ruta del JSON de resultados de la combinación elegida."""
    for c in combinaciones:
        if c["grado"] == grado and c["universidad"] == universidad:
            return Path(dir_datos) / c["archivo"]
    raise ValueError(f"No hay resultados para {grado} · {universidad}.")