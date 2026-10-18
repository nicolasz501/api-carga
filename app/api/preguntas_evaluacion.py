from fastapi import APIRouter, HTTPException

from app.models.PreguntaEvaluacion import PreguntaEvaluacion
from app.repositories.pregunta_evaluacion_repository import PreguntaEvaluacionRepository

router = APIRouter(
    prefix="/preguntas-evaluacion",
    tags=["Preguntas por Evaluación"]
)

repo = PreguntaEvaluacionRepository()


@router.get("/")
def listar():
    return repo.obtener_todos()


@router.get("/evaluacion/{evaluacion_id}")
def listar_por_evaluacion(evaluacion_id: int):
    return repo.obtener_por_evaluacion(evaluacion_id)


@router.get("/{pregunta_evaluacion_id}")
def obtener(pregunta_evaluacion_id: int):
    item = repo.obtener_por_id(pregunta_evaluacion_id)
    if not item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return item


@router.post("/")
def crear(datos: PreguntaEvaluacion):
    try:
        nuevo_id = repo.crear(datos)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not nuevo_id:
        raise HTTPException(status_code=500, detail="No se pudo crear el registro")
    return {"mensaje": "Pregunta asignada a la evaluación", "id": nuevo_id}


@router.put("/{pregunta_evaluacion_id}")
def actualizar(pregunta_evaluacion_id: int, datos: PreguntaEvaluacion):
    try:
        exito = repo.actualizar(pregunta_evaluacion_id, datos)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not exito:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return {"mensaje": "Registro actualizado correctamente"}


@router.delete("/{pregunta_evaluacion_id}")
def eliminar(pregunta_evaluacion_id: int):
    try:
        exito = repo.eliminar(pregunta_evaluacion_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not exito:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return {"mensaje": "Registro eliminado correctamente"}