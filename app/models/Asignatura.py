from pydantic import BaseModel
from typing import Optional



class Asignatura(BaseModel):
    asignatura_id: Optional[int] = None
    programa_id: int
    codigo_asignatura: str
    nombres_asignaturas: str
    creditos: int
    estado: bool = True
    