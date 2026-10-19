
import logging
from typing import Optional

from app.core.database import Database
from app.models.Respuesta import Respuesta

logger = logging.getLogger(__name__)


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
                ORDER BY r.created_at DESC, r.respuesta_id DESC;
            """)

            return cursor.fetchall()

        except Exception:
            logger.exception("Error al obtener todas las respuestas")
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

        except Exception:
            logger.exception(
                "Error al consultar la respuesta %s",
                respuesta_id,
            )
            raise

        finally:
            if conn:
                conn.close()

    def obtener_ultima_respuesta(
        self,
        usuario_id: int,
        evaluacion_id: int,
    ):
        """
        Devuelve la respuesta más reciente del usuario para una evaluación.
        Si nunca respondió, devuelve None.
        """
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
                    pe.evaluacion_id
                FROM respuestas r
                JOIN preguntas_evaluacion pe
                    ON pe.pregunta_evaluacion_id =
                       r.pregunta_evaluacion_id
                WHERE r.usuario_id = %s
                  AND pe.evaluacion_id = %s
                ORDER BY
                    r.created_at DESC NULLS LAST,
                    r.respuesta_id DESC
                LIMIT 1;
            """, (usuario_id, evaluacion_id))

            return cursor.fetchone()

        except Exception:
            logger.exception(
                "Error consultando última respuesta del usuario %s "
                "para la evaluación %s",
                usuario_id,
                evaluacion_id,
            )
            raise

        finally:
            if conn:
                conn.close()

    def obtener_estado_evaluaciones_usuario(self, usuario_id: int):
        """
        Devuelve el estado de cada evaluación del usuario.

        Una evaluación se considera completada cuando existen cinco
        respuestas en su último intento.
        """
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                WITH intentos AS (
                    SELECT
                        pe.evaluacion_id,
                        r.usuario_id,
                        r.created_at,
                        r.respuesta_id,
                        COUNT(*) OVER (
                            PARTITION BY
                                pe.evaluacion_id,
                                r.usuario_id,
                                r.created_at
                        ) AS respuestas_en_mismo_instante
                    FROM respuestas r
                    JOIN preguntas_evaluacion pe
                        ON pe.pregunta_evaluacion_id =
                           r.pregunta_evaluacion_id
                    WHERE r.usuario_id = %s
                ),
                resumen AS (
                    SELECT
                        evaluacion_id,
                        usuario_id,
                        COUNT(*) AS total_respuestas
                    FROM respuestas r
                    JOIN preguntas_evaluacion pe
                        ON pe.pregunta_evaluacion_id =
                           r.pregunta_evaluacion_id
                    WHERE r.usuario_id = %s
                    GROUP BY evaluacion_id, usuario_id
                )
                SELECT
                    evaluacion_id,
                    usuario_id,
                    total_respuestas,
                    (total_respuestas >= 5) AS completada
                FROM resumen
                ORDER BY evaluacion_id;
            """, (usuario_id, usuario_id))

            return cursor.fetchall()

        except Exception:
            logger.exception(
                "Error consultando estado de evaluaciones del usuario %s",
                usuario_id,
            )
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
            raise ValueError("El usuario no existe o está inactivo.")

    def _validar_relaciones(self, cursor, respuestas):
        """
        Comprueba que las respuestas correspondan a preguntas activas
        de una misma evaluación. Devuelve evaluacion_id.
        """

        if not respuestas:
            raise ValueError("Debes proporcionar respuestas.")

        relaciones = [
            getattr(r, "pregunta_evaluacion_id", None)
            for r in respuestas
        ]
        preguntas = [
            getattr(r, "pregunta_id", None)
            for r in respuestas
        ]

        if any(
            valor is None
            or isinstance(valor, bool)
            or not isinstance(valor, int)
            or valor <= 0
            for valor in relaciones + preguntas
        ):
            raise ValueError(
                "Cada respuesta debe incluir identificadores válidos."
            )

        if len(set(relaciones)) != len(relaciones):
            raise ValueError("No puedes repetir relaciones de preguntas.")

        if len(set(preguntas)) != len(preguntas):
            raise ValueError("No puedes repetir preguntas en un envío.")

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
              AND p.estado = TRUE;
        """, (relaciones,))

        filas = cursor.fetchall()

        if len(filas) != len(respuestas):
            raise ValueError(
                "Una o más preguntas no existen o están inactivas."
            )

        datos = {
            (
                self._valor(fila, "pregunta_evaluacion_id", 0),
                self._valor(fila, "pregunta_id", 1),
                self._valor(fila, "evaluacion_id", 2),
            )
            for fila in filas
        }

        evaluacion_ids = {dato[2] for dato in datos}

        if None in evaluacion_ids or len(evaluacion_ids) != 1:
            raise ValueError(
                "Todas las preguntas deben pertenecer a la misma evaluación."
            )

        esperadas = {
            (r.pregunta_evaluacion_id, r.pregunta_id)
            for r in respuestas
        }
        encontradas = {(dato[0], dato[1]) for dato in datos}

        if esperadas != encontradas:
            raise ValueError(
                "Las preguntas enviadas no coinciden con sus relaciones."
            )

        for respuesta in respuestas:
            puntaje = respuesta.puntaje

            if (
                isinstance(puntaje, bool)
                or not isinstance(puntaje, int)
                or not 1 <= puntaje <= 5
            ):
                raise ValueError(
                    "Cada puntaje debe ser un entero entre 1 y 5."
                )

        evaluacion_id = next(iter(evaluacion_ids))

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
            total = int(self._valor(fila, "total", 0) or 0)

            if total != 5:
                raise ValueError(
                    "La evaluación debe tener exactamente "
                    "cinco preguntas activas."
                )

        return evaluacion_id

    def crear(self, respuesta: Respuesta):
        conn = None

        try:
            if not respuesta.usuario_id:
                raise ValueError("Se necesita el usuario evaluador.")

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
                respuesta.estado,
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
        comentario: Optional[str] = None,
        evaluacion_id: Optional[int] = None,
    ):
        """
        Registra cinco respuestas dentro de una transacción.

        Permite varios envíos de una misma evaluación. Cada envío
        se conserva; el frontend debe consultar el último intento
        para mostrar el estado actualizado.
        """
        conn = None

        try:
            if (
                isinstance(usuario_id, bool)
                or not isinstance(usuario_id, int)
                or usuario_id <= 0
            ):
                raise ValueError("El usuario evaluador no es válido.")

            if not isinstance(respuestas, (list, tuple)) or len(respuestas) != 5:
                raise ValueError(
                    "La evaluación debe contener exactamente cinco respuestas."
                )

            conn = self.db.get_connection()
            cursor = conn.cursor()

            self._validar_usuario(cursor, usuario_id)

            evaluacion_id_preguntas = self._validar_relaciones(
                cursor,
                respuestas,
            )

            if (
                evaluacion_id is not None
                and evaluacion_id != evaluacion_id_preguntas
            ):
                raise ValueError(
                    "La evaluación indicada no coincide con las preguntas."
                )

            evaluacion_id = evaluacion_id_preguntas

            # Serializa envíos simultáneos del mismo usuario y evaluación.
            cursor.execute(
                "SELECT pg_advisory_xact_lock(%s, %s);",
                (usuario_id, evaluacion_id),
            )

            # Comprueba que la evaluación esté activa y corresponda
            # a una carga activa del docente.
            cursor.execute("""
                SELECT e.evaluacion_id
                FROM evaluaciones e
                WHERE e.evaluacion_id = %s
                  AND e.estado = TRUE
                  AND EXISTS (
                      SELECT 1
                      FROM carga_docente cd
                      WHERE cd.carga_id = e.carga_id
                        AND cd.user_id = %s
                        AND cd.estado = TRUE
                  )
                LIMIT 1;
            """, (evaluacion_id, usuario_id))

            if cursor.fetchone() is None:
                raise ValueError(
                    "La evaluación está inactiva o no está asignada "
                    "a una carga docente activa del usuario."
                )

            comentario_general = (
                comentario.strip()[:500]
                if comentario and comentario.strip()
                else None
            )

            ids_creados = []

            for indice, respuesta in enumerate(respuestas):
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
                    respuesta.estado,
                ))

                fila = cursor.fetchone()
                ids_creados.append(
                    self._valor(fila, "respuesta_id", 0)
                )

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
                raise ValueError("Se necesita el usuario evaluador.")

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
                respuesta_id,
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
