from pydantic import BaseModel


class PreguntaEvaluacion(BaseModel):
    pregunta_id: int
    evaluacion_id: int
    numero_orden: int
    estado: bool = True