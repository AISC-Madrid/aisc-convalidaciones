from src.embeddings.texts import (
    construir_texto_destino,
    construir_texto_uc3m,
    limpiar_descripcion,
)


def test_elimina_referencia_cruzada():
    descripcion = "Physical realizations and experiments. Crosslisted with PHYS 4782 ."

    assert limpiar_descripcion(descripcion) == ("Physical realizations and experiments.")


def test_conserva_contenido_academico():
    descripcion = "ME Special Topics with lab component."

    assert limpiar_descripcion(descripcion) == descripcion


def test_descripcion_ausente():
    assert limpiar_descripcion(None) == ""
    assert limpiar_descripcion("") == ""


def test_texto_destino_con_descripcion():
    texto = construir_texto_destino(
        "Linear Elasticity",
        "Governing equations. Crosslisted with ME 6769.",
    )

    assert texto == "query: Linear Elasticity. Governing equations."


def test_texto_destino_sin_descripcion():
    texto = construir_texto_destino("Special Topics", None)

    assert texto == "query: Special Topics."


def test_texto_uc3m_con_ficha_completa():
    texto = construir_texto_uc3m(
        "Linear Algebra",
        "Understand vector spaces.",
        "Matrices. Linear transformations.",
    )

    assert texto == (
        "query: Linear Algebra. Understand vector spaces. Matrices. Linear transformations."
    )


def test_texto_uc3m_sin_objetivos():
    texto = construir_texto_uc3m(
        "Files and Databases",
        None,
        "Data models. Database systems.",
    )

    assert texto == "query: Files and Databases. Data models. Database systems."


def test_texto_uc3m_normaliza_campos_vacios_y_espacios():
    texto = construir_texto_uc3m("  Subject  ", "  ", "First\n\nsecond")

    assert texto == "query: Subject. First second."


def test_texto_uc3m_no_duplica_punto_del_nombre_y_los_campos():
    texto = construir_texto_uc3m(
        "Subject.",
        "Objective.",
        "Programme.",
    )

    assert texto == "query: Subject. Objective. Programme."


def test_texto_destino_anade_punto_final():
    texto = construir_texto_destino("Mechanics", "Stress and strain")

    assert texto == "query: Mechanics. Stress and strain."


def test_texto_destino_no_duplica_punto_del_nombre():
    texto = construir_texto_destino("Mechanics.", "Stress and strain.")

    assert texto == "query: Mechanics. Stress and strain."
