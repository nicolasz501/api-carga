
from app.core.database import Database
from app.models.Respuesta import Respuesta


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

            if isinstance(resultado, dict):
                respuesta_id = resultado["respuesta_id"]
            else:
                respuesta_id = resultado[0]

            conn.commit()
            return respuesta_id

        except Exception:
            if conn:
                conn.rollback()
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
            conn = self.db.get_connection()
            cursor = conn.cursor()

            ids_creados = []

            for indice, respuesta in enumerate(respuestas):
                comentario_respuesta = (
                    comentario.strip()[:500]
                    if indice == 0 and comentario and comentario.strip()
                    else respuesta.comentario
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
                    comentario_respuesta,
                    respuesta.estado
                ))

                resultado = cursor.fetchone()

                if isinstance(resultado, dict):
                    respuesta_id = resultado["respuesta_id"]
                else:
                    respuesta_id = resultado[0]

                ids_creados.append(respuesta_id)

            conn.commit()
            return ids_creados

        except Exception:
            if conn:
                conn.rollback()
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
            raise

        finally:
            if conn:
                conn.close()
