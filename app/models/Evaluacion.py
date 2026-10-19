from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Evaluacion(BaseModel):
    evaluacion_id: Optional[int] = None
    carga_id: int
    periodo_id: Optional[int] = None
    tipo_evaluacion: str
    titulo: Optional[str] = None
    fecha_envio: Optional[datetime] = None
    estado: bool = True