from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Grupo(BaseModel):
    grupos_id: Optional[int] = None
    asignaturas_id: int
    periodos_id: int
    nombre_grupos: str
    capacidad: int
    estado: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None