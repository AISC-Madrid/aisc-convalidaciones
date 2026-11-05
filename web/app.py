"""Aplicación web de convalidaciones."""

import json
from json import JSONDecodeError
from pathlib import Path
from types import SimpleNamespace

import catalogo
import pdf
import resultados
import streamlit as st

RUTA_EJEMPLO = Path(__file__).with_name("ejemplo.json")
SELECCION = "propuestas_seleccionadas"
ETIQUETAS = {
    "PRECEDENTE_APROBADO": "Precedente aprobado",
    "SUGERENCIA_IA": "Sugerencia IA",
}


def cargar_datos(ruta=RUTA_EJEMPLO):
    """Carga y valida la estructura mínima que necesita la aplicación."""
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, JSONDecodeError) as error:
        raise ValueError(f"No se puede leer el archivo de resultados: {error}") from error

    if not isinstance(datos, dict):
        raise ValueError("El contenido debe ser un objeto JSON.")
    if not isinstance(datos.get("grado"), str) or not isinstance(datos.get("universidad"), str):
        raise ValueError("Faltan el grado o la universidad en el archivo de resultados.")
    filas = datos.get("resultados")
    if not isinstance(filas, list):
        raise ValueError("El archivo de resultados no contiene una lista de propuestas.")

    for fila in filas:
        if not isinstance(fila, dict):
            raise ValueError("Hay una propuesta con un formato no válido.")
        if fila.get("etiqueta") not in ETIQUETAS:
            raise ValueError("Hay una propuesta con una etiqueta no reconocida.")
        if not isinstance(fila.get("score"), (int, float)):
            raise ValueError("Hay una propuesta sin una puntuación numérica.")
        for lado in ("origen", "destino"):
            asignatura = fila.get(lado)
            if not isinstance(asignatura, dict) or not all(
                isinstance(asignatura.get(campo), str) for campo in ("codigo", "nombre")
            ):
                raise ValueError(f"Hay una asignatura de {lado} con un formato no válido.")
            if not isinstance(asignatura.get("ects"), (int, float)):
                raise ValueError(f"Faltan los ECTS de una asignatura de {lado}.")
        grupo = fila.get("grupo")
        if grupo is not None and not isinstance(grupo, (int, str)):
            raise ValueError("Hay una propuesta con un grupo no válido.")

    return datos


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


def _pagina_resultados(ruta_json):
    st.subheader("Resultados")
    st.warning(
        "Estos resultados son todavía de ejemplo y proceden de ejemplo.json. "
        "No son equivalencias reales ni constituyen una aprobación de convalidación."
    )

    try:
        datos = cargar_datos(ruta_json)
    except ValueError as error:
        st.error("No se pueden mostrar los resultados de ejemplo.")
        st.caption(str(error))
        return

    st.caption(f"{datos['grado']} · {datos['universidad']}")
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
    else:
        _tabla_resultados(bloques)
    _seleccion_y_pdf(datos, bloques)


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


def _seleccion_y_pdf(datos, bloques):
    st.subheader("Selecciona tus propuestas")
    # La selección se guarda por clave (no por posición) y fuera de los checkbox,
    # para que no cambie de propuesta al buscar ni se pierda si el filtro la oculta.
    seleccionadas = st.session_state.setdefault(SELECCION, set())
    for bloque in bloques:
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


def main(ruta_json=RUTA_EJEMPLO, ruta_bd=catalogo.RUTA_BD):
    st.set_page_config(page_title="Convalidaciones · AISC", layout="wide")
    st.title("AISC · Buscador de convalidaciones")
    st.caption("Explora propuestas orientativas para tu movilidad. El tutor decide.")

    pestaña_resultados, pestaña_catalogo, pestaña_como_funciona = st.tabs(
        ["Resultados", "Catálogo", "Cómo funciona"]
    )
    with pestaña_resultados:
        _pagina_resultados(ruta_json)
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