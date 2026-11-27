"""Aplicación web de convalidaciones."""

from datetime import date
from types import SimpleNamespace

import bd_resultados
import catalogo
import pdf
import resultados
import streamlit as st

SELECCION = "propuestas_seleccionadas"
ETIQUETAS = {
    "PRECEDENTE_APROBADO": "Precedente aprobado",
    "SUGERENCIA_IA": "Sugerencia IA",
}


def texto_cabecera(datos):
    """Grado, universidad, fecha de generación y umbral de los resultados, para la cabecera."""
    partes = [f"{datos['grado']} · {datos['universidad']}"]
    generado = datos.get("generado")
    if isinstance(generado, str) and generado:
        try:
            generado = date.fromisoformat(generado).strftime("%d/%m/%Y")
        except ValueError:
            pass  # si no es una fecha ISO, se muestra tal cual
        partes.append(f"Generado el {generado}")
    umbral = datos.get("umbral")
    if isinstance(umbral, (int, float)) and not isinstance(umbral, bool):
        partes.append(f"Umbral de similitud: {umbral:.2f}".replace(".", ","))
    return " · ".join(partes)


def _objetos_resultados(filas):
    return [
        SimpleNamespace(
            origen=SimpleNamespace(**fila["origen"]),
            destino=SimpleNamespace(**fila["destino"]),
            etiqueta=fila["etiqueta"],
            score=fila["score"],
            grupo=fila.get("grupo"),
            aviso_ects=fila.get("aviso_ects", False),
            fila_original=fila,
        )
        for fila in filas
    ]


def preparar_bloques(filas, texto="", filtro="Todas"):
    """Agrupa propuestas, aplica búsqueda y etiqueta, y ordena precedentes primero."""
    objetos = _objetos_resultados(filas)
    bloques = resultados.ordenar(resultados.agrupar(objetos))
    bloques = resultados.filtrar(bloques, texto)
    if filtro == "Precedentes aprobados":
        bloques = [bloque for bloque in bloques if resultados.es_precedente(bloque)]
    elif filtro == "Sugerencias IA":
        bloques = [bloque for bloque in bloques if not resultados.es_precedente(bloque)]
    return bloques


def _fila_tabla(bloque):
    def nombres(lado):
        asignaturas = {}
        for fila in bloque:
            asignatura = getattr(fila, lado)
            asignaturas[asignatura.codigo] = asignatura
        return "\n".join(
            f"{asignatura.nombre} ({asignatura.codigo})"
            for asignatura in asignaturas.values()
        )

    def ects(lado):
        return sum(
            {
                getattr(fila, lado).codigo: getattr(fila, lado).ects
                for fila in bloque
            }.values()
        )

    etiqueta = (
        "Precedente aprobado"
        if resultados.es_precedente(bloque)
        else "Sugerencia IA"
    )
    return {
        "Asignaturas UC3M": nombres("origen"),
        "ECTS UC3M": ects("origen"),
        "Asignaturas destino": nombres("destino"),
        "ECTS destino": ects("destino"),
        "Similitud": max(fila.score for fila in bloque),
        "Etiqueta": etiqueta,
        "Aviso": "ECTS dispares" if any(fila.aviso_ects for fila in bloque) else "",
    }

def _elegir_combinacion():
    """Pinta los desplegables y devuelve (grado, universidad), o None si no hay datos."""
    try:
        combinaciones = bd_resultados.combinaciones()
    except catalogo.BDNoDisponible as error:
        st.error("Los resultados no están disponibles ahora mismo. Inténtalo más tarde.")
        st.caption(f"Detalle técnico: {error}")
        return None
    if not combinaciones:
        st.info("Todavía no hay resultados publicados para ningún grado.")
        return None

    columna_grado, columna_universidad = st.columns(2)
    grado = columna_grado.selectbox(
        "Grado UC3M", bd_resultados.grados(combinaciones), key="grado"
    )
    universidad = columna_universidad.selectbox(
        "Universidad de destino",
        bd_resultados.universidades(combinaciones, grado),
        key="universidad",
    )

    # Si cambia la combinación, la selección anterior ya no tiene sentido.
    combinacion = (grado, universidad)
    if st.session_state.get("combinacion") != combinacion:
        st.session_state["combinacion"] = combinacion
        st.session_state[SELECCION] = set()
        st.session_state["pagina"] = 1
    return combinacion


def _pagina_resultados():
    st.subheader("Resultados")
    st.warning(
        "Estos resultados son todavía de ejemplo: no son equivalencias reales "
        "ni constituyen una aprobación de convalidación."
    )

    combinacion = _elegir_combinacion()
    if combinacion is None:
        return

    try:
        datos = bd_resultados.cargar(*combinacion)
    except (catalogo.BDNoDisponible, bd_resultados.SinResultados) as error:
        st.error("No se pueden mostrar los resultados de esta combinación.")
        st.caption(str(error))
        return

    st.caption(texto_cabecera(datos))
    columna_texto, columna_filtro = st.columns([3, 1])
    texto = columna_texto.text_input(
        "Buscar por asignatura o código",
        placeholder="Ej.: Sistemas Operativos o CS 2200",
    )
    filtro = columna_filtro.selectbox(
        "Tipo de resultado",
        ["Todas", "Precedentes aprobados", "Sugerencias IA"],
    )

    bloques = preparar_bloques(datos["resultados"], texto, filtro)
    if not bloques:
        st.info("No hay propuestas que coincidan con la búsqueda y el filtro.")
        visibles = []
    else:
        visibles = _paginacion(bloques)
        _tabla_resultados(visibles)
    _seleccion_y_pdf(datos, bloques, visibles)


def _paginacion(bloques):
    """Si hay más de una página, pinta el selector y devuelve solo los bloques de esa página."""
    _, total = resultados.paginar(bloques, 1)
    if total == 1:
        return bloques

    # Si una búsqueda deja menos páginas, volvemos a la 1 antes de pintar el selector.
    if st.session_state.get("pagina", 1) > total:
        st.session_state["pagina"] = 1
    pagina = st.number_input(
        f"Página (de {total})", min_value=1, max_value=total, step=1, key="pagina"
    )
    visibles, _ = resultados.paginar(bloques, pagina)
    inicio = (pagina - 1) * resultados.TAMANO_PAGINA + 1
    st.caption(f"Propuestas {inicio}-{inicio + len(visibles) - 1} de {len(bloques)}")
    return visibles


def _tabla_resultados(bloques):
    st.dataframe(
        [_fila_tabla(bloque) for bloque in bloques],
        hide_index=True,
        column_config={
            "Asignaturas UC3M": st.column_config.TextColumn(width="large"),
            "Asignaturas destino": st.column_config.TextColumn(width="large"),
            "ECTS UC3M": st.column_config.NumberColumn(format="%.1f"),
            "ECTS destino": st.column_config.NumberColumn(format="%.1f"),
            "Similitud": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    st.caption(
        "Las asignaturas con el mismo grupo n:m aparecen juntas como una única propuesta. "
        "La similitud no indica la probabilidad de aprobación."
    )


def _seleccion_y_pdf(datos, bloques, visibles):
    st.subheader("Selecciona tus propuestas")
    # La selección se guarda por clave (no por posición) y fuera de los checkbox,
    # para que no cambie de propuesta al buscar ni se pierda si el filtro la oculta.
    seleccionadas = st.session_state.setdefault(SELECCION, set())
    for bloque in visibles:
        fila = _fila_tabla(bloque)
        etiqueta = (
            f"{fila['Asignaturas UC3M'].replace(chr(10), ', ')} → "
            f"{fila['Asignaturas destino'].replace(chr(10), ', ')}"
        )
        clave = resultados.clave_bloque(bloque)
        if st.checkbox(etiqueta, key=f"propuesta_{clave}", value=clave in seleccionadas):
            seleccionadas.add(clave)
        else:
            seleccionadas.discard(clave)

    todos = preparar_bloques(datos["resultados"])
    seleccion = [
        fila.fila_original
        for bloque in todos
        if resultados.clave_bloque(bloque) in seleccionadas
        for fila in bloque
    ]
    ocultas = len(seleccionadas) - sum(
        resultados.clave_bloque(bloque) in seleccionadas for bloque in bloques
    )
    if ocultas:
        st.caption(
            f"Tienes {ocultas} propuesta(s) seleccionada(s) que el filtro oculta; "
            "siguen incluidas en el PDF."
        )

    ects_origen, ects_destino = pdf.calcular_ects(seleccion)
    columna_origen, columna_destino = st.columns(2)
    columna_origen.metric("ECTS UC3M seleccionados", ects_origen)
    columna_destino.metric("ECTS destino seleccionados", ects_destino)

    nombre = st.text_input("Nombre del alumno")
    motivo = resultados.motivo_no_descarga(seleccion, nombre)
    if motivo:
        st.info(motivo)
        st.download_button(
            "Descargar propuesta PDF",
            data=b"",
            file_name="propuesta_convalidacion.pdf",
            mime="application/pdf",
            disabled=True,
        )
        return

    try:
        contenido_pdf = pdf.generar_pdf(
            {
                "nombre": nombre.strip(),
                "grado": datos["grado"],
                "universidad": datos["universidad"],
            },
            seleccion,
        )
    except (KeyError, TypeError, ValueError) as error:
        st.error("No se pudo generar la propuesta PDF.")
        st.caption(f"Detalle técnico: {error}")
        return

    st.download_button(
        "Descargar propuesta PDF",
        data=contenido_pdf,
        file_name="propuesta_convalidacion.pdf",
        mime="application/pdf",
    )


def main(ruta_bd=catalogo.RUTA_BD):
    st.set_page_config(page_title="Convalidaciones · AISC", layout="wide")
    st.title("AISC · Buscador de convalidaciones")
    st.caption("Explora propuestas orientativas para tu movilidad. El tutor decide.")

    pestaña_resultados, pestaña_catalogo, pestaña_como_funciona = st.tabs(
        ["Resultados", "Catálogo", "Cómo funciona"]
    )
    with pestaña_resultados:
        _pagina_resultados()
    with pestaña_catalogo:
        catalogo.pagina_catalogo(ruta_bd)
    with pestaña_como_funciona:
        st.subheader("Cómo funciona")
        st.write(
            "La web muestra propuestas calculadas previamente a partir de asignaturas "
            "de la UC3M y de la universidad de destino. No carga ni ejecuta modelos "
            "de inteligencia artificial durante la consulta."
        )
        st.markdown(
            "- **Precedente aprobado:** existe una convalidación histórica.\n"
            "- **Sugerencia IA:** propuesta orientativa basada en similitud de contenidos.\n"
            "- **Propuestas n:m:** las asignaturas del mismo grupo se mantienen juntas.\n"
            "- **PDF:** incluye únicamente las propuestas seleccionadas y debe revisarlo el tutor."
        )
        st.info(
            "En esta versión, los resultados mostrados son datos de ejemplo y no "
            "representan decisiones oficiales."
        )


if __name__ == "__main__":
    main()
