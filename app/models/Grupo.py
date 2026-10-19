
from typing import Optional
from pydantic import BaseModel, Field


class Grupo(BaseModel):
    grupos_id: Optional[int] = None
    asignaturas_id: int = Field(..., gt=0)
    nombre_grupos: str = Field(..., min_length=1, max_length=50)
    capacidad: int = Field(default=30, gt=0)
    estado: bool = True
