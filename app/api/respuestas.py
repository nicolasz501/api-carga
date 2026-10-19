
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.models.Respuesta import Respuesta
from app.repositories.respuesta_repository import RespuestaRepository


router = APIRouter(
    prefix="/respuestas",
    tags=["Gestión de Respuestas"]
)

repo = RespuestaRepository()


class RespuestaLoteItem(BaseModel):
    pregunta_evaluacion_id: int = Field(gt=0)
    pregunta_id: int = Field(gt=0)
    puntaje: int = Field(ge=1, le=5)
    estado: bool = True


class RespuestasLote(BaseModel):
    usuario_id: int = Field(gt=0)

    respuestas: list[RespuestaLoteItem] = Field(
        min_length=5,
        max_length=5
    )

    comentario: Optional[str] = Field(
        default=None,
        max_length=2000
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
                "Las cinco respuestas deben tener relaciones "
                "de pregunta diferentes."
            )

        if len(set(pregunta_ids)) != 5:
            raise ValueError(
                "Las cinco respuestas deben corresponder "
                "a preguntas diferentes."
            )

        return self


@router.post("/lote")
def crear_respuestas_lote(datos: RespuestasLote):
    try:
        ids = repo.crear_lote(
            respuestas=datos.respuestas,
            usuario_id=datos.usuario_id,
            comentario=datos.comentario
        )

        return {
            "mensaje": "Las cinco respuestas se registraron exitosamente.",
            "usuario_id": datos.usuario_id,
            "ids": ids,
            "total": len(ids),
            "comentario_guardado": bool(
                datos.comentario and datos.comentario.strip()
            )
        }

    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )

    except Exception as e:
        print(f"Error en POST /respuestas/lote: {e}")

        raise HTTPException(
            status_code=500,
            detail="No se pudieron registrar las respuestas."
        )


@router.get("/")
def listar_respuestas():
    try:
        return repo.obtener_todos()

    except Exception as e:
        print(f"Error al listar respuestas: {e}")
        raise HTTPException(
            status_code=500,
            detail="No se pudieron consultar las respuestas."
        )


@router.get("/{respuesta_id}")
def obtener_respuesta(respuesta_id: int):
    try:
        respuesta = repo.obtener_por_id(respuesta_id)

        if respuesta is None:
            raise HTTPException(
                status_code=404,
                detail="Respuesta no encontrada."
            )

        return respuesta

    except HTTPException:
        raise

    except Exception as e:
        print(f"Error al consultar respuesta: {e}")
        raise HTTPException(
            status_code=500,
            detail="No se pudo consultar la respuesta."
        )


@router.post("/")
def crear_respuesta(respuesta: Respuesta):
    try:
        nuevo_id = repo.crear(respuesta)

        return {
            "mensaje": "Respuesta registrada exitosamente.",
            "id": nuevo_id
        }

    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )

    except Exception as e:
        print(f"Error al crear respuesta: {e}")
        raise HTTPException(
            status_code=500,
            detail="No se pudo registrar la respuesta."
        )


@router.put("/{respuesta_id}")
def actualizar_respuesta(
    respuesta_id: int,
    respuesta: Respuesta
):
    try:
        actualizado = repo.actualizar(
            respuesta_id,
            respuesta
        )

        if not actualizado:
            raise HTTPException(
                status_code=404,
                detail="Respuesta no encontrada."
            )

        return {
            "mensaje": "Respuesta actualizada correctamente."
        }

    except HTTPException:
        raise

    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )

    except Exception as e:
        print(f"Error al actualizar respuesta: {e}")
        raise HTTPException(
            status_code=500,
            detail="No se pudo actualizar la respuesta."
        )


@router.delete("/{respuesta_id}")
def eliminar_respuesta(respuesta_id: int):
    try:
        eliminado = repo.eliminar(respuesta_id)

        if not eliminado:
            raise HTTPException(
                status_code=404,
                detail="Respuesta no encontrada."
            )

        return {
            "mensaje": "Respuesta eliminada correctamente."
        }

    except HTTPException:
        raise

    except Exception as e:
        print(f"Error al eliminar respuesta: {e}")
        raise HTTPException(
            status_code=500,
            detail="No se pudo eliminar la respuesta."
        )
