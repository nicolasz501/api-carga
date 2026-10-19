import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.models.Evaluacion import Evaluacion
from app.repositories.evaluacion_repository import EvaluacionRepository
from app.api.usuarios import (
    UsuarioActual,
    es_administrador,
    get_usuario_actual,
    requiere_jefe,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluaciones", tags=["Gestión de Evaluaciones"])
repo = EvaluacionRepository()


class AsignacionEvaluacion(BaseModel):
    carga_id: int = Field(gt=0)


class AsignacionMasiva(BaseModel):
    plantilla_evaluacion_id: int = Field(gt=0)


class EstadoPlantilla(BaseModel):
    estado: bool


@router.get("/mis-evaluaciones")
def mis_evaluaciones(usuario: UsuarioActual = Depends(get_usuario_actual)):
    try:
        return repo.obtener_para_docente(usuario.usuario_id)
    except Exception:
        logger.exception("Error consultando autoevaluaciones del usuario %s", usuario.usuario_id)
        raise HTTPException(status_code=500, detail="No fue posible consultar las evaluaciones pendientes.")


@router.get("/plantillas-autoevaluacion")
def listar_plantillas_autoevaluacion(_jefe: UsuarioActual = Depends(requiere_jefe)):
    try:
        return repo.listar_plantillas_autoevaluacion()
    except Exception:
        logger.exception("Error listando plantillas de autoevaluación")
        raise HTTPException(status_code=500, detail="No fue posible consultar las plantillas.")


@router.put("/{evaluacion_id}/estado")
def cambiar_estado_autoevaluacion(
    evaluacion_id: int,
    solicitud: EstadoPlantilla,
    _jefe: UsuarioActual = Depends(requiere_jefe),
):
    try:
        resultado = repo.cambiar_estado_plantilla(evaluacion_id, solicitud.estado)
        if not resultado:
            raise HTTPException(status_code=404, detail="No se encontró la plantilla de autoevaluación.")
        return {
            "mensaje": "Autoevaluación habilitada correctamente." if solicitud.estado else "Autoevaluación deshabilitada correctamente.",
            "evaluacion_id": resultado["evaluacion_id"],
            "estado": resultado["estado"],
            "periodo_id": resultado["periodo_id"],
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error cambiando estado de plantilla %s", evaluacion_id)
        raise HTTPException(status_code=500, detail="No fue posible cambiar el estado de la autoevaluación.")


@router.get("/")
def listar_evaluaciones(_jefe: UsuarioActual = Depends(requiere_jefe)):
    try:
        return repo.obtener_todos()
    except Exception:
        logger.exception("Error al listar evaluaciones")
        raise HTTPException(status_code=500, detail="No fue posible consultar las evaluaciones.")


@router.post("/")
def crear_evaluacion(evaluacion: Evaluacion, _jefe: UsuarioActual = Depends(requiere_jefe)):
    try:
        nuevo_id = repo.crear(evaluacion)
        if nuevo_id is None:
            raise HTTPException(status_code=500, detail="No fue posible registrar la evaluación.")
        return {"mensaje": "Evaluación registrada exitosamente.", "id": nuevo_id}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error al crear una evaluación")
        raise HTTPException(status_code=500, detail="No fue posible registrar la evaluación.")


@router.get("/{evaluacion_id}")
def obtener_evaluacion(evaluacion_id: int, usuario: UsuarioActual = Depends(get_usuario_actual)):
    try:
        evaluacion = repo.obtener_por_id(evaluacion_id)
        if not evaluacion or (
            not es_administrador(usuario.rol)
            and not repo.pertenece_a_docente(evaluacion_id, usuario.usuario_id)
        ):
            raise HTTPException(status_code=404, detail="Evaluación no encontrada.")
        return evaluacion
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error consultando evaluación %s", evaluacion_id)
        raise HTTPException(status_code=500, detail="No fue posible consultar la evaluación.")


@router.put("/{evaluacion_id}/asignar")
def asignar_evaluacion(
    evaluacion_id: int,
    asignacion: AsignacionEvaluacion,
    _jefe: UsuarioActual = Depends(requiere_jefe),
):
    try:
        if not repo.obtener_por_id(evaluacion_id):
            raise HTTPException(status_code=404, detail="Evaluación no encontrada.")
        if not repo.asignar_carga(evaluacion_id, asignacion.carga_id):
            raise HTTPException(status_code=404, detail="No se encontró la carga docente indicada.")
        return {"mensaje": "Evaluación asignada correctamente.", "evaluacion_id": evaluacion_id, "carga_id": asignacion.carga_id}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error asignando evaluación %s a carga %s", evaluacion_id, asignacion.carga_id)
        raise HTTPException(status_code=500, detail="No fue posible asignar la evaluación.")


@router.put("/{evaluacion_id}")
def actualizar_evaluacion(
    evaluacion_id: int,
    evaluacion: Evaluacion,
    _jefe: UsuarioActual = Depends(requiere_jefe),
):
    try:
        if not repo.actualizar(evaluacion_id, evaluacion):
            raise HTTPException(status_code=404, detail="Evaluación no encontrada.")
        return {"mensaje": "Evaluación actualizada correctamente."}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error actualizando evaluación %s", evaluacion_id)
        raise HTTPException(status_code=500, detail="No fue posible actualizar la evaluación.")


@router.delete("/{evaluacion_id}")
def eliminar_evaluacion(evaluacion_id: int, _jefe: UsuarioActual = Depends(requiere_jefe)):
    try:
        if not repo.eliminar(evaluacion_id):
            raise HTTPException(status_code=404, detail="Evaluación no encontrada.")
        return {"mensaje": "Evaluación eliminada correctamente."}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error eliminando evaluación %s", evaluacion_id)
        raise HTTPException(status_code=500, detail="No fue posible eliminar la evaluación.")
