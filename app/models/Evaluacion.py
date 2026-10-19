from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Evaluacion(BaseModel):

    evaluacion_id: Optional[int] = None
    carga_id: int
    tipo_evaluacion: str
    titulo: str  # NOT NULL en la base de datos
    fecha_envio: Optional[datetime] = None
    estado: bool = True