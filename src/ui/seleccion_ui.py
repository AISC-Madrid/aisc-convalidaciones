import streamlit as st

from src.ui.seleccion import (
    calcular_ects,
    hay_aviso_ects,
    obtener_propuesta,
    obtener_seleccion,
)


def mostrar_seleccion(resultados, indices_visibles):
    claves_visibles = set()

    for indice in indices_visibles:
        grupo = resultados[indice].get("grupo")
        clave = ("grupo", grupo) if grupo is not None else ("fila", indice)
        claves_visibles.add(clave)

    st.subheader("Selecciona tus propuestas")

    indices = []
    grupos_mostrados = set()

    for indice, resultado in enumerate(resultados):
        grupo = resultado.get("grupo")
        clave = ("grupo", grupo) if grupo is not None else ("fila", indice)

        if clave not in claves_visibles:
            continue

        if grupo is not None:
            if grupo in grupos_mostrados:
                continue
            grupos_mostrados.add(grupo)

        propuesta = obtener_propuesta(resultados, indice)

        origen = {
            fila["origen"]["codigo"]: fila["origen"]["nombre"]
            for fila in propuesta
        }
        destino = {
            fila["destino"]["codigo"]: fila["destino"]["nombre"]
            for fila in propuesta
        }

        etiqueta = f"{', '.join(origen.values())} → {', '.join(destino.values())}"

        if st.checkbox(etiqueta, key=f"propuesta_{indice}"):
            indices.append(indice)

        if hay_aviso_ects(propuesta):
            st.caption(
                '<span style="display: block; margin-left: 1.75rem;">'
                "⚠ Esta propuesta tiene una diferencia de ECTS superior al 25 %."
                "</span>",
                unsafe_allow_html=True,
            )

    seleccion = obtener_seleccion(resultados, indices)
    total_origen, total_destino = calcular_ects(seleccion)

    columna_origen, columna_destino = st.columns(2)
    columna_origen.metric("ECTS UC3M seleccionados", total_origen)
    columna_destino.metric("ECTS destino seleccionados", total_destino)

    return seleccion