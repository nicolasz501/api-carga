import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.models.Evaluacion import Evaluacion
from app.repositories.evaluacion_repository import EvaluacionRepository


logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Seguridad (incluida aquí para no agregar archivos nuevos al proyecto).
# Si el proyecto ya tiene una forma de obtener el usuario autenticado,
# reemplaza el cuerpo de get_usuario_actual por esa lógica.
# ----------------------------------------------------------------------
# Debe coincidir con roles.nombre_rol en la base de datos.
ROL_JEFE = "JEFE_DEPARTAMENTO"

_bearer = HTTPBearer(auto_error=False)


class UsuarioActual(BaseModel):
    usuario_id: int  # usuarios.id_usuario
    rol: str         # roles.nombre_rol


def get_usuario_actual(
    credenciales: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UsuarioActual:
    if credenciales is None:
        raise HTTPException(status_code=401, detail="No autenticado.")

    token = credenciales.credentials

    # TODO: validar el token con el mecanismo de login actual y devolver
    # UsuarioActual(usuario_id=..., rol=...).
    raise HTTPException(
        status_code=501,
        detail="get_usuario_actual aún no está implementado."
    )


def requiere_jefe(
    usuario: UsuarioActual = Depends(get_usuario_actual),
) -> UsuarioActual:
    if usuario.rol != ROL_JEFE:
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    return usuario

router = APIRouter(
    prefix="/evaluaciones",
    tags=["Gestión de Evaluaciones"]
)

repo = EvaluacionRepository()


class AsignacionEvaluacion(BaseModel):
    carga_id: int = Field(gt=0)


class AsignacionMasiva(BaseModel):
    plantilla_evaluacion_id: int = Field(gt=0)


# ----------------------------------------------------------------------
# Rutas del docente (el ID sale de la sesión, nunca del cliente)
# ----------------------------------------------------------------------
@router.get("/mis-evaluaciones")
def mis_evaluaciones(
    usuario: UsuarioActual = Depends(get_usuario_actual)
):
    try:
        return repo.obtener_para_docente(usuario.usuario_id)

    except Exception:
        logger.exception(
            "Error consultando evaluaciones del docente usuario_id=%s",
            usuario.usuario_id
        )
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar las evaluaciones pendientes."
        )


# ----------------------------------------------------------------------
# Rutas del jefe de departamento
# (las rutas fijas deben ir antes de /{evaluacion_id})
# ----------------------------------------------------------------------
@router.post("/asignar-todos")
def asignar_autoevaluacion_todos(
    solicitud: AsignacionMasiva,
    _jefe: UsuarioActual = Depends(requiere_jefe)
):
    try:
        return repo.asignar_autoevaluacion_a_todos(
            solicitud.plantilla_evaluacion_id
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception:
        logger.exception(
            "Error al asignar autoevaluaciones a todos los docentes"
        )
        raise HTTPException(
            status_code=500,
            detail="No fue posible asignar las autoevaluaciones."
        )


@router.get("/")
def listar_evaluaciones(_jefe: UsuarioActual = Depends(requiere_jefe)):
    try:
        return repo.obtener_todos()
    except Exception:
        logger.exception("Error al listar evaluaciones")
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar las evaluaciones."
        )


@router.post("/")
def crear_evaluacion(
    evaluacion: Evaluacion,
    _jefe: UsuarioActual = Depends(requiere_jefe)
):
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


# ----------------------------------------------------------------------
# Detalle (jefe: cualquiera; docente: solo la propia)
# ----------------------------------------------------------------------
@router.get("/{evaluacion_id}")
def obtener_evaluacion(
    evaluacion_id: int,
    usuario: UsuarioActual = Depends(get_usuario_actual)
):
    try:
        evaluacion = repo.obtener_por_id(evaluacion_id)

        # Mismo 404 si no existe o si no es suya: no revela su existencia.
        if not evaluacion or (
            usuario.rol != ROL_JEFE
            and not repo.pertenece_a_docente(
                evaluacion_id, usuario.usuario_id
            )
        ):
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


@router.put("/{evaluacion_id}/asignar")
def asignar_evaluacion(
    evaluacion_id: int,
    asignacion: AsignacionEvaluacion,
    _jefe: UsuarioActual = Depends(requiere_jefe)
):
    try:
        evaluacion = repo.obtener_por_id(evaluacion_id)

        if not evaluacion:
            raise HTTPException(
                status_code=404,
                detail="Evaluación no encontrada."
            )

        exito = repo.asignar_carga(evaluacion_id, asignacion.carga_id)

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
    evaluacion: Evaluacion,
    _jefe: UsuarioActual = Depends(requiere_jefe)
):
    try:
        exito = repo.actualizar(evaluacion_id, evaluacion)

        if not exito:
            raise HTTPException(
                status_code=404,
                detail="Evaluación no encontrada."
            )

        return {"mensaje": "Evaluación actualizada correctamente."}

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
def eliminar_evaluacion(
    evaluacion_id: int,
    _jefe: UsuarioActual = Depends(requiere_jefe)
):
    try:
        exito = repo.eliminar(evaluacion_id)

        if not exito:
            raise HTTPException(
                status_code=404,
                detail="Evaluación no encontrada."
            )

        return {"mensaje": "Evaluación eliminada correctamente."}

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