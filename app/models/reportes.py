from pydantic import BaseModel
from datetime import date
from typing import Optional


class FiltrosReporte(BaseModel):
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    programa: Optional[str] = None
    apellido: Optional[str] = None
    tipo_evaluacion: Optional[str] = None