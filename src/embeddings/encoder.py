"""Codificación de textos con embeddings multilingües."""

from functools import lru_cache
from typing import Any

import numpy as np

MODEL_NAME = "intfloat/multilingual-e5-small"
EMBEDDING_DIMENSION = 384
CHUNK_SIZE = 400
QUERY_PREFIX = "query:"


@lru_cache(maxsize=1)
def _cargar_modelo() -> Any:
    """Carga el modelo una sola vez, únicamente cuando se solicita."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def _separar_prefijo(texto: str) -> tuple[str, str]:
    """Devuelve el prefijo E5 y el contenido sin prefijo duplicado."""
    texto = texto.strip()
    if texto.casefold().startswith(QUERY_PREFIX):
        return QUERY_PREFIX, texto[len(QUERY_PREFIX) :].lstrip()
    return QUERY_PREFIX, texto


def _limites_de_palabra(tokens: list[int], tokenizer: Any) -> set[int]:
    """Obtiene posiciones donde puede terminar un fragmento sin partir palabras."""
    convertir_tokens = getattr(tokenizer, "convert_ids_to_tokens", None)
    if not callable(convertir_tokens):
        return set(range(len(tokens) + 1))

    tokens_texto = convertir_tokens(tokens)
    return {
        posicion
        for posicion, token in enumerate(tokens_texto)
        if posicion == 0 or token.startswith(("▁", "Ġ"))
    } | {len(tokens)}


def _trocear_texto(texto: str, tokenizer: Any) -> list[str]:
    """Divide un texto en fragmentos de unos 400 tokens conservando ``query:``."""
    prefijo, contenido = _separar_prefijo(texto)
    prefijo_tokens = tokenizer.encode(prefijo, add_special_tokens=False)
    tokens_por_fragmento = max(1, CHUNK_SIZE - len(prefijo_tokens))
    tokens = tokenizer.encode(contenido, add_special_tokens=False)
    limites = _limites_de_palabra(tokens, tokenizer)

    if not tokens:
        return [prefijo]

    fragmentos = []
    inicio = 0
    while inicio < len(tokens):
        fin = min(inicio + tokens_por_fragmento, len(tokens))
        while fin < len(tokens) and fin not in limites:
            fin += 1
        contenido_fragmento = tokenizer.decode(
            tokens[inicio:fin],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        ).strip()
        fragmentos.append(f"{prefijo} {contenido_fragmento}".strip())
        inicio = fin

    return fragmentos


def _normalizar_l2(vector: np.ndarray) -> np.ndarray:
    """Normaliza un vector con su norma L2 y rechaza vectores nulos."""
    norma = np.linalg.norm(vector)
    if norma == 0:
        raise ValueError("No se puede normalizar un embedding de norma cero.")
    return (vector / norma).astype(np.float32)


def encode_textos(textos: list[str], *, modelo: Any | None = None) -> np.ndarray:
    """Codifica textos en una matriz float32 de embeddings normalizados.

    Los textos se dividen en fragmentos de aproximadamente 400 tokens. Se
    calcula la media de los embeddings de cada texto y se normaliza el vector
    resultante con L2. Un texto vacío se representa mediante el embedding de
    ``query:``. El parámetro opcional ``modelo`` permite inyectar un modelo
    simulado en tests; si no se proporciona, se reutiliza el modelo real en
    caché.
    """
    if not textos:
        return np.empty((0, EMBEDDING_DIMENSION), dtype=np.float32)

    if modelo is None:
        modelo = _cargar_modelo()
    fragmentos_por_texto = [
        _trocear_texto(texto, modelo.tokenizer) for texto in textos
    ]
    fragmentos = [fragmento for grupo in fragmentos_por_texto for fragmento in grupo]
    embeddings = np.asarray(
        modelo.encode(
            fragmentos,
            normalize_embeddings=False,
            convert_to_numpy=True,
        ),
        dtype=np.float32,
    )

    if embeddings.ndim != 2 or embeddings.shape[1] != EMBEDDING_DIMENSION:
        raise ValueError(
            f"El modelo debe devolver embeddings de dimensión {EMBEDDING_DIMENSION}."
        )
    if embeddings.shape[0] != len(fragmentos):
        raise ValueError(
            "El modelo devolvió un número de embeddings distinto al de fragmentos."
        )
    if not np.isfinite(embeddings).all():
        raise ValueError("Los embeddings deben contener únicamente valores finitos.")

    resultados = []
    inicio = 0
    for fragmentos_texto in fragmentos_por_texto:
        fin = inicio + len(fragmentos_texto)
        media = embeddings[inicio:fin].mean(axis=0)
        resultados.append(_normalizar_l2(media))
        inicio = fin

    return np.vstack(resultados).astype(np.float32, copy=False)
