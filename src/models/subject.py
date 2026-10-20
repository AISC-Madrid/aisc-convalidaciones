from typing import Literal

from pydantic import BaseModel, Field

Tipo = Literal["FB", "OB", "OP", "HUM"]


class Subject(BaseModel):
    """Asignatura tal como aparece en el JSON publicado (lado UC3M o lado destino)."""

    codigo: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    ects: float = Field(gt=0)
    tipo: Tipo | None = None
    url: str | None = None
