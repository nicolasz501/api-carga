
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
        relaciones = [
            respuesta.pregunta_evaluacion_id
            for respuesta in self.respuestas
        ]
        preguntas = [
            respuesta.pregunta_id
            for respuesta in self.respuestas
        ]

        if len(set(relaciones)) != 5:
            raise ValueError(
                "Las cinco respuestas deben corresponder "
                "a relaciones de preguntas diferentes."
            )

        if len(set(preguntas)) != 5:
            raise ValueError(
                "No puedes responder dos veces la misma pregunta."
            )

        return self


def es_administrador(usuario: UsuarioActual) -> bool:
    """Comprueba si el rol del usuario tiene permisos administrativos."""
    rol = getattr(usuario, "rol", None)

    if isinstance(rol, dict):
        rol = rol.get("nombre_rol") or rol.get("nombre")

    if rol is None:
        rol = getattr(usuario, "nombre_rol", "")

    rol = str(rol or "").strip().casefold()

    return rol in {
        "administrador",
        "admin",
        "dirección académica",
        "direccion academica",
        "jefe de departamento",
    }


def obtener_propietario(respuesta):
    """Obtiene usuario_id de una fila devuelta como tupla o diccionario."""
    if respuesta is None:
        return None

    if isinstance(respuesta, dict):
        return respuesta.get("usuario_id")

    # obtener_por_id selecciona usuario_id en la posición 3.
    return respuesta[3]


@router.post("/lote")
def crear_respuestas_lote(
    datos: RespuestasLote,
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """Guarda cinco respuestas para una evaluación del usuario autenticado."""
    usuario_id = usuario.usuario_id

    if usuario_id != datos.usuario_id:
        raise HTTPException(
            status_code=403,
            detail="No puedes registrar respuestas en nombre de otro usuario.",
        )

    try:
        ids = repo.crear_lote(
            respuestas=datos.respuestas,
            usuario_id=usuario_id,
            comentario=datos.comentario,
            evaluacion_id=datos.evaluacion_id,
        )

        return {
            "mensaje": "Las respuestas se registraron exitosamente.",
            "usuario_id": usuario_id,
            "evaluacion_id": datos.evaluacion_id,
            "ids": ids,
            "total": len(ids),
            "completada": True,
            "comentario_guardado": bool(
                datos.comentario and datos.comentario.strip()
            ),
        }

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    except Exception:
        logger.exception(
            "Error guardando respuestas del usuario %s",
            usuario_id,
        )
        raise HTTPException(
            status_code=500,
            detail="No se pudieron registrar las respuestas.",
        )


@router.get("/")
def listar_respuestas(
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """Los administradores consultan todas; otros usuarios, solo las propias."""
    conn = None

    try:
        conn = repo.db.get_connection()
        cursor = conn.cursor()

        consulta = """
            SELECT
                r.respuesta_id,
                r.pregunta_evaluacion_id,
                r.pregunta_id,
                r.usuario_id,
                r.puntaje,
                r.comentario,
                r.estado,
                r.created_at,
                r.updated_at,
                CONCAT_WS(
                    ' ',
                    u.primer_nombre,
                    u.segundo_nombre,
                    u.primer_apellido,
                    u.segundo_apellido
                ) AS nombre_evaluador,
                u.correo,
                p.texto_pregunta AS pregunta,
                pe.evaluacion_id,
                e.titulo AS evaluacion,
                e.tipo_evaluacion
            FROM respuestas r
            LEFT JOIN usuarios u
                ON u.usuario_id = r.usuario_id
            LEFT JOIN preguntas p
                ON p.pregunta_id = r.pregunta_id
            LEFT JOIN preguntas_evaluacion pe
                ON pe.pregunta_evaluacion_id =
                   r.pregunta_evaluacion_id
            LEFT JOIN evaluaciones e
                ON e.evaluacion_id = pe.evaluacion_id
        """

        parametros = ()

        if not es_administrador(usuario):
            consulta += " WHERE r.usuario_id = %s"
            parametros = (usuario.usuario_id,)

        consulta += """
            ORDER BY r.created_at DESC, r.respuesta_id DESC;
        """

        cursor.execute(consulta, parametros)
        return cursor.fetchall()

    except Exception:
        logger.exception("Error al listar respuestas")
        raise HTTPException(
            status_code=500,
            detail="No se pudieron consultar las respuestas.",
        )

    finally:
        if conn:
            conn.close()


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

        propietario_id = obtener_propietario(respuesta)

        if (
            propietario_id != usuario.usuario_id
            and not es_administrador(usuario)
        ):
            raise HTTPException(
                status_code=403,
                detail="No tienes permiso para consultar esta respuesta.",
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
