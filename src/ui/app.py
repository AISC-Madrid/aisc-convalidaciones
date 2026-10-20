"""Interfaz mínima para el JSON de ejemplo del equipo."""

from pathlib import Path

import streamlit as st

from src.models import Resultados

RUTA_JSON = Path(__file__).resolve().parents[2] / "public/data/ejemplo.json"

COLUMNAS = {
    "Asignatura UC3M": st.column_config.TextColumn(width="large"),
    "Asignatura de destino": st.column_config.TextColumn("Destino", width="large"),
    "ECTS UC3M": st.column_config.NumberColumn(width="small"),
    "ECTS destino": st.column_config.NumberColumn(width="small"),
    "Similitud": st.column_config.NumberColumn(format="%.2f", width="small"),
    "Etiqueta": st.column_config.TextColumn(width="medium"),
    "Aviso": st.column_config.TextColumn(width="small"),
    "Ficha de destino": st.column_config.LinkColumn(
        "Ficha", display_text="Ver ficha", width="small"
    ),
    "Grupo conjunto": st.column_config.TextColumn("Grupo", width="small"),
}


def cargar_datos(ruta):
    """Lee el JSON como un diccionario de Python."""
    datos = Resultados.model_validate_json(Path(ruta).read_text(encoding="utf-8")).model_dump()
    return datos


def preparar_tabla(resultados):
    """Transforma las parejas de asignaturas en filas legibles."""
    etiquetas = {
        "PRECEDENTE_APROBADO": "Precedente aprobado",
        "SUGERENCIA_IA": "Sugerencia IA",
    }
    filas = []
    for resultado in resultados:
        origen, destino = resultado["origen"], resultado["destino"]
        filas.append(
            {
                "Asignatura UC3M": f"{origen['nombre']} ({origen['codigo']})",
                "ECTS UC3M": origen["ects"],
                "Asignatura de destino": f"{destino['nombre']} ({destino['codigo']})",
                "ECTS destino": destino["ects"],
                "Similitud": resultado["score"],
                "Etiqueta": etiquetas[resultado["etiqueta"]],
                "Aviso": "ECTS dispares" if resultado["aviso_ects"] else "",
                "Ficha de destino": destino.get("url"),
                "Grupo conjunto": str(resultado["grupo"])
                if resultado.get("grupo") is not None
                else "",
            }
        )
    return filas


def main(ruta=RUTA_JSON):
    st.set_page_config(page_title="Convalidaciones · AISC", layout="wide")
    st.title("AISC · Buscador de convalidaciones")
    st.write("Explora posibles equivalencias para tu movilidad.")
    st.caption("Las propuestas requieren la revisión del tutor.")

    datos, filas, error = None, [], None
    try:
        datos = cargar_datos(ruta)
        filas = preparar_tabla(datos["resultados"])
    except FileNotFoundError:
        pass  # Sin archivo todavía: se muestra un aviso, no un error.
    except (ValueError, KeyError, TypeError):
        datos = None
        error = "El archivo de resultados no tiene el formato esperado."
    except OSError:
        error = "No se ha podido leer el archivo de resultados."

    # Un JSON contiene una sola combinación de grado y universidad.
    columna_grado, columna_universidad = st.columns(2)
    with columna_grado:
        st.selectbox(
            "Grado",
            [datos["grado"]] if datos else ["Pendiente de cargar datos"],
            disabled=datos is None,
        )
    with columna_universidad:
        st.selectbox(
            "Universidad de destino",
            [datos["universidad"]] if datos else ["Pendiente de cargar datos"],
            disabled=datos is None,
        )

    st.subheader("Resultados")
    if error:
        st.error(error)
    elif datos is None:
        st.info("Todavía no hay resultados disponibles. Esperando los datos de ejemplo.")
    elif not filas:
        st.info("No hay equivalencias disponibles para este grado y universidad.")
    else:
        st.caption("Datos de ejemplo: asignaturas y resultados inventados.")
        st.caption("Las filas con el mismo grupo pertenecen a una propuesta conjunta.")
        opciones_etiqueta = ["Precedente aprobado", "Sugerencia IA"]
        etiquetas_seleccionadas = st.sidebar.multiselect(
            "Etiqueta",
            opciones_etiqueta,
            default=opciones_etiqueta,
        )
        similitud_minima = st.sidebar.slider(
            "Similitud mínima",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.01,
            format="%.2f",
        )
        asignaturas = sorted({fila["Asignatura UC3M"] for fila in filas})
        asignatura_seleccionada = st.sidebar.selectbox(
            "Asignatura UC3M",
            ["Todas", *asignaturas],
        )
        filas_filtradas = [
            fila
            for fila in filas
            if fila["Etiqueta"] in etiquetas_seleccionadas
            and fila["Similitud"] >= similitud_minima
            and asignatura_seleccionada in ("Todas", fila["Asignatura UC3M"])
        ]
        if filas_filtradas:
            st.dataframe(
                filas_filtradas,
                hide_index=True,
                column_config=COLUMNAS,
            )
        else:
            st.info("No hay resultados que coincidan con los filtros seleccionados.")
    st.caption(
        "*Precedente aprobado: existe una convalidación histórica.*  \n"
        "*Sugerencia IA: propuesta basada en similitud de contenidos.*"
    )
    st.caption("*La similitud no indica la probabilidad de aprobación.*")


if __name__ == "__main__":
    main()
