from pydantic import BaseModel, Field
from typing import Optional, List

# 1. Modelo para cada pregunta respondida individualmente
class RespuestaItem(BaseModel):
    pregunta_evaluacion_id: int
    pregunta_id: int
    puntaje: int = Field(ge=1, le=5)

# 2. Modelo contenedor principal para la ruta /respuestas/lote
class LoteRespuestasSchema(BaseModel):
    usuario_id: int
    evaluacion_id: int
    comentario: Optional[str] = Field(default=None, max_length=500)
    estado: bool = True
    respuestas: List[RespuestaItem]