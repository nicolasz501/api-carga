
from app.core.database import Database
from app.models.Respuesta import Respuesta


class RespuestaRepository:

    def __init__(self):
        self.db = Database()

    @staticmethod
    def _valor(fila, columna, indice):
        """Compatible con cursores que devuelven diccionarios o tuplas."""
        if isinstance(fila, dict):
            return fila[columna]
        return fila[indice]

    def obtener_todos(self):
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
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
                ORDER BY r.respuesta_id ASC;
            """)

            return cursor.fetchall()

        except Exception as e:
            print(f"Error al obtener respuestas: {e}")
            raise

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
                WHERE r.respuesta_id = %s;
            """, (respuesta_id,))

            return cursor.fetchone()

        except Exception as e:
            print(f"Error al obtener respuesta: {e}")
            raise

        finally:
            if conn:
                conn.close()

    def _validar_usuario(self, cursor, usuario_id: int):
        cursor.execute("""
            SELECT usuario_id
            FROM usuarios
            WHERE usuario_id = %s
              AND estado = TRUE;
        """, (usuario_id,))

        if cursor.fetchone() is None:
            raise ValueError("El usuario no existe o está inactivo.")

    def _validar_relaciones(self, cursor, respuestas):
        """
        Comprueba que cada pregunta_evaluacion_id corresponda
        al pregunta_id enviado y que ambos estén activos.
        """
        for respuesta in respuestas:
            relacion_id = getattr(
                respuesta, "pregunta_evaluacion_id", None
            )
            pregunta_id = getattr(respuesta, "pregunta_id", None)

            if not relacion_id or not pregunta_id:
                raise ValueError(
                    "Cada respuesta debe incluir pregunta_evaluacion_id "
                    "y pregunta_id."
                )

            cursor.execute("""
                SELECT pe.pregunta_evaluacion_id
                FROM preguntas_evaluacion pe
                JOIN preguntas p
                    ON p.pregunta_id = pe.pregunta_id
                WHERE pe.pregunta_evaluacion_id = %s
                  AND pe.pregunta_id = %s
                  AND pe.estado = TRUE
                  AND p.estado = TRUE;
            """, (relacion_id, pregunta_id))

            if cursor.fetchone() is None:
                raise ValueError(
                    f"La relación de pregunta {relacion_id} no existe, "
                    "está inactiva o no corresponde a la pregunta "
                    f"{pregunta_id}."
                )

            puntaje = respuesta.puntaje

            if puntaje is None or not 1 <= puntaje <= 5:
                raise ValueError(
                    "Cada puntaje debe estar entre 1 y 5."
                )

    def crear(self, respuesta: Respuesta):
        conn = None

        try:
            if not respuesta.usuario_id:
                raise ValueError(
                    "Se necesita el usuario que realiza la evaluación."
                )

            conn = self.db.get_connection()
            cursor = conn.cursor()

            self._validar_usuario(cursor, respuesta.usuario_id)
            self._validar_relaciones(cursor, [respuesta])

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

            fila = cursor.fetchone()
            nuevo_id = self._valor(fila, "respuesta_id", 0)

            conn.commit()
            return nuevo_id

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
        comentario: str | None = None
    ):
        conn = None

        try:
            if not usuario_id or usuario_id <= 0:
                raise ValueError("El usuario evaluador no es válido.")

            if len(respuestas) != 5:
                raise ValueError(
                    "La evaluación debe contener exactamente "
                    "5 respuestas."
                )

            relacion_ids = [
                r.pregunta_evaluacion_id for r in respuestas
            ]
            pregunta_ids = [r.pregunta_id for r in respuestas]

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

            conn = self.db.get_connection()
            cursor = conn.cursor()

            self._validar_usuario(cursor, usuario_id)
            self._validar_relaciones(cursor, respuestas)

            ids_creados = []
            comentario_general = (
                comentario.strip()[:500]
                if comentario and comentario.strip()
                else None
            )

            for indice, respuesta in enumerate(respuestas):
                # El comentario general se guarda una sola vez.
                comentario_respuesta = (
                    comentario_general if indice == 0 else None
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

                fila = cursor.fetchone()
                ids_creados.append(
                    self._valor(fila, "respuesta_id", 0)
                )

            # Solo confirmar cuando las cinco inserciones funcionen.
            conn.commit()
            return ids_creados

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

            eliminado = cursor.fetchone()
            conn.commit()

            return eliminado is not None

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

            self._validar_usuario(cursor, respuesta.usuario_id)
            self._validar_relaciones(cursor, [respuesta])

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

            actualizado = cursor.fetchone()
            conn.commit()

            return actualizado is not None

        except Exception:
            if conn:
                conn.rollback()
            raise

        finally:
            if conn:
                conn.close()
