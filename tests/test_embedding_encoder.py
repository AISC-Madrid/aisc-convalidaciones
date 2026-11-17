import numpy as np
import pytest

from src.embeddings.encoder import encode_textos


class TokenizerSimulado:
    def encode(self, texto, add_special_tokens=False):
        return texto.split()

    def decode(
        self,
        tokens,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=True,
    ):
        return " ".join(tokens)


class ModeloSimulado:
    tokenizer = TokenizerSimulado()

    def __init__(self):
        self.textos = []

    def encode(self, textos, normalize_embeddings=False, convert_to_numpy=True):
        self.textos.extend(textos)
        embeddings = []
        for texto in textos:
            numero_tokens = len(texto.split())
            vector = np.zeros(384, dtype=np.float32)
            vector[0] = numero_tokens
            vector[1] = sum(ord(caracter) for caracter in texto) % 1000
            embeddings.append(vector)
        return np.asarray(embeddings, dtype=np.float32)


class ModeloNulo(ModeloSimulado):
    def encode(self, textos, normalize_embeddings=False, convert_to_numpy=True):
        self.textos.extend(textos)
        return np.zeros((len(textos), 384), dtype=np.float32)


class ModeloConNumeroIncorrecto(ModeloSimulado):
    def encode(self, textos, normalize_embeddings=False, convert_to_numpy=True):
        self.textos.extend(textos)
        return np.zeros((len(textos) - 1, 384), dtype=np.float32)


class ModeloConValoresNoFinitos(ModeloSimulado):
    def encode(self, textos, normalize_embeddings=False, convert_to_numpy=True):
        self.textos.extend(textos)
        embeddings = np.ones((len(textos), 384), dtype=np.float32)
        embeddings[0, 0] = np.nan
        return embeddings


def test_textos_identicos_generan_embeddings_identicos():
    modelo = ModeloSimulado()

    embeddings = encode_textos(
        ["query: Algebra lineal", "query: Algebra lineal"],
        modelo=modelo,
    )

    np.testing.assert_array_equal(embeddings[0], embeddings[1])
    assert np.dot(embeddings[0], embeddings[1]) == pytest.approx(1.0)


def test_devuelve_matriz_float32_de_384_dimensiones():
    embeddings = encode_textos(["query: Algebra lineal"], modelo=ModeloSimulado())

    assert embeddings.shape == (1, 384)
    assert embeddings.dtype == np.float32


def test_lista_vacia_devuelve_matriz_vacia_sin_cargar_modelo():
    embeddings = encode_textos([])

    assert embeddings.shape == (0, 384)
    assert embeddings.dtype == np.float32


def test_texto_largo_se_divide_sin_perder_tokens():
    modelo = ModeloSimulado()
    tokens = [f"token-{indice}" for indice in range(801)]

    encode_textos(["query: " + " ".join(tokens)], modelo=modelo)

    assert len(modelo.textos) == 3
    tokens_recibidos = [
        token
        for fragmento in modelo.textos
        for token in fragmento.split()
        if token != "query:"
    ]
    assert tokens_recibidos == tokens


def test_cada_fragmento_conserva_un_unico_prefijo_query():
    modelo = ModeloSimulado()

    encode_textos(["query: " + " ".join(f"token-{i}" for i in range(801))], modelo=modelo)

    assert all(fragmento.startswith("query: ") for fragmento in modelo.textos)
    assert all(fragmento.count("query:") == 1 for fragmento in modelo.textos)


def test_calcula_la_media_de_los_fragmentos_antes_de_normalizar():
    class ModeloMedia(ModeloSimulado):
        def encode(self, textos, normalize_embeddings=False, convert_to_numpy=True):
            self.textos.extend(textos)
            embeddings = []
            for texto in textos:
                vector = np.zeros(384, dtype=np.float32)
                if len(texto.split()) == 400:
                    vector[0] = 3
                else:
                    vector[1] = 4
                embeddings.append(vector)
            return np.asarray(embeddings, dtype=np.float32)

    modelo = ModeloMedia()
    texto = "query: " + " ".join(f"token-{indice}" for indice in range(500))

    resultado = encode_textos([texto], modelo=modelo)[0]
    media = np.array([1.5, 2.0], dtype=np.float32)
    esperado = media / np.linalg.norm(media)

    np.testing.assert_allclose(resultado[:2], esperado)


def test_normaliza_con_l2_los_vectores_finales():
    embeddings = encode_textos(
        ["query: uno", "query: dos tres"],
        modelo=ModeloSimulado(),
    )

    np.testing.assert_allclose(np.linalg.norm(embeddings, axis=1), [1.0, 1.0])


def test_texto_vacio_se_codifica_como_query():
    modelo = ModeloSimulado()

    resultado = encode_textos([""], modelo=modelo)

    assert modelo.textos == ["query:"]
    assert resultado.shape == (1, 384)
    assert np.linalg.norm(resultado[0]) == pytest.approx(1.0)


def test_rechaza_embeddings_de_norma_cero():
    with pytest.raises(ValueError, match="norma cero"):
        encode_textos(["query: texto"], modelo=ModeloNulo())


def test_rechaza_numero_de_embeddings_distinto_al_de_fragmentos():
    with pytest.raises(ValueError, match="número de embeddings distinto"):
        encode_textos(["query: texto"], modelo=ModeloConNumeroIncorrecto())


@pytest.mark.parametrize("valor", [np.nan, np.inf, -np.inf])
def test_rechaza_embeddings_con_valores_no_finitos(valor):
    class ModeloNoFinito(ModeloSimulado):
        def encode(self, textos, normalize_embeddings=False, convert_to_numpy=True):
            self.textos.extend(textos)
            embeddings = np.ones((len(textos), 384), dtype=np.float32)
            embeddings[0, 0] = valor
            return embeddings

    with pytest.raises(ValueError, match="valores finitos"):
        encode_textos(["query: texto"], modelo=ModeloNoFinito())


def test_trocea_con_el_tokenizador_real_sin_truncar():
    transformers = pytest.importorskip("transformers")
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        "intfloat/multilingual-e5-small"
    )
    from src.embeddings.encoder import CHUNK_SIZE, _trocear_texto

    contenido = " ".join(
        (
            "Árboles, grafos y programación dinámica: "
            "caracterización electroencefalográfica y "
            "supercalifragilisticoespialidoso."
        )
        for _ in range(160)
    )
    texto = f"query: {contenido}"
    fragmentos = _trocear_texto(texto, tokenizer)

    tokens_contenido = tokenizer.encode(contenido, add_special_tokens=False)
    tokens_prefijo = tokenizer.encode("query:", add_special_tokens=False)
    tokens_por_fragmento = CHUNK_SIZE - len(tokens_prefijo)
    fragmentos_esperados = (
        len(tokens_contenido) + tokens_por_fragmento - 1
    ) // tokens_por_fragmento

    assert len(tokens_contenido) > 512
    assert len(fragmentos) == fragmentos_esperados
    assert all(
        len(tokenizer.encode(fragmento, add_special_tokens=False)) <= 512
        for fragmento in fragmentos
    )
    assert all(fragmento.startswith("query:") for fragmento in fragmentos)

    tokens_reconstruidos = []
    for fragmento in fragmentos:
        cuerpo = fragmento[len("query: "):]
        tokens_reconstruidos.extend(
            tokenizer.encode(cuerpo, add_special_tokens=False)
        )

    assert tokens_reconstruidos == tokens_contenido
