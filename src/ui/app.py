"""Interfaz mínima para el JSON de ejemplo del equipo."""

from pathlib import Path

import streamlit as st

from src.models import Resultados

RUTA_JSON = Path(__file__).resolve().parents[2] / "public/data/ejemplo.json"


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
                "Asignatura de origen": f"{origen['nombre']} ({origen['codigo']})",
                "ECTS origen": origen["ects"],
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
    # layout="wide" aprovecha el ancho disponible.
    st.set_page_config(page_title="Convalidaciones · AISC", layout="wide")
    st.title("AISC · Buscador de convalidaciones")
    st.write("Explora posibles equivalencias para tu movilidad.")
    st.caption("Las propuestas requieren la revisión del tutor.")

    datos, filas, error = None, [], None
    try:
        datos = cargar_datos(ruta)
        filas = preparar_tabla(datos["resultados"])
    except FileNotFoundError:
        pass  # Es normal mientras esperamos el archivo de Héctor.
    except (ValueError, KeyError, TypeError):
        datos = None
        error = "El archivo de resultados no tiene el formato esperado."
    except OSError:
        error = "No se ha podido leer el archivo de resultados."

    # Un JSON contiene una sola combinación de grado y universidad.
    columna_grado, columna_universidad = st.columns(2)
    with columna_grado:
        # selectbox crea un desplegable.
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
        st.dataframe(
            filas,
            hide_index=True,
            column_config={
                "Asignatura de origen": st.column_config.TextColumn(width="large"),
                "Asignatura de destino": st.column_config.TextColumn("Destino", width="large"),
                "ECTS origen": st.column_config.NumberColumn(width="small"),
                "ECTS destino": st.column_config.NumberColumn(width="small"),
                "Similitud": st.column_config.NumberColumn(format="%.2f", width="small"),
                "Etiqueta": st.column_config.TextColumn(width="medium"),
                "Aviso": st.column_config.TextColumn(width="small"),
                "Ficha de destino": st.column_config.LinkColumn(
                    "Ficha", display_text="Ver ficha", width="small"
                ),
                "Grupo conjunto": st.column_config.TextColumn("Grupo", width="small"),
            },
        )
    st.caption(
        "*Precedente aprobado: existe una convalidación histórica.*  \n"
        "*Sugerencia IA: propuesta basada en similitud de contenidos.*"
        # *texto* pone el texto en cursiva.
    )
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("*La similitud no indica la probabilidad de aprobación.*")


if __name__ == "__main__":
    main()

