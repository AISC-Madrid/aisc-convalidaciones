from pydantic import BaseModel, Field


class HistoricalMatch(BaseModel):
    """Una fila de los Excel de convalidaciones MNE ya aprobadas."""

    curso_academico: str = Field(pattern=r"^\d{4}-\d{4}$")
    pais: str
    universidad: str
    grado: str
    uc3m_codigo: str = Field(min_length=1)
    uc3m_nombre: str
    ects: float = Field(gt=0)
    curso: int | None = None
    tipo: str | None = None  # Carácter de la asignatura UC3M: FB, OB, OP...
    # 304 filas del histórico no tienen código destino: se enlazan por nombre.
    destino_codigo: str | None = None
    destino_nombre: str
    # Lo asigna el loader (2A) a las convalidaciones n:m.
    group_id: int | None = None
