"""Preparación de los textos que recibirá el modelo de embeddings."""

import re


def limpiar_descripcion(descripcion: str | None) -> str:
    """Elimina referencias de catálogo del tipo 'Crosslisted with ... .'."""
    if descripcion is None:
        return ""

    patron = r"\bCrosslisted with\s+[^.]+\."
    texto = re.sub(patron, "", descripcion, flags=re.IGNORECASE)

    return " ".join(texto.split())


def construir_texto_uc3m(
    nombre: str,
    objetivos: str | None,
    programa: str | None,
) -> str:
    """Combina nombre, objetivos y programa de una ficha UC3M."""
    partes = [nombre.strip()]
    for campo in (objetivos, programa):
        texto = " ".join((campo or "").split())
        if texto:
            partes.append(texto)

    texto = f"query: {partes[0]}"
    for parte in partes[1:]:
        separador = " " if texto.endswith(".") else ". "
        texto += f"{separador}{parte}"

    return texto if texto.endswith(".") else f"{texto}."

def construir_texto_destino(nombre: str, descripcion: str | None) -> str:
    """Combina el nombre y la descripción limpia para el modelo."""
    nombre_limpio = nombre.strip()
    descripcion_limpia = limpiar_descripcion(descripcion)

    partes = [nombre_limpio]

    if descripcion_limpia:
        partes.append(descripcion_limpia)

    return f"query: {'. '.join(partes)}" 