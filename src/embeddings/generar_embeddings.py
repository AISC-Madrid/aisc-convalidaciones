"""Generación y consulta local de embeddings de los dos catálogos."""

import argparse
import json
import unicodedata
from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np

from src.embeddings.index import buscar_top_k

DIMENSION = 384
SEMILLA_SIMULACION = 37
DIRECTORIO_DATOS = Path("data/processed")
CORPUS_UC3M = DIRECTORIO_DATOS / "corpus_uc3m.jsonl"
CORPUS_GATECH = DIRECTORIO_DATOS / "corpus_gatech.jsonl"

Encoder = Callable[[list[str]], np.ndarray]


def _leer_corpus(ruta: str | Path) -> list[dict[str, str]]:
    registros = []
    with Path(ruta).open(encoding="utf-8") as archivo:
        for numero_linea, linea in enumerate(archivo, start=1):
            if not linea.strip():
                continue

            registro = json.loads(linea)
            if not isinstance(registro, dict):
                raise ValueError(f"El registro de {ruta}, línea {numero_linea}, no es un objeto.")
            if not isinstance(registro.get("texto"), str):
                raise ValueError(f"Falta el texto en {ruta}, línea {numero_linea}.")
            if not isinstance(registro.get("codigo"), str) or not isinstance(
                registro.get("nombre"), str
            ):
                raise ValueError(
                    f"Falta el código o nombre en {ruta}, línea {numero_linea}."
                )
            registros.append(registro)

    if not registros:
        raise ValueError(f"El corpus está vacío: {ruta}")
    return registros


def _validar_vectores(vectores: np.ndarray, cantidad: int) -> np.ndarray:
    matriz = np.asarray(vectores, dtype=np.float32)
    if matriz.shape != (cantidad, DIMENSION):
        raise ValueError(
            f"Se esperaba una matriz de forma ({cantidad}, {DIMENSION}); "
            f"se recibió {matriz.shape}."
        )
    if not np.isfinite(matriz).all():
        raise ValueError("Los vectores deben contener números finitos.")

    normas = np.linalg.norm(matriz, axis=1)
    if not np.allclose(normas, 1.0, rtol=0.0, atol=1e-4):
        raise ValueError("Cada vector debe estar normalizado a longitud uno.")
    return matriz


def _simular(textos: list[str], semilla: int) -> np.ndarray:
    generador = np.random.default_rng(semilla)
    vectores = generador.standard_normal((len(textos), DIMENSION)).astype(np.float32)
    return vectores / np.linalg.norm(vectores, axis=1, keepdims=True)


def _codificar_real(textos: list[str]) -> np.ndarray:
    from src.embeddings.encoder import encode_textos

    return encode_textos(textos)


def generar_embeddings_corpus(
    ruta_corpus: str | Path,
    ruta_vectores: str | Path,
    ruta_metadatos: str | Path,
    *,
    encoder: Encoder | None = None,
    simular: bool = False,
    semilla: int = SEMILLA_SIMULACION,
) -> tuple[Path, Path]:
    """Genera y guarda la matriz y los metadatos en el orden del corpus."""
    registros = _leer_corpus(ruta_corpus)
    textos = [registro["texto"] for registro in registros]

    if simular:
        vectores = _simular(textos, semilla)
    else:
        funcion_encoder = _codificar_real if encoder is None else encoder
        vectores = funcion_encoder(textos)
    matriz = _validar_vectores(vectores, len(registros))

    ruta_vectores = Path(ruta_vectores)
    ruta_metadatos = Path(ruta_metadatos)
    ruta_vectores.parent.mkdir(parents=True, exist_ok=True)
    ruta_metadatos.parent.mkdir(parents=True, exist_ok=True)

    np.save(ruta_vectores, matriz, allow_pickle=False)
    metadatos = {
        "dimension": DIMENSION,
        "simulado": simular,
        "asignaturas": [
            {"codigo": registro["codigo"], "nombre": registro["nombre"]}
            for registro in registros
        ],
    }
    ruta_metadatos.write_text(
        json.dumps(metadatos, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return ruta_vectores, ruta_metadatos


def generar_embeddings_catalogos(
    ruta_corpus_uc3m: str | Path = CORPUS_UC3M,
    ruta_corpus_gatech: str | Path = CORPUS_GATECH,
    directorio_salida: str | Path = DIRECTORIO_DATOS,
    *,
    encoder: Encoder | None = None,
    simular: bool = False,
    semilla: int = SEMILLA_SIMULACION,
) -> dict[str, tuple[Path, Path]]:
    """Genera embeddings de ambos corpus; la simulación se guarda en subdirectorio propio."""
    directorio_salida = Path(directorio_salida)
    if simular:
        directorio_salida = directorio_salida / "simulados"

    resultados = {}
    for desfase_semilla, (nombre, ruta_corpus) in enumerate(
        (
            ("uc3m", ruta_corpus_uc3m),
            ("gatech", ruta_corpus_gatech),
        )
    ):
        resultados[nombre] = generar_embeddings_corpus(
            ruta_corpus,
            directorio_salida / f"embeddings_{nombre}.npy",
            directorio_salida / f"embeddings_{nombre}.json",
            encoder=encoder,
            simular=simular,
            semilla=semilla + desfase_semilla,
        )
    return resultados


def cargar_embeddings(
    ruta_vectores: str | Path,
    ruta_metadatos: str | Path,
) -> tuple[np.ndarray, dict[str, object]]:
    """Carga los vectores y comprueba su forma y correspondencia con los metadatos."""
    ruta_vectores = Path(ruta_vectores)
    ruta_metadatos = Path(ruta_metadatos)
    metadatos = json.loads(ruta_metadatos.read_text(encoding="utf-8"))
    if not isinstance(metadatos, dict) or metadatos.get("dimension") != DIMENSION:
        raise ValueError(f"Metadatos inválidos: {ruta_metadatos}")
    asignaturas = metadatos.get("asignaturas")
    if not isinstance(asignaturas, list):
        raise ValueError(f"Faltan asignaturas en los metadatos: {ruta_metadatos}")
    if any(
        not isinstance(asignatura, dict)
        or not isinstance(asignatura.get("codigo"), str)
        or not isinstance(asignatura.get("nombre"), str)
        for asignatura in asignaturas
    ):
        raise ValueError(f"Metadatos de asignaturas inválidos: {ruta_metadatos}")

    vectores = np.load(ruta_vectores, allow_pickle=False)
    matriz = _validar_vectores(vectores, len(asignaturas))
    return matriz, metadatos


def _normalizar_nombre(nombre: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", nombre.casefold())
    sin_tildes = "".join(
        caracter for caracter in descompuesto if not unicodedata.combining(caracter)
    )
    return " ".join(sin_tildes.split())


def comprobar_top5(
    directorio: str | Path = DIRECTORIO_DATOS,
    *,
    nombre_consulta: str = "Estructuras de Datos",
    codigo_uc3m: str | None = None,
) -> list[tuple[str, str, float]]:
    """Imprime el top-5 real o lista coincidencias ambiguas sin elegir una automáticamente."""
    directorio = Path(directorio)
    uc3m, metadatos_uc3m = cargar_embeddings(
        directorio / "embeddings_uc3m.npy",
        directorio / "embeddings_uc3m.json",
    )
    gatech, metadatos_gatech = cargar_embeddings(
        directorio / "embeddings_gatech.npy",
        directorio / "embeddings_gatech.json",
    )
    if metadatos_uc3m.get("simulado") or metadatos_gatech.get("simulado"):
        raise ValueError("Los vectores simulados no permiten validar similitudes reales.")

    asignaturas = metadatos_uc3m["asignaturas"]
    coincidencias = [
        (indice, asignatura)
        for indice, asignatura in enumerate(asignaturas)
        if _normalizar_nombre(asignatura["nombre"]) == _normalizar_nombre(nombre_consulta)
    ]
    print(f"Coincidencias UC3M para «{nombre_consulta}»:")
    for _, asignatura in coincidencias:
        print(f"  {asignatura['codigo']}: {asignatura['nombre']}")

    if not coincidencias:
        raise ValueError(f"No se encontró «{nombre_consulta}» en el corpus UC3M.")
    if codigo_uc3m is None and len(coincidencias) > 1:
        raise ValueError("Hay varias coincidencias; indica el código UC3M para elegir.")
    seleccionadas = (
        coincidencias
        if codigo_uc3m is None
        else [
            (indice, asignatura)
            for indice, asignatura in coincidencias
            if asignatura["codigo"] == codigo_uc3m
        ]
    )
    if len(seleccionadas) != 1:
        raise ValueError(f"El código UC3M no identifica una única coincidencia: {codigo_uc3m}.")

    indice_consulta, asignatura_consulta = seleccionadas[0]
    posiciones, puntuaciones = buscar_top_k(uc3m[indice_consulta], gatech, k=5)
    resultados = [
        (
            metadatos_gatech["asignaturas"][int(posicion)]["codigo"],
            metadatos_gatech["asignaturas"][int(posicion)]["nombre"],
            float(puntuacion),
        )
        for posicion, puntuacion in zip(posiciones, puntuaciones, strict=True)
    ]
    print(f"\nTop-5 para {asignatura_consulta['codigo']}: {asignatura_consulta['nombre']}")
    for codigo, nombre, puntuacion in resultados:
        print(f"  {codigo}: {nombre} — {puntuacion:.6f}")
    return resultados


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    acciones = parser.add_mutually_exclusive_group()
    acciones.add_argument(
        "--simular",
        action="store_true",
        help="Genera vectores aleatorios reproducibles en el subdirectorio simulados/.",
    )
    acciones.add_argument(
        "--top5",
        action="store_true",
        help="Carga los vectores reales guardados y comprueba el top-5 de Estructuras de Datos.",
    )
    parser.add_argument("--salida", type=Path, default=DIRECTORIO_DATOS)
    parser.add_argument("--semilla", type=int, default=SEMILLA_SIMULACION)
    parser.add_argument("--codigo-uc3m", help="Código para resolver coincidencias UC3M múltiples.")
    argumentos = parser.parse_args(argv)
    if argumentos.codigo_uc3m and not argumentos.top5:
        parser.error("--codigo-uc3m solo se usa junto con --top5.")

    if argumentos.top5:
        comprobar_top5(argumentos.salida, codigo_uc3m=argumentos.codigo_uc3m)
    else:
        resultados = generar_embeddings_catalogos(
            directorio_salida=argumentos.salida,
            simular=argumentos.simular,
            semilla=argumentos.semilla,
        )
        for nombre, (ruta_vectores, ruta_metadatos) in resultados.items():
            print(f"{nombre}: {ruta_vectores} y {ruta_metadatos}")
        if argumentos.simular:
            print("Vectores simulados: no permiten valorar similitudes reales.")


if __name__ == "__main__":
    main()
