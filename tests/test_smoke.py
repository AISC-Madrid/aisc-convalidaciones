"""Test trivial: comprueba que el paquete se importa y que la CI funciona.

Cuando añadas tu primera tarea, crea su fichero de tests al lado (tests/test_<modulo>.py).
"""

import src


def test_el_paquete_se_importa():
    assert src is not None
