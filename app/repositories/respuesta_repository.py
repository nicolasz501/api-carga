
from app.core.database import Database
import logging

logger = logging.getLogger(__name__)


class RespuestaRepository:
    def __init__(self):
        self.db = Database()

    @staticmethod
    def _obtener_valor(resultado, columna, indice=0):
        """Obtiene un valor tanto de una fila dict como de una tupla."""
        if resultado is None:
            return None

        if isinstance(resultado, dict):
            return resultado.get(columna)

        try:
            return resultado[indice]
        except (IndexError, KeyError, TypeError):
            return None

    def obtener_todos(self):
        conn = self.db.get_connection()
        try:
            with conn.cursor() as cursor:
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
                    ORDER BY respuesta_id ASC
                """)
                return cursor.fetchall()
        finally:
            conn.close()

    def obtener_por_id(self, respuesta_id):
        conn = self.db.get_connection()
        try:
            with conn.cursor() as cursor:
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
                    WHERE respuesta_id = %s
                """, (respuesta_id,))
                return cursor.fetchone()
        finally:
            conn.close()

    def crear(self, respuesta):
        conn = self.db.get_connection()
        try:
            with conn.cursor() as cursor:
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
                    RETURNING respuesta_id
                """, (
                    respuesta.pregunta_evaluacion_id,
                    respuesta.pregunta_id,
                    respuesta.usuario_id,
                    respuesta.puntaje,
                    getattr(respuesta, "comentario", None),
                    getattr(respuesta, "estado", True),
                ))

                resultado = cursor.fetchone()
                respuesta_id = self._obtener_valor(
                    resultado, "respuesta_id"
                )

                if respuesta_id is None:
                    raise RuntimeError(
                        "PostgreSQL no devolvió respuesta_id."
                    )

                conn.commit()
                return respuesta_id

        except Exception:
            conn.rollback()
            logger.exception("Error creando respuesta")
            raise
        finally:
            conn.close()

    def crear_lote(
        self,
        respuestas: list,
        usuario_id: int,
        comentario: str = None,
        evaluacion_id: int = None
    ):
        """
        Guarda todas las respuestas de un envío en una transacción.
        Permite volver a responder una evaluación en otro envío.
        """
        if not respuestas:
            raise ValueError(
                "Debes enviar al menos una respuesta."
            )

        conn = self.db.get_connection()
        ids_creados = []

        try:
            with conn.cursor() as cursor:
                for indice, respuesta in enumerate(respuestas):
                    pregunta_evaluacion_id = getattr(
                        respuesta, "pregunta_evaluacion_id", None
                    )
                    pregunta_id = getattr(
                        respuesta, "pregunta_id", None
                    )
                    puntaje = getattr(respuesta, "puntaje", None)
                    estado = getattr(respuesta, "estado", True)

                    if pregunta_evaluacion_id is None:
                        raise ValueError(
                            "Falta pregunta_evaluacion_id "
                            "en una de las respuestas."
                        )

                    if pregunta_id is None:
                        raise ValueError(
                            "Falta pregunta_id en una de las respuestas."
                        )

                    if puntaje is None or not 1 <= puntaje <= 5:
                        raise ValueError(
                            "Cada puntaje debe estar entre 1 y 5."
                        )

                    # El comentario general se guarda una sola vez,
                    # en la primera respuesta del envío.
                    comentario_respuesta = None

                    if indice == 0 and comentario:
                        comentario_limpio = comentario.strip()
                        if comentario_limpio:
                            comentario_respuesta = comentario_limpio[:500]
                    else:
                        # Compatible con modelos que tengan comentario.
                        comentario_individual = getattr(
                            respuesta, "comentario", None
                        )
                        if comentario_individual:
                            comentario_respuesta = (
                                comentario_individual.strip()[:500]
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
                        RETURNING respuesta_id
                    """, (
                        pregunta_evaluacion_id,
                        pregunta_id,
                        usuario_id,
                        puntaje,
                        comentario_respuesta,
                        estado,
                    ))

                    resultado = cursor.fetchone()
                    respuesta_id = self._obtener_valor(
                        resultado, "respuesta_id"
                    )

                    if respuesta_id is None:
                        raise RuntimeError(
                            "PostgreSQL no devolvió respuesta_id "
                            "al guardar una respuesta."
                        )

                    ids_creados.append(respuesta_id)

            # Confirmar únicamente cuando todas se hayan insertado.
            conn.commit()

            logger.info(
                "Se guardaron %s respuestas del usuario %s "
                "para la evaluación %s.",
                len(ids_creados),
                usuario_id,
                evaluacion_id,
            )

            return ids_creados

        except Exception:
            conn.rollback()
            logger.exception(
                "Error guardando respuestas. Usuario=%s, evaluación=%s",
                usuario_id,
                evaluacion_id,
            )
            raise

        finally:
            conn.close()

    def actualizar(self, respuesta_id, respuesta):
        conn = self.db.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE respuestas
                    SET
                        pregunta_evaluacion_id = %s,
                        pregunta_id = %s,
                        usuario_id = %s,
                        puntaje = %s,
                        comentario = %s,
                        estado = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE respuesta_id = %s
                    RETURNING respuesta_id
                """, (
                    respuesta.pregunta_evaluacion_id,
                    respuesta.pregunta_id,
                    respuesta.usuario_id,
                    respuesta.puntaje,
                    getattr(respuesta, "comentario", None),
                    getattr(respuesta, "estado", True),
                    respuesta_id,
                ))

                resultado = cursor.fetchone()

                if resultado is None:
                    conn.rollback()
                    return None

                actualizado_id = self._obtener_valor(
                    resultado, "respuesta_id"
                )

                conn.commit()
                return actualizado_id

        except Exception:
            conn.rollback()
            logger.exception(
                "Error actualizando respuesta %s", respuesta_id
            )
            raise
        finally:
            conn.close()

    def eliminar(self, respuesta_id):
        conn = self.db.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM respuestas
                    WHERE respuesta_id = %s
                    RETURNING respuesta_id
                """, (respuesta_id,))

                resultado = cursor.fetchone()

                if resultado is None:
                    conn.rollback()
                    return False

                conn.commit()
                return True

        except Exception:
            conn.rollback()
            logger.exception(
                "Error eliminando respuesta %s", respuesta_id
            )
            raise
        finally:
            conn.close()
