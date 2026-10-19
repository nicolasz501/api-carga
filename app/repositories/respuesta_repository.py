
from app.core.database import Database
from app.models.Respuesta import Respuesta


class RespuestaRepository:

    def __init__(self):
        self.db = Database()

    @staticmethod
    def _valor(fila, columna, indice):
        """Compatible con cursores que devuelven diccionarios o tuplas."""
        if fila is None:
            return None

        if isinstance(fila, dict):
            return fila.get(columna)

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
        """Verifica que el usuario exista y esté activo."""

        cursor.execute("""
            SELECT usuario_id
            FROM usuarios
            WHERE usuario_id = %s
              AND estado = TRUE;
        """, (usuario_id,))

        if cursor.fetchone() is None:
            raise ValueError(
                "El usuario no existe o está inactivo."
            )

    def _validar_relaciones(self, cursor, respuestas):
        """
        Valida las preguntas de una evaluación.

        Para el lote:
        - Deben existir exactamente cinco respuestas.
        - No puede haber preguntas ni relaciones repetidas.
        - Las preguntas y relaciones deben estar activas.
        - Las cinco relaciones deben pertenecer a la misma evaluación.
        - La evaluación debe tener exactamente cinco preguntas activas.

        Retorna el evaluacion_id.
        """

        if not respuestas:
            raise ValueError(
                "Debes proporcionar al menos una respuesta."
            )

        relaciones = [
            getattr(r, "pregunta_evaluacion_id", None)
            for r in respuestas
        ]

        preguntas = [
            getattr(r, "pregunta_id", None)
            for r in respuestas
        ]

        # Comprobar identificadores.
        if any(
            identificador is None or identificador <= 0
            for identificador in relaciones + preguntas
        ):
            raise ValueError(
                "Cada respuesta debe incluir identificadores "
                "válidos de pregunta y relación."
            )

        # Validar que no se repitan relaciones.
        if len(set(relaciones)) != len(relaciones):
            raise ValueError(
                "No puedes repetir relaciones de preguntas."
            )

        # Validar que no se repitan preguntas.
        if len(set(preguntas)) != len(preguntas):
            raise ValueError(
                "No puedes repetir preguntas en una evaluación."
            )

        cursor.execute("""
            SELECT
                pe.pregunta_evaluacion_id,
                pe.pregunta_id,
                pe.evaluacion_id
            FROM preguntas_evaluacion pe
            JOIN preguntas p
                ON p.pregunta_id = pe.pregunta_id
            WHERE pe.pregunta_evaluacion_id = ANY(%s)
              AND pe.estado = TRUE
              AND p.estado = TRUE
            ORDER BY pe.pregunta_evaluacion_id;
        """, (relaciones,))

        filas = cursor.fetchall()

        if len(filas) != len(respuestas):
            raise ValueError(
                "Una o más preguntas no existen, están inactivas "
                "o no tienen una relación válida."
            )

        datos = {
            (
                self._valor(fila, "pregunta_evaluacion_id", 0),
                self._valor(fila, "pregunta_id", 1),
                self._valor(fila, "evaluacion_id", 2)
            )
            for fila in filas
        }

        # Asegurar que todas las respuestas sean de la misma evaluación.
        evaluacion_ids = {
            dato[2] for dato in datos
        }

        if None in evaluacion_ids or len(evaluacion_ids) != 1:
            raise ValueError(
                "Todas las preguntas deben pertenecer a la misma evaluación."
            )

        esperadas = {
            (r.pregunta_evaluacion_id, r.pregunta_id)
            for r in respuestas
        }

        encontradas = {
            (dato[0], dato[1])
            for dato in datos
        }

        if esperadas != encontradas:
            raise ValueError(
                "Las preguntas enviadas no coinciden con sus relaciones."
            )

        # Validar puntajes.
        for respuesta in respuestas:
            puntaje = respuesta.puntaje

            if (
                puntaje is None
                or isinstance(puntaje, bool)
                or not isinstance(puntaje, int)
                or not 1 <= puntaje <= 5
            ):
                raise ValueError(
                    "Cada puntaje debe ser un número entero entre 1 y 5."
                )

        evaluacion_id = next(iter(evaluacion_ids))

        # Para el lote, verificar que existan exactamente cinco preguntas activas.
        if len(respuestas) == 5:
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM preguntas_evaluacion pe
                JOIN preguntas p
                    ON p.pregunta_id = pe.pregunta_id
                WHERE pe.evaluacion_id = %s
                  AND pe.estado = TRUE
                  AND p.estado = TRUE;
            """, (evaluacion_id,))

            fila = cursor.fetchone()
            total = int(
                self._valor(fila, "total", 0) or 0
            )

            if total != 5:
                raise ValueError(
                    "La evaluación debe tener exactamente "
                    "cinco preguntas activas."
                )

        return evaluacion_id

    def crear(self, respuesta: Respuesta):
        """
        Crea una respuesta individual.

        Para evaluaciones que exigen cinco preguntas, utiliza
        crear_lote desde el endpoint de envío completo.
        """

        conn = None

        try:
            if not respuesta.usuario_id:
                raise ValueError(
                    "Se necesita el usuario que realiza la evaluación."
                )

            conn = self.db.get_connection()
            cursor = conn.cursor()

            self._validar_usuario(
                cursor,
                respuesta.usuario_id
            )

            self._validar_relaciones(
                cursor,
                [respuesta]
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
                respuesta.usuario_id,
                respuesta.puntaje,
                respuesta.comentario,
                respuesta.estado
            ))

            fila = cursor.fetchone()
            nuevo_id = self._valor(
                fila,
                "respuesta_id",
                0
            )

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
        """
        Guarda las cinco respuestas de una evaluación en una transacción.

        La evaluación debe estar activa y asociada a una carga docente
        cuyo user_id corresponda al usuario que responde.

        El comentario general se guarda solamente en la primera respuesta.
        """

        conn = None

        try:
            if (
                usuario_id is None
                or isinstance(usuario_id, bool)
                or not isinstance(usuario_id, int)
                or usuario_id <= 0
            ):
                raise ValueError(
                    "El usuario evaluador no es válido."
                )

            if not isinstance(respuestas, (list, tuple)) or len(respuestas) != 5:
                raise ValueError(
                    "La evaluación debe contener exactamente cinco respuestas."
                )

            conn = self.db.get_connection()
            cursor = conn.cursor()

            # Verificar que el usuario esté activo.
            self._validar_usuario(cursor, usuario_id)

            # Validar relaciones y obtener la evaluación.
            evaluacion_id = self._validar_relaciones(
                cursor,
                respuestas
            )

            # Bloquear envíos concurrentes para este usuario y evaluación.
            cursor.execute("""
                SELECT pg_advisory_xact_lock(%s, %s);
            """, (usuario_id, evaluacion_id))

            # Confirmar que la evaluación esté activa y asignada al usuario.
            cursor.execute("""
                SELECT e.evaluacion_id
                FROM evaluaciones e
                JOIN carga_docente cd
                    ON cd.carga_id = e.carga_id
                WHERE e.evaluacion_id = %s
                  AND e.estado = TRUE
                  AND cd.user_id = %s
                LIMIT 1;
            """, (evaluacion_id, usuario_id))

            if cursor.fetchone() is None:
                raise ValueError(
                    "Esta evaluación no está asignada a tu carga docente."
                )

            # No permitir un segundo envío de la misma evaluación.
            cursor.execute("""
                SELECT 1
                FROM respuestas r
                JOIN preguntas_evaluacion pe
                    ON pe.pregunta_evaluacion_id =
                       r.pregunta_evaluacion_id
                WHERE pe.evaluacion_id = %s
                  AND r.usuario_id = %s
                LIMIT 1;
            """, (evaluacion_id, usuario_id))

            if cursor.fetchone() is not None:
                raise ValueError(
                    "Ya respondió esta evaluación. "
                    "No se permiten envíos duplicados."
                )

            comentario_general = (
                comentario.strip()[:500]
                if comentario and comentario.strip()
                else None
            )

            ids_creados = []

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

            # Guardar las cinco respuestas como una sola operación.
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
            if not respuesta.usuario_id:
                raise ValueError(
                    "Se necesita el usuario que realiza la evaluación."
                )

            conn = self.db.get_connection()
            cursor = conn.cursor()

            self._validar_usuario(
                cursor,
                respuesta.usuario_id
            )

            self._validar_relaciones(
                cursor,
                [respuesta]
            )

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
