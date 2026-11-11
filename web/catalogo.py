"""Catálogo de asignaturas para el alumno.

Solo expone código, nombre, ECTS y enlace. Los temarios (objetivos,
programa, descripción) se quedan en la BD: los usa el modelo, no el alumno.
"""
import os
import unicodedata
from urllib.parse import quote

import pymysql
import streamlit as st

# Se conserva como argumento de compatibilidad con app.py y el caché de Streamlit.
RUTA_BD = None

ESTUDIO_BIOMEDICA = "257"
CURSO_ACTUAL = "2026/2027"
UNIVERSIDAD_DESTINO = "GATECH"

UC3M = "UC3M · Ingeniería Biomédica"
GATECH = "Georgia Tech"


class BDNoDisponible(Exception):
    """La base de datos no existe o no se puede leer."""


def conectar(ruta=RUTA_BD):
    """Abre la MySQL del servidor usando las variables MYSQL_* del entorno."""
    del ruta  # La ruta SQLite anterior ya no se utiliza.
    requeridas = ("MYSQL_HOST", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD")
    faltantes = [nombre for nombre in requeridas if not os.environ.get(nombre)]
    if faltantes:
        raise BDNoDisponible(f"Falta configurar: {', '.join(faltantes)}")
    try:
        return pymysql.connect(
            host=os.environ["MYSQL_HOST"],
            port=int(os.environ.get("MYSQL_PORT", "3306")),
            database=os.environ["MYSQL_DATABASE"],
            user=os.environ["MYSQL_USER"],
            password=os.environ["MYSQL_PASSWORD"],
            connect_timeout=5,
            read_timeout=10,
            write_timeout=10,
        )
    except (pymysql.MySQLError, ValueError) as e:
        raise BDNoDisponible(f"No se puede conectar a la base de datos: {e}") from e


_SQL_UC3M = """
SELECT codigo, nombre, creditos, url
FROM (
    SELECT s.codigo, s.nombre, s.creditos, s.url,
           ROW_NUMBER() OVER (
               PARTITION BY s.codigo
               ORDER BY (s.curso_academico = %(curso)s) DESC,
                        s.curso_academico DESC,
                        (s.idioma = 'ES') DESC
           ) AS n
    FROM subjects AS s
    WHERE s.codigo IN (
        SELECT codigo
        FROM subject_plans
        WHERE estudio = %(estudio)s AND curso_academico = %(curso)s
    )
) AS catalogo_uc3m
WHERE n = 1
"""

_SQL_GATECH = """
SELECT codigo, nombre, ects
FROM dest_subjects
WHERE universidad = %s
"""


def url_gatech(codigo):
    return "https://catalog.gatech.edu/search/?P=" + quote(codigo)


def cargar_catalogo(ruta=RUTA_BD):
    con = conectar(ruta)
    try:
        with con.cursor() as cursor:
            cursor.execute(
                _SQL_UC3M, {"estudio": ESTUDIO_BIOMEDICA, "curso": CURSO_ACTUAL}
            )
            uc3m = cursor.fetchall()
            cursor.execute(_SQL_GATECH, (UNIVERSIDAD_DESTINO,))
            gatech = cursor.fetchall()
    except pymysql.MySQLError as e:
        raise BDNoDisponible(f"No se puede leer la base de datos: {e}") from e
    finally:
        con.close()

    asignaturas = [
        {"universidad": UC3M, "codigo": c, "nombre": n, "ects": e, "url": u}
        for c, n, e, u in uc3m
    ] + [
        {
            "universidad": GATECH,
            "codigo": c,
            "nombre": n,
            "ects": e,
            "url": url_gatech(c),
        }
        for c, n, e in gatech
    ]
    return sorted(asignaturas, key=lambda a: (a["universidad"], a["nombre"] or ""))


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto or "")
    sin_tildes = "".join(c for c in texto if not unicodedata.combining(c))
    return sin_tildes.lower().replace(" ", "")


def buscar(asignaturas, texto="", universidad=None):
    consulta = normalizar(texto)
    return [
        a for a in asignaturas
        if (universidad is None or a["universidad"] == universidad)
        and (consulta in normalizar(a["nombre"]) or consulta in normalizar(a["codigo"]))
    ]


# --- Pantalla (Streamlit) ---------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def _cargar_cacheado(ruta):
    return cargar_catalogo(ruta)


def pagina_catalogo(ruta=RUTA_BD):
    st.header("Catálogo de asignaturas")
    st.caption(
        "Asignaturas de Ingeniería Biomédica (UC3M) y de Georgia Tech. "
        "Abre la ficha oficial para ver el temario completo."
    )

    try:
        asignaturas = _cargar_cacheado(str(ruta))
    except BDNoDisponible as e:
        st.error("El catálogo no está disponible ahora mismo. Inténtalo más tarde.")
        st.caption(f"Detalle técnico: {e}")
        return

    col_texto, col_uni = st.columns([3, 1])
    texto = col_texto.text_input(
        "Buscar por nombre o código", placeholder="Ej.: Biomecánica, 19903 o BMED 2110"
    )
    opcion = col_uni.selectbox("Universidad", ["Todas", UC3M, GATECH])
    universidad = None if opcion == "Todas" else opcion

    resultado = buscar(asignaturas, texto, universidad)
    if not resultado:
        st.info("No hay asignaturas que coincidan con la búsqueda.")
        return

    n = len(resultado)
    st.write(f"{n} asignatura{'s' if n != 1 else ''}")
    st.dataframe(
        resultado,
        hide_index=True,
        column_order=["universidad", "codigo", "nombre", "ects", "url"],
        column_config={
            "universidad": "Universidad",
            "codigo": "Código",
            "nombre": "Nombre",
            "ects": st.column_config.NumberColumn("ECTS", format="%.1f"),
            "url": st.column_config.LinkColumn("Ficha", display_text="Abrir ficha"),
        },
    )


if __name__ == "__main__":
    pagina_catalogo()
