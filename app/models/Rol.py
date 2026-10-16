from pydantic import BaseModel
from typing import Optional


class Rol(BaseModel):
    rol_id: Optional[int] = None
    nombre_rol: str
    estado: bool = True
