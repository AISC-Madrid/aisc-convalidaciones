from src.ui.seleccion import calcular_ects, hay_aviso_ects, obtener_propuesta, obtener_seleccion


def test_no_duplica_creditos_de_origen():
    resultados = [
        {
            "origen": {"codigo": "001", "ects": 6},
            "destino": {"codigo": "CS1301", "ects": 4.5},
        },
        {
            "origen": {"codigo": "001", "ects": 6},
            "destino": {"codigo": "CS1331", "ects": 4.5},
        },
    ]

    total_origen, total_destino = calcular_ects(resultados)

    assert total_origen == 6
    assert total_destino == 9

def test_no_duplica_creditos_de_destino():
    resultados = [
        {
            "origen": {"codigo": "001", "ects": 3},
            "destino": {"codigo": "CS1301", "ects": 6},
        },
        {
            "origen": {"codigo": "002", "ects": 3},
            "destino": {"codigo": "CS1301", "ects": 6},
        },
    ]

    total_origen, total_destino = calcular_ects(resultados)

    assert total_origen == 6
    assert total_destino == 6

def test_seleccion_vacia():
    assert calcular_ects([]) == (0, 0)


def test_una_equivalencia_individual():
    resultados = [
        {
            "origen": {"codigo": "001", "ects": 6},
            "destino": {"codigo": "CS1301", "ects": 4.5},
        },
    ]

    assert calcular_ects(resultados) == (6, 4.5)


def test_grupo_nm_sin_duplicar_creditos():
    resultados = [
        {
            "origen": {"codigo": "001", "ects": 3},
            "destino": {"codigo": "CS1301", "ects": 4.5},
        },
        {
            "origen": {"codigo": "001", "ects": 3},
            "destino": {"codigo": "CS1331", "ects": 4.5},
        },
        {
            "origen": {"codigo": "002", "ects": 6},
            "destino": {"codigo": "CS1301", "ects": 4.5},
        },
        {
            "origen": {"codigo": "002", "ects": 6},
            "destino": {"codigo": "CS1331", "ects": 4.5},
        },
    ]

    assert calcular_ects(resultados) == (9, 9)

def test_propuesta_individual_no_agrupa_filas_sin_grupo():
    resultados = [
        {"grupo": None, "nombre": "Propuesta A"},
        {"grupo": None, "nombre": "Propuesta B"},
    ]

    assert obtener_propuesta(resultados, 0) == [resultados[0]]


def test_propuesta_conjunta_incluye_todo_el_grupo():
    resultados = [
        {"grupo": 1, "nombre": "Parte A"},
        {"grupo": None, "nombre": "Individual"},
        {"grupo": 1, "nombre": "Parte B"},
        {"grupo": 2, "nombre": "Otro grupo"},
    ]

    esperado = [resultados[0], resultados[2]]

    assert obtener_propuesta(resultados, 0) == esperado
    assert obtener_propuesta(resultados, 2) == esperado


def test_sin_seleccion_no_hay_aviso():
    assert hay_aviso_ects([]) is False


def test_creditos_iguales_no_generan_aviso():
    propuesta = [
        {
            "origen": {"codigo": "001", "ects": 6},
            "destino": {"codigo": "CS1", "ects": 6},
        },
    ]

    assert hay_aviso_ects(propuesta) is False


def test_diferencia_exacta_del_25_por_ciento_no_genera_aviso():
    propuesta = [
        {
            "origen": {"codigo": "001", "ects": 6},
            "destino": {"codigo": "CS1", "ects": 7.5},
        },
    ]

    assert hay_aviso_ects(propuesta) is False


def test_creditos_insuficientes_generan_aviso():
    propuesta = [
        {
            "origen": {"codigo": "001", "ects": 6},
            "destino": {"codigo": "CS1", "ects": 4},
        },
    ]

    assert hay_aviso_ects(propuesta) is True


def test_aviso_compara_totales_del_grupo():
    propuesta = [
        {
            "origen": {"codigo": "001", "ects": 6},
            "destino": {"codigo": "CS1", "ects": 4.5},
            "grupo": 1,
        },
        {
            "origen": {"codigo": "001", "ects": 6},
            "destino": {"codigo": "CS2", "ects": 4.5},
            "grupo": 1,
        },
    ]

    assert hay_aviso_ects(propuesta) is True

def test_obtener_seleccion_vacia():
    resultados = [{"grupo": None, "nombre": "Individual"}]

    assert obtener_seleccion(resultados, []) == []


def test_obtener_seleccion_combina_individual_y_grupo():
    resultados = [
        {"grupo": 1, "nombre": "Parte A"},
        {"grupo": None, "nombre": "Individual"},
        {"grupo": 1, "nombre": "Parte B"},
    ]

    assert obtener_seleccion(resultados, [0, 1]) == [
        resultados[0],
        resultados[2],
        resultados[1],
    ]


def test_seleccionar_dos_filas_del_grupo_no_lo_duplica():
    resultados = [
        {"grupo": 1, "nombre": "Parte A"},
        {"grupo": 1, "nombre": "Parte B"},
    ]

    assert obtener_seleccion(resultados, [0, 1]) == resultados   