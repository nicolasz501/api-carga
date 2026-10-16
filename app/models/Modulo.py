from pydantic import BaseModel
from typing import Optional



class Modulo(BaseModel):
    modulos_id: Optional[int] = None
    nombre_modulo: str
    estado: bool = True
    