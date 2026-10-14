from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from src.models.subject import Subject

LIMITE_AVISO_ECTS = 0.25


def ects_dispares(origen: float, destino: float) -> bool:
    return abs(destino - origen) / origen > LIMITE_AVISO_ECTS


class Match(BaseModel):
    """Un resultado: asignatura UC3M frente a la asignatura del destino que la convalidaría."""

    origen: Subject
    destino: Subject
    score: float = Field(ge=0, le=1)
    etiqueta: Literal["PRECEDENTE_APROBADO", "SUGERENCIA_IA"]
    aviso_ects: bool
    # Mismo número en las filas de una convalidación n:m del histórico.
    grupo: int | None = None

    @model_validator(mode="after")
    def aviso_coherente(self):
        if self.aviso_ects != ects_dispares(self.origen.ects, self.destino.ects):
            raise ValueError("aviso_ects no coincide con la diferencia de ECTS (> 25 %)")
        return self


class Resultados(BaseModel):
    """Un fichero public/data/<grado>__<uni>.json completo."""

    grado: str
    universidad: str
    generado: date
    modelo: str
    umbral: float = Field(ge=0, le=1)
    resultados: list[Match]
