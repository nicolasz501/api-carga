
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.models.Evaluacion import Evaluacion
from app.repositories.evaluacion_repository import EvaluacionRepository
from app.api.usuarios import (
    UsuarioActual,
    get_usuario_actual,
    requiere_jefe,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/evaluaciones",
    tags=["Gestión de Evaluaciones"],
)

repo = EvaluacionRepository()


class AsignacionEvaluacion(BaseModel):
    carga_id: int = Field(gt=0)


@router.get("/mis-evaluaciones")
def mis_evaluaciones(
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    try:
        return repo.obtener_para_docente(usuario.usuario_id)

    except Exception:
        logger.exception("Error consultando evaluaciones del docente")
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar tus evaluaciones.",
        )


@router.get("/")
def listar_evaluaciones(
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    try:
        return repo.obtener_todos()

    except Exception:
        logger.exception("Error consultando evaluaciones")
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar las evaluaciones.",
        )


@router.get("/{evaluacion_id}")
def obtener_evaluacion(
    evaluacion_id: int,
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    try:
        evaluacion = repo.obtener_por_id(evaluacion_id)

        if evaluacion is None:
            raise HTTPException(
                status_code=404,
                detail="Evaluación no encontrada.",
            )

        return evaluacion

    except HTTPException:
        raise

    except Exception:
        logger.exception("Error consultando evaluación")
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar la evaluación.",
        )


@router.post("/")
def crear_evaluacion(
    evaluacion: Evaluacion,
    _jefe: UsuarioActual = Depends(requiere_jefe),
):
    try:
        nuevo_id = repo.crear(evaluacion)

        if nuevo_id is None:
            raise HTTPException(
                status_code=500,
                detail="No fue posible registrar la evaluación.",
            )

        return {
            "mensaje": "Evaluación registrada correctamente.",
            "evaluacion_id": nuevo_id,
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Error creando evaluación")
        raise HTTPException(
            status_code=500,
            detail="No fue posible registrar la evaluación.",
        )


@router.put("/{evaluacion_id}/asignar")
def asignar_evaluacion(
    evaluacion_id: int,
    asignacion: AsignacionEvaluacion,
    _jefe: UsuarioActual = Depends(requiere_jefe),
):
    try:
        if repo.obtener_por_id(evaluacion_id) is None:
            raise HTTPException(
                status_code=404,
                detail="Evaluación no encontrada.",
            )

        if not repo.asignar_carga(
            evaluacion_id,
            asignacion.carga_id,
        ):
            raise HTTPException(
                status_code=404,
                detail="Carga docente no encontrada o inactiva.",
            )

        return {
            "mensaje": "Evaluación asignada correctamente.",
            "evaluacion_id": evaluacion_id,
            "carga_id": asignacion.carga_id,
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Error asignando evaluación")
        raise HTTPException(
            status_code=500,
            detail="No fue posible asignar la evaluación.",
        )


@router.put("/{evaluacion_id}")
def actualizar_evaluacion(
    evaluacion_id: int,
    evaluacion: Evaluacion,
    _jefe: UsuarioActual = Depends(requiere_jefe),
):
    try:
        if not repo.actualizar(evaluacion_id, evaluacion):
            raise HTTPException(
                status_code=404,
                detail="Evaluación no encontrada.",
            )

        return {
            "mensaje": "Evaluación actualizada correctamente.",
            "evaluacion_id": evaluacion_id,
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Error actualizando evaluación")
        raise HTTPException(
            status_code=500,
            detail="No fue posible actualizar la evaluación.",
        )


@router.delete("/{evaluacion_id}")
def eliminar_evaluacion(
    evaluacion_id: int,
    _jefe: UsuarioActual = Depends(requiere_jefe),
):
    try:
        if not repo.eliminar(evaluacion_id):
            raise HTTPException(
                status_code=404,
                detail="Evaluación no encontrada.",
            )

        return {
            "mensaje": "Evaluación eliminada correctamente.",
            "evaluacion_id": evaluacion_id,
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Error eliminando evaluación")
        raise HTTPException(
            status_code=500,
            detail=(
                "No fue posible eliminar la evaluación. "
                "Puede tener preguntas o respuestas relacionadas."
            ),
        )
