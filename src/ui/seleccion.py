from src.models.match import ects_dispares


def calcular_ects(resultados):
    """Devuelve los ECTS de origen y destino sin repetir asignaturas."""
    origen = {}
    destino = {}

    for resultado in resultados:
        asignatura_origen = resultado["origen"]
        asignatura_destino = resultado["destino"]

        origen[asignatura_origen["codigo"]] = asignatura_origen["ects"]
        destino[asignatura_destino["codigo"]] = asignatura_destino["ects"]

    return sum(origen.values()), sum(destino.values()) 

def obtener_propuesta(resultados, indice):
    """Devuelve la fila elegida o todas las filas de su grupo."""
    elegida = resultados[indice]
    grupo = elegida.get("grupo")

    if grupo is None:
        return [elegida]

    propuesta = []

    for resultado in resultados:
        if resultado.get("grupo") == grupo:
            propuesta.append(resultado)

    return propuesta

def hay_aviso_ects(propuesta):
    """Indica si los créditos de una propuesta difieren más del 25 %."""
    total_origen, total_destino = calcular_ects(propuesta)

    if total_origen == 0:
        return False

    return ects_dispares(total_origen, total_destino)

def obtener_seleccion(resultados, indices):
    """Reúne las propuestas seleccionadas, incluyendo sus grupos completos."""
    seleccion = []

    for indice in indices:
        propuesta = obtener_propuesta(resultados, indice)

        for resultado in propuesta:
            if resultado not in seleccion:
                seleccion.append(resultado)

    return seleccion
