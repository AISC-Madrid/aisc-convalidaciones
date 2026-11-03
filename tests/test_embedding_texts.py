from src.embeddings.texts import construir_texto_destino, limpiar_descripcion


def test_elimina_referencia_cruzada():
    descripcion = (
        "Physical realizations and experiments. "
        "Crosslisted with PHYS 4782 ."
    )

    assert limpiar_descripcion(descripcion) == (
        "Physical realizations and experiments."
    )


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

    assert texto == "query: Special Topics"