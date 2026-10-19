from typing import Optional
from pydantic import BaseModel, Field


class Respuesta(BaseModel):
    pregunta_evaluacion_id: int = Field(gt=0)
    pregunta_id: int = Field(gt=0)
    usuario_id: Optional[int] = None
    puntaje: int = Field(ge=1, le=5)
    comentario: Optional[str] = None
    estado: bool = True