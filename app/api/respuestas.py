
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.repositories.respuesta_repository import RespuestaRepository
from app.api.usuarios import UsuarioActual, get_usuario_actual

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/respuestas",
    tags=["Gestión de Respuestas"],
)

repo = RespuestaRepository()


class RespuestaLoteItem(BaseModel):
    pregunta_evaluacion_id: int = Field(gt=0)
    pregunta_id: int = Field(gt=0)
    puntaje: int = Field(ge=1, le=5)
    estado: bool = True


class RespuestasLote(BaseModel):
    usuario_id: int = Field(gt=0)
    evaluacion_id: int = Field(gt=0)

    respuestas: list[RespuestaLoteItem] = Field(
        min_length=5,
        max_length=5,
    )

    comentario: Optional[str] = Field(
        default=None,
        max_length=500,
    )

    @model_validator(mode="after")
    def validar_preguntas_unicas(self):
        relacion_ids = [
            r.pregunta_evaluacion_id for r in self.respuestas
        ]
        pregunta_ids = [
            r.pregunta_id for r in self.respuestas
        ]

        if len(set(relacion_ids)) != 5:
            raise ValueError(
                "Las cinco respuestas deben tener preguntas diferentes."
            )

        if len(set(pregunta_ids)) != 5:
            raise ValueError(
                "No puedes responder dos veces la misma pregunta "
                "en un mismo envío."
            )

        return self


@router.post("/lote")
def crear_respuestas_lote(
    datos: RespuestasLote,
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """
    Registra un nuevo intento. No bloquea al usuario por haber
    respondido previamente.

    La identidad se toma de la sesión autenticada para evitar
    registrar respuestas con el ID de otra persona.
    """
    if usuario.usuario_id != datos.usuario_id:
        raise HTTPException(
            status_code=403,
            detail="No puedes registrar respuestas en nombre de otro usuario.",
        )

    try:
        ids = repo.crear_lote(
            respuestas=datos.respuestas,
            usuario_id=usuario.usuario_id,
            comentario=datos.comentario,
            evaluacion_id=datos.evaluacion_id,
        )

        return {
            "mensaje": "Las cinco respuestas se registraron exitosamente.",
            "usuario_id": usuario.usuario_id,
            "evaluacion_id": datos.evaluacion_id,
            "ids": ids,
            "total": len(ids),
            "completada": True,
            "comentario_guardado": bool(
                datos.comentario and datos.comentario.strip()
            ),
        }

    except ValueError as e:
        logger.warning(
            "No se pudieron registrar respuestas del usuario %s: %s",
            usuario.usuario_id,
            e,
        )
        raise HTTPException(
            status_code=422,
            detail=str(e),
        )

    except TypeError:
        logger.exception(
            "La firma de RespuestaRepository.crear_lote no coincide "
            "con los argumentos enviados."
        )
        raise HTTPException(
            status_code=501,
            detail=(
                "Debes actualizar RespuestaRepository.crear_lote "
                "para recibir evaluacion_id y aceptar nuevos intentos."
            ),
        )

    except Exception:
        logger.exception(
            "Error guardando respuestas del usuario %s",
            usuario.usuario_id,
        )
        raise HTTPException(
            status_code=500,
            detail="No se pudieron registrar las respuestas.",
        )


@router.get("/")
def listar_respuestas(
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    try:
        # Conserva este endpoint para la consulta general.
        # En producción, limita los resultados según el rol.
        return repo.obtener_todos()
    except Exception:
        logger.exception("Error al listar respuestas")
        raise HTTPException(
            status_code=500,
            detail="No se pudieron consultar las respuestas.",
        )


@router.get("/{respuesta_id}")
def obtener_respuesta(
    respuesta_id: int,
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    try:
        respuesta = repo.obtener_por_id(respuesta_id)

        if respuesta is None:
            raise HTTPException(
                status_code=404,
                detail="Respuesta no encontrada.",
            )

        return respuesta

    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Error consultando respuesta %s",
            respuesta_id,
        )
        raise HTTPException(
            status_code=500,
            detail="No se pudo consultar la respuesta.",
        )
