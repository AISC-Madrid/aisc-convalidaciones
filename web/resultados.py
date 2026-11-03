"""Lógica de la pantalla de resultados (sin Streamlit).

Trabaja con «bloques»: cada grupo n:m es un bloque con todas sus filas y
cada propuesta 1:1 es un bloque de una fila. Así un grupo nunca se separa
al ordenar ni al filtrar.
"""
from catalogo import normalizar

PRECEDENTE = "PRECEDENTE_APROBADO"


def agrupar(resultados):
    """Junta en un bloque las filas con el mismo `grupo` y deja solas las 1:1."""
    bloques = []
    por_grupo = {}
    for m in resultados:
        if m.grupo is None:
            bloques.append([m])
        elif m.grupo in por_grupo:
            por_grupo[m.grupo].append(m)
        else:
            por_grupo[m.grupo] = [m]
            bloques.append(por_grupo[m.grupo])
    return bloques


def es_precedente(bloque):
    return any(m.etiqueta == PRECEDENTE for m in bloque)


def ordenar(bloques):
    """Precedentes primero; dentro de cada tipo, de mayor a menor score."""
    return sorted(
        bloques,
        key=lambda b: (not es_precedente(b), -max(m.score for m in b)),
    )


def filtrar(bloques, texto=""):
    """Bloques con alguna asignatura (UC3M o destino) que coincida por nombre o código."""
    consulta = normalizar(texto)
    if not consulta:
        return list(bloques)

    def coincide(m):
        campos = (m.origen.nombre, m.origen.codigo, m.destino.nombre, m.destino.codigo)
        return any(consulta in normalizar(c) for c in campos)

    return [b for b in bloques if any(coincide(m) for m in b)]


def motivo_no_descarga(seleccion, nombre_alumno):
    """Por qué no se puede generar el PDF, o None si se puede."""
    if not seleccion:
        return "Selecciona al menos una propuesta para poder generar el PDF."
    if not (nombre_alumno or "").strip():
        return "Escribe tu nombre: aparece en la propuesta que se entrega al tutor."
    return None