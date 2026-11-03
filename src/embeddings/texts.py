"""Preparación de los textos que recibirá el modelo de embeddings."""

import re


def limpiar_descripcion(descripcion: str | None) -> str:
    """Elimina referencias de catálogo del tipo 'Crosslisted with ... .'."""
    if descripcion is None:
        return ""

    patron = r"\bCrosslisted with\s+[^.]+\."
    texto = re.sub(patron, "", descripcion, flags=re.IGNORECASE)

    return " ".join(texto.split()) 

def construir_texto_destino(nombre: str, descripcion: str | None) -> str:
    """Combina el nombre y la descripción limpia para el modelo."""
    nombre_limpio = nombre.strip()
    descripcion_limpia = limpiar_descripcion(descripcion)

    partes = [nombre_limpio]

    if descripcion_limpia:
        partes.append(descripcion_limpia)

    return f"query: {'. '.join(partes)}" 