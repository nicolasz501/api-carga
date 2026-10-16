from pydantic import BaseModel
from typing import Optional



class ModuloRol(BaseModel):
    modules_rol_id: Optional[int] = None
    role_id: int
    module_id: int
    puede_ver: bool
    puede_crear: bool = False
    puede_editar: bool = False
    puede_eliminar: bool = False
    estado: bool = True
    
    