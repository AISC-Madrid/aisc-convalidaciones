import numpy as np
import pytest

from src.embeddings.index import buscar_top_k


def test_top_k_devuelve_los_vectores_correctos_en_orden():
    consulta = [1, 0]
    catalogo = [
        [0, 1],
        [0.8, 0.6],
        [1, 0],
    ]

    posiciones, puntuaciones = buscar_top_k(consulta, catalogo, k=2)

    assert posiciones.tolist() == [2, 1]
    np.testing.assert_allclose(puntuaciones, [1.0, 0.8])


def test_k_mayor_que_catalogo_devuelve_todos():
    posiciones, puntuaciones = buscar_top_k(
        consulta=[1, 0],
        vectores=[[0, 1], [1, 0]],
        k=5,
    )

    assert posiciones.tolist() == [1, 0]
    np.testing.assert_allclose(puntuaciones, [1.0, 0.0])


def test_rechaza_dimensiones_incompatibles():
    with pytest.raises(ValueError, match="dimensiones"):
        buscar_top_k(
            consulta=[1, 0],
            vectores=[[1, 0, 0]],
            k=1,
        )


@pytest.mark.parametrize("k", [0, -1, 1.5, True])
def test_rechaza_k_invalido(k):
    with pytest.raises(ValueError, match="entero positivo"):
        buscar_top_k(
            consulta=[1, 0],
            vectores=[[1, 0]],
            k=k,
        )


def test_acepta_k_entero_numpy():
    posiciones, puntuaciones = buscar_top_k(
        consulta=[1, 0],
        vectores=[[0, 1], [1, 0]],
        k=np.int64(1),
    )

    assert posiciones.tolist() == [1]
    np.testing.assert_allclose(puntuaciones, [1.0])
