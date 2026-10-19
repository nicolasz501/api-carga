
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.Evaluacion import Evaluacion
from app.repositories.evaluacion_repository import EvaluacionRepository


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/evaluaciones",
    tags=["Gestión de Evaluaciones"]
)

repo = EvaluacionRepository()


class AsignacionEvaluacion(BaseModel):
    carga_id: int = Field(gt=0)


class AsignacionMasiva(BaseModel):
    plantilla_evaluacion_id: int = Field(gt=0)


@router.get("/")
def listar_evaluaciones():
    try:
        return repo.obtener_todos()
    except Exception:
        logger.exception("Error al listar evaluaciones")
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar las evaluaciones."
        )


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
        logger.exception(
            "Error consultando evaluaciones del docente usuario_id=%s",
            usuario_id
        )
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar las evaluaciones pendientes."
        )


@router.post("/asignar-todos")
def asignar_autoevaluacion_todos(
    solicitud: AsignacionMasiva
):
    try:
        resultado = repo.asignar_autoevaluacion_a_todos(
            solicitud.plantilla_evaluacion_id
        )
        return resultado

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception:
        logger.exception(
            "Error al asignar autoevaluaciones a todos los docentes"
        )
        raise HTTPException(
            status_code=500,
            detail="No fue posible asignar las autoevaluaciones."
        )


@router.get("/{evaluacion_id}")
def obtener_evaluacion(evaluacion_id: int):
    try:
        evaluacion = repo.obtener_por_id(evaluacion_id)

        if not evaluacion:
            raise HTTPException(
                status_code=404,
                detail="Evaluación no encontrada."
            )

        return evaluacion

    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Error al consultar evaluacion_id=%s",
            evaluacion_id
        )
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar la evaluación."
        )


@router.post("/")
def crear_evaluacion(evaluacion: Evaluacion):
    try:
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

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error al crear una evaluación")
        raise HTTPException(
            status_code=500,
            detail="No fue posible registrar la evaluación."
        )


@router.put("/{evaluacion_id}/asignar")
def asignar_evaluacion(
    evaluacion_id: int,
    asignacion: AsignacionEvaluacion
):
    try:
        evaluacion = repo.obtener_por_id(evaluacion_id)

        if not evaluacion:
            raise HTTPException(
                status_code=404,
                detail="Evaluación no encontrada."
            )

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
        logger.exception(
            "Error asignando evaluacion_id=%s a carga_id=%s",
            evaluacion_id,
            asignacion.carga_id
        )
        raise HTTPException(
            status_code=500,
            detail="No fue posible asignar la evaluación."
        )


@router.put("/{evaluacion_id}")
def actualizar_evaluacion(
    evaluacion_id: int,
    evaluacion: Evaluacion
):
    try:
        exito = repo.actualizar(evaluacion_id, evaluacion)

        if not exito:
            raise HTTPException(
                status_code=404,
                detail="Evaluación no encontrada."
            )

        return {
            "mensaje": "Evaluación actualizada correctamente."
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Error al actualizar evaluacion_id=%s",
            evaluacion_id
        )
        raise HTTPException(
            status_code=500,
            detail="No fue posible actualizar la evaluación."
        )


@router.delete("/{evaluacion_id}")
def eliminar_evaluacion(evaluacion_id: int):
    try:
        exito = repo.eliminar(evaluacion_id)

        if not exito:
            raise HTTPException(
                status_code=404,
                detail="Evaluación no encontrada."
            )

        return {
            "mensaje": "Evaluación eliminada correctamente."
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Error al eliminar evaluacion_id=%s",
            evaluacion_id
        )
        raise HTTPException(
            status_code=500,
            detail="No fue posible eliminar la evaluación."
        )
