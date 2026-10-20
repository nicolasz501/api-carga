
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

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
    respuestas: list[RespuestaLoteItem] = Field(min_length=1)
    comentario: Optional[str] = Field(
        default=None,
        max_length=500,
    )


def es_administrador(usuario: UsuarioActual) -> bool:
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
    if respuesta is None:
        return None

    if isinstance(respuesta, dict):
        return respuesta.get("usuario_id")

    # SELECT de obtener_por_id devuelve las columnas en este orden:
    # respuesta_id, pregunta_evaluacion_id, pregunta_id, usuario_id...
    return respuesta[3]


@router.post("/lote")
def crear_respuestas_lote(
    datos: RespuestasLote,
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """Guarda un envío nuevo de respuestas del usuario autenticado."""

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
            "mensaje": "Respuestas guardadas correctamente.",
            "usuario_id": usuario_id,
            "evaluacion_id": datos.evaluacion_id,
            "ids": ids,
            "total": len(ids),
            "comentario_guardado": bool(
                datos.comentario and datos.comentario.strip()
            ),
        }

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    except Exception as error:
        logger.exception(
            "Error en POST /respuestas/lote. Usuario=%s, evaluación=%s",
            usuario_id,
            datos.evaluacion_id,
        )

        raise HTTPException(
            status_code=500,
            detail="No se pudieron guardar las respuestas. Revisa los logs del servidor.",
        ) from error


@router.get("/")
def listar_respuestas(
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """Los administradores ven todas las respuestas; los demás, las propias."""

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

    except Exception as error:
        logger.exception("Error consultando respuestas")
        raise HTTPException(
            status_code=500,
            detail="No se pudieron consultar las respuestas.",
        ) from error

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

    except Exception as error:
        logger.exception(
            "Error consultando respuesta %s",
            respuesta_id,
        )
        raise HTTPException(
            status_code=500,
            detail="No se pudo consultar la respuesta.",
        ) from error
