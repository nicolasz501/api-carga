from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.Evaluacion import Evaluacion
from app.repositories.evaluacion_repository import EvaluacionRepository


router = APIRouter(
    prefix="/evaluaciones",
    tags=["Gestión de Evaluaciones"]
)

repo = EvaluacionRepository()


class AsignacionEvaluacion(BaseModel):
    carga_id: int = Field(gt=0)


@router.get("/")
def listar_evaluaciones():
    return repo.obtener_todos()


@router.get("/docente/{usuario_id}")
def listar_evaluaciones_docente(usuario_id: int):
    if usuario_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="El identificador del usuario no es válido."
        )

    try:
        return repo.obtener_para_docente(usuario_id)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar las evaluaciones pendientes."
        )


@router.get("/{evaluacion_id}")
def obtener_evaluacion(evaluacion_id: int):
    evaluacion = repo.obtener_por_id(evaluacion_id)

    if not evaluacion:
        raise HTTPException(
            status_code=404,
            detail="Evaluación no encontrada."
        )

    return evaluacion


@router.post("/")
def crear_evaluacion(evaluacion: Evaluacion):
    nuevo_id = repo.crear(evaluacion)

    if nuevo_id is None:
        raise HTTPException(
            status_code=500,
            detail="No fue posible registrar la evaluación."
        )

    return {
        "mensaje": "Evaluación registrada exitosamente.",
        "id": nuevo_id
    }


@router.put("/{evaluacion_id}/asignar")
def asignar_evaluacion(
    evaluacion_id: int,
    asignacion: AsignacionEvaluacion
):
    if not repo.obtener_por_id(evaluacion_id):
        raise HTTPException(
            status_code=404,
            detail="Evaluación no encontrada."
        )

    try:
        exito = repo.asignar_carga(
            evaluacion_id,
            asignacion.carga_id
        )

        if not exito:
            raise HTTPException(
                status_code=404,
                detail="No se encontró la carga docente indicada."
            )

        return {
            "mensaje": "Evaluación asignada correctamente.",
            "evaluacion_id": evaluacion_id,
            "carga_id": asignacion.carga_id
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="No fue posible asignar la evaluación."
        )


@router.put("/{evaluacion_id}")
def actualizar_evaluacion(
    evaluacion_id: int,
    evaluacion: Evaluacion
):
    exito = repo.actualizar(evaluacion_id, evaluacion)

    if not exito:
        raise HTTPException(
            status_code=404,
            detail="Evaluación no encontrada."
        )

    return {"mensaje": "Evaluación actualizada correctamente."}


@router.delete("/{evaluacion_id}")
def eliminar_evaluacion(evaluacion_id: int):
    exito = repo.eliminar(evaluacion_id)

    if not exito:
        raise HTTPException(
            status_code=404,
            detail="Evaluación no encontrada."
        )

    return {"mensaje": "Evaluación eliminada correctamente."}