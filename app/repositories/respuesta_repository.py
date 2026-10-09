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
                SELECT *
                FROM respuestas
                ORDER BY respuesta_id ASC;
            """)

            return cursor.fetchall()

        except Exception as e:
            print(f"Error al obtener respuestas: {e}")
            return []

        finally:
            if conn:
                conn.close()

    def obtener_por_id(self, respuesta_id: int):
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM respuestas
                WHERE respuesta_id = %s;
            """, (respuesta_id,))

            return cursor.fetchone()

        except Exception as e:
            print(f"Error al obtener respuesta: {e}")
            return None

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
                    pregunta_id,
                    puntaje,
                    comentario,
                    estado
                )
                VALUES (%s, %s, %s, %s)
                RETURNING respuesta_id;
            """, (
                respuesta.pregunta_id,
                respuesta.puntaje,
                respuesta.comentario,
                respuesta.estado
            ))

            resultado = cursor.fetchone()
            nuevo_id = resultado["respuesta_id"]

            conn.commit()
            return nuevo_id

        except Exception as e:
            if conn:
                conn.rollback()

            print(f"Error al crear respuesta: {e}")
            return None

        finally:
            if conn:
                conn.close()

    def crear_lote(self, respuestas: list[Respuesta], comentario: str | None = None):
        conn = None

        try:
            if len(respuestas) != 5:
                raise ValueError(
                    "La evaluación debe contener exactamente 5 respuestas."
                )

            pregunta_ids = [r.pregunta_id for r in respuestas]

            if len(set(pregunta_ids)) != 5:
                raise ValueError(
                    "No puedes responder dos veces la misma pregunta "
                    "en una misma solicitud."
                )

            conn = self.db.get_connection()
            cursor = conn.cursor()

            ids_creados = []

            for indice, respuesta in enumerate(respuestas):
                # El comentario general se almacena una sola vez.
                comentario_respuesta = (
                    comentario.strip()
                    if indice == 0 and comentario and comentario.strip()
                    else None
                )

                cursor.execute("""
                    INSERT INTO respuestas (
                        pregunta_id,
                        puntaje,
                        comentario,
                        estado
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING respuesta_id;
                """, (
                    respuesta.pregunta_id,
                    respuesta.puntaje,
                    comentario_respuesta,
                    respuesta.estado
                ))

                resultado = cursor.fetchone()
                ids_creados.append(resultado["respuesta_id"])

            # Solo se confirman las cinco respuestas si todas se insertan.
            conn.commit()

            return ids_creados

        except Exception as e:
            if conn:
                conn.rollback()

            print(f"Error al crear respuestas por lote: {e}")
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

            eliminado = cursor.fetchone()

            conn.commit()
            return eliminado is not None

        except Exception as e:
            if conn:
                conn.rollback()

            print(f"Error al eliminar respuesta: {e}")
            return False

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
                SET pregunta_id = %s,
                    puntaje = %s,
                    comentario = %s,
                    estado = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE respuesta_id = %s
                RETURNING respuesta_id;
            """, (
                respuesta.pregunta_id,
                respuesta.puntaje,
                respuesta.comentario,
                respuesta.estado,
                respuesta_id
            ))

            actualizado = cursor.fetchone()

            conn.commit()
            return actualizado is not None

        except Exception as e:
            if conn:
                conn.rollback()

            print(f"Error al actualizar respuesta: {e}")
            return False

        finally:
            if conn:
                conn.close()