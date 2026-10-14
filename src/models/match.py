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
        # En las n:m el aviso compara los totales del grupo; lo comprueba Resultados.
        if self.grupo is None and self.aviso_ects != ects_dispares(
            self.origen.ects, self.destino.ects
        ):
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

    @model_validator(mode="after")
    def aviso_coherente_en_grupos(self):
        grupos: dict[int, list[Match]] = {}
        for m in self.resultados:
            if m.grupo is not None:
                grupos.setdefault(m.grupo, []).append(m)
        for grupo, filas in grupos.items():
            origen = sum({m.origen.codigo: m.origen.ects for m in filas}.values())
            destino = sum({m.destino.codigo: m.destino.ects for m in filas}.values())
            if any(m.aviso_ects != ects_dispares(origen, destino) for m in filas):
                raise ValueError(
                    f"grupo {grupo}: aviso_ects no coincide con la diferencia de ECTS "
                    "entre los totales del grupo (> 25 %)"
                )
        return self
