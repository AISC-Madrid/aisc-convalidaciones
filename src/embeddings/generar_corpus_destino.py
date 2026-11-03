import json
import sqlite3
from contextlib import closing
from pathlib import Path
from statistics import median

from src.embeddings.texts import construir_texto_destino, limpiar_descripcion


def main() -> None:

    ruta_bd = Path("data/processed/uc3m.sqlite").resolve()
    ruta_salida = Path("data/processed/corpus_gatech.jsonl")

    with closing(sqlite3.connect(f"{ruta_bd.as_uri()}?mode=ro", uri=True)) as conexion:
        filas = conexion.execute(
            """
            SELECT id, codigo, nombre, descripcion
            FROM dest_subjects
            WHERE universidad = 'GATECH'
            ORDER BY codigo, id
            """
        ).fetchall()

    sin_descripcion = 0

    with ruta_salida.open("w", encoding="utf-8") as archivo:
        for identificador, codigo, nombre, descripcion in filas:
            descripcion_vacia = not (descripcion or "").strip()
            sin_descripcion += int(descripcion_vacia)

            registro = {
                "id": identificador,
                "universidad": "GATECH",
                "codigo": codigo,
                "nombre": nombre,
                "texto": construir_texto_destino(nombre, descripcion),
                "descripcion_vacia": descripcion_vacia,
            }

            archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")

    print(f"Archivo generado: {ruta_salida}")
    print(f"Asignaturas exportadas: {len(filas)}")
    print(f"Sin descripción original: {sin_descripcion}")


    longitudes = []
    descripciones_cortas = []

    for _identificador, codigo, _nombre, descripcion in filas:
        descripcion_limpia = limpiar_descripcion(descripcion)
        numero_palabras = len(descripcion_limpia.split())
        longitudes.append(numero_palabras)

        if 0 < numero_palabras < 10:
            descripciones_cortas.append((codigo, numero_palabras))

    print("\nLongitud de las descripciones limpias, sin incluir el nombre:")
    print(f"Mínimo: {min(longitudes)} palabras")
    print(f"Mediana: {median(longitudes)} palabras")
    print(f"Máximo: {max(longitudes)} palabras")
    print(f"Descripciones de 1 a 9 palabras: {len(descripciones_cortas)}")

    for codigo, numero_palabras in descripciones_cortas[:10]:
        print(f"  {codigo}: {numero_palabras} palabras")

    vacias_tras_limpieza = sum(longitud == 0 for longitud in longitudes)

    print(f"Descripciones vacías tras limpiar: {vacias_tras_limpieza}")
    print(
        "Descripciones que quedaron vacías por la limpieza: "
        f"{vacias_tras_limpieza - sin_descripcion}"
    )

if __name__ == "__main__":
    main()
