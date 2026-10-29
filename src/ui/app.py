"""Interfaz mínima para el JSON de ejemplo del equipo."""

from pathlib import Path

import streamlit as st

from src.models import Resultados
from src.ui.seleccion_ui import mostrar_seleccion

RUTA_JSON = Path(__file__).resolve().parents[2] / "public/data/ejemplo.json"

COLUMNAS = {
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
    st.set_page_config(page_title="Convalidaciones · AISC", layout="wide")
    st.markdown(
        """
        <style>
               /* Cabecera rosa con texto blanco */
        [data-testid="stExpander"] summary {
            background-color: #EB178E;
            color: #FFFFFF;
            border-radius: 12px;
            padding: 6px 16px;
            display: flex;
            flex-direction: row-reverse;
            justify-content: flex-end;
            gap: 8px;
        }

        [data-testid="stExpander"] summary p {
            color: #FFFFFF;
            font-size: 20px;
            font-weight: 600;
        }

        /* Flecha blanca */
        [data-testid="stExpander"] summary svg,
        [data-testid="stExpander"] summary span {
            color: #FFFFFF;
        }

        /* Botón que abre las etiquetas */
        [data-testid="stPopoverButton"] {
            border: 2px solid #EB178E;
            background-color: #FDE8F3;
            color: #202020;
        }

        [data-testid="stPopoverButton"]:hover {
            background-color: #EB178E;
            color: #111111;
        }

        /* Valores de los contadores de créditos */
        [data-testid="stMetricValue"] {
            color: #EB178E;
        }

        /* Títulos de las secciones */
        [data-testid="stHeading"] h3 {
            color: #EB178E;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )    
    st.title("AISC · Buscador de convalidaciones")
    st.markdown(
        '<div style="height: 4px; background-color: #20CCF1; '
        'border-radius: 2px; margin-bottom: 1rem;"></div>',
        unsafe_allow_html=True,
    )
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
        contenido, columna_filtros = st.columns([4, 1], gap="large")
        filtros = columna_filtros.expander("Filtros", expanded=True)
        opciones_etiqueta = ["Precedente aprobado", "Sugerencia IA"]
        with filtros.popover("Etiquetas"):
            etiquetas_seleccionadas = []

            for etiqueta in opciones_etiqueta:
                if st.checkbox(
                    etiqueta,
                    value=True,
                    key=f"filtro_{etiqueta}",
                ):
                    etiquetas_seleccionadas.append(etiqueta)
                    
        similitud_minima = filtros.slider(
            "Similitud mínima",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.01,
            format="%.2f",
        )
        asignaturas = sorted({fila["Asignatura de origen"] for fila in filas})
        asignatura_seleccionada = filtros.selectbox(
            "Asignatura UC3M",
            ["Todas", *asignaturas],
        )
        filas_filtradas = [
            fila
            for fila in filas
            if fila["Etiqueta"] in etiquetas_seleccionadas
            and fila["Similitud"] >= similitud_minima
            and asignatura_seleccionada in ("Todas", fila["Asignatura de origen"])
        ]
        if filas_filtradas:
            contenido.dataframe(
                filas_filtradas,
                hide_index=True,
                column_config=COLUMNAS,
            )
            contenido.caption(
                "*Precedente aprobado: existe una convalidación histórica.*  \n"
                "*Sugerencia IA: propuesta basada en similitud de contenidos.*"
            )
            contenido.caption(
                "*La similitud no indica la probabilidad de aprobación.*"
            )            
            indices_visibles = [
                indice
                for indice, fila in enumerate(filas)
                if fila in filas_filtradas
            ]

            with contenido:
                mostrar_seleccion(datos["resultados"], indices_visibles)          
        else:
            contenido.info("No hay resultados que coincidan con los filtros seleccionados.")


if __name__ == "__main__":
    main()