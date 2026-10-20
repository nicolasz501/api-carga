
import logging
from app.core.database import Database
from app.models.Respuesta import Respuesta

logger = logging.getLogger(__name__)


class RespuestaRepository:

    def __init__(self):
        self.db = Database()

    def obtener_todos(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    respuesta_id,
                    pregunta_evaluacion_id,
                    pregunta_id,
                    usuario_id,
                    puntaje,
                    comentario,
                    estado,
                    created_at,
                    updated_at
                FROM respuestas
                ORDER BY respuesta_id ASC;
            """)

            return cursor.fetchall()
        finally:
            if conn:
                conn.close()

    def obtener_por_id(self, respuesta_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    respuesta_id,
                    pregunta_evaluacion_id,
                    pregunta_id,
                    usuario_id,
                    puntaje,
                    comentario,
                    estado,
                    created_at,
                    updated_at
                FROM respuestas
                WHERE respuesta_id = %s;
            """, (respuesta_id,))

            return cursor.fetchone()
        finally:
            if conn:
                conn.close()

    def crear(self, respuesta: Respuesta):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO respuestas (
                    pregunta_evaluacion_id,
                    pregunta_id,
                    usuario_id,
                    puntaje,
                    comentario,
                    estado
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING respuesta_id;
            """, (
                respuesta.pregunta_evaluacion_id,
                respuesta.pregunta_id,
                respuesta.usuario_id,
                respuesta.puntaje,
                respuesta.comentario,
                respuesta.estado
            ))

            resultado = cursor.fetchone()
            conn.commit()

            return resultado[0] if resultado else None

        except Exception:
            if conn:
                conn.rollback()
            logger.exception("Error creando respuesta")
            raise
        finally:
            if conn:
                conn.close()

    def crear_lote(
        self,
        respuestas: list,
        usuario_id: int,
        comentario: str = None,
        evaluacion_id: int = None
    ):
        conn = None

        try:
            if not respuestas:
                raise ValueError(
                    "Debes enviar al menos una respuesta."
                )

            if evaluacion_id is None or evaluacion_id <= 0:
                raise ValueError(
                    "Debes indicar una evaluación válida."
                )

            conn = self.db.get_connection()
            cursor = conn.cursor()

            # Comprobar que la evaluación exista y esté activa.
            cursor.execute("""
                SELECT evaluacion_id
                FROM evaluaciones
                WHERE evaluacion_id = %s
                  AND estado = TRUE;
            """, (evaluacion_id,))

            if cursor.fetchone() is None:
                raise ValueError(
                    "La evaluación no existe o está inactiva."
                )

            # Validar todas las preguntas antes de insertar.
            ids_preguntas = set()

            for respuesta in respuestas:
                pregunta_evaluacion_id = (
                    respuesta.pregunta_evaluacion_id
                )
                pregunta_id = respuesta.pregunta_id
                puntaje = respuesta.puntaje

                if pregunta_evaluacion_id in ids_preguntas:
                    raise ValueError(
                        "No puedes enviar dos respuestas para "
                        "la misma pregunta en un solo envío."
                    )

                ids_preguntas.add(pregunta_evaluacion_id)

                if not 1 <= puntaje <= 5:
                    raise ValueError(
                        "El puntaje debe estar entre 1 y 5."
                    )

                cursor.execute("""
                    SELECT pe.pregunta_evaluacion_id
                    FROM preguntas_evaluacion pe
                    JOIN preguntas p
                      ON p.pregunta_id = pe.pregunta_id
                    WHERE pe.pregunta_evaluacion_id = %s
                      AND pe.pregunta_id = %s
                      AND pe.evaluacion_id = %s
                      AND pe.estado = TRUE
                      AND p.estado = TRUE;
                """, (
                    pregunta_evaluacion_id,
                    pregunta_id,
                    evaluacion_id
                ))

                if cursor.fetchone() is None:
                    raise ValueError(
                        "Una de las preguntas no pertenece a "
                        "la evaluación seleccionada o está inactiva."
                    )

            ids_creados = []

            # Insertar respuestas nuevas. No se sobrescriben
            # los envíos anteriores del usuario.
            for indice, respuesta in enumerate(respuestas):
                comentario_individual = getattr(
                    respuesta,
                    "comentario",
                    None
                )

                comentario_general = (
                    comentario.strip()[:500]
                    if indice == 0
                    and comentario
                    and comentario.strip()
                    else comentario_individual
                )

                cursor.execute("""
                    INSERT INTO respuestas (
                        pregunta_evaluacion_id,
                        pregunta_id,
                        usuario_id,
                        puntaje,
                        comentario,
                        estado
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING respuesta_id;
                """, (
                    respuesta.pregunta_evaluacion_id,
                    respuesta.pregunta_id,
                    usuario_id,
                    respuesta.puntaje,
                    comentario_general,
                    getattr(respuesta, "estado", True)
                ))

                resultado = cursor.fetchone()
                ids_creados.append(resultado[0])

            conn.commit()
            return ids_creados

        except Exception:
            if conn:
                conn.rollback()

            logger.exception(
                "Error guardando respuestas de la evaluación %s",
                evaluacion_id
            )
            raise

        finally:
            if conn:
                conn.close()

    def actualizar(self, respuesta_id: int, respuesta: Respuesta):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE respuestas
                SET pregunta_evaluacion_id = %s,
                    pregunta_id = %s,
                    usuario_id = %s,
                    puntaje = %s,
                    comentario = %s,
                    estado = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE respuesta_id = %s
                RETURNING respuesta_id;
            """, (
                respuesta.pregunta_evaluacion_id,
                respuesta.pregunta_id,
                respuesta.usuario_id,
                respuesta.puntaje,
                respuesta.comentario,
                respuesta.estado,
                respuesta_id
            ))

            resultado = cursor.fetchone()
            conn.commit()

            return resultado is not None

        except Exception:
            if conn:
                conn.rollback()
            logger.exception("Error actualizando respuesta")
            raise
        finally:
            if conn:
                conn.close()

    def eliminar(self, respuesta_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM respuestas
                WHERE respuesta_id = %s
                RETURNING respuesta_id;
            """, (respuesta_id,))

            resultado = cursor.fetchone()
            conn.commit()

            return resultado is not None

        except Exception:
            if conn:
                conn.rollback()
            logger.exception("Error eliminando respuesta")
            raise
        finally:
            if conn:
                conn.close()
