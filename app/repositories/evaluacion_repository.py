
import logging

from app.core.database import Database
from app.models.Evaluacion import Evaluacion

logger = logging.getLogger(__name__)


class EvaluacionRepository:

    def __init__(self):
        self.db = Database()

    @staticmethod
    def _valor(fila, columna, indice=0):
        if fila is None:
            return None

        if isinstance(fila, dict):
            return fila.get(columna)

        return fila[indice]

    def obtener_todos(self):
        """Devuelve todas las evaluaciones registradas."""
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    e.*,
                    (
                        SELECT COUNT(*)
                        FROM preguntas_evaluacion pe
                        WHERE pe.evaluacion_id = e.evaluacion_id
                          AND pe.estado = TRUE
                    ) AS total_preguntas
                FROM evaluaciones e
                ORDER BY e.evaluacion_id ASC;
            """)

            return cursor.fetchall()

        except Exception:
            logger.exception("Error al obtener evaluaciones")
            raise

        finally:
            if conn:
                conn.close()

    def obtener_por_id(self, evaluacion_id: int):
        """Obtiene una evaluación por su identificador."""
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    e.*,
                    (
                        SELECT COUNT(*)
                        FROM preguntas_evaluacion pe
                        WHERE pe.evaluacion_id = e.evaluacion_id
                          AND pe.estado = TRUE
                    ) AS total_preguntas
                FROM evaluaciones e
                WHERE e.evaluacion_id = %s;
            """, (evaluacion_id,))

            return cursor.fetchone()

        except Exception:
            logger.exception(
                "Error al obtener evaluación %s",
                evaluacion_id,
            )
            raise

        finally:
            if conn:
                conn.close()

    def obtener_para_docente(self, usuario_id: int):
        """
        Obtiene las evaluaciones activas asociadas a las cargas
        docentes activas del usuario.
        """
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT
                    e.evaluacion_id,
                    e.carga_id,
                    COALESCE(e.periodo_id, cd.periodo_id) AS periodo_id,
                    e.tipo_evaluacion,
                    e.titulo,
                    e.fecha_envio,
                    e.estado,
                    (
                        SELECT COUNT(*)
                        FROM preguntas_evaluacion pe
                        INNER JOIN preguntas p
                            ON p.pregunta_id = pe.pregunta_id
                        WHERE pe.evaluacion_id = e.evaluacion_id
                          AND pe.estado = TRUE
                          AND p.estado = TRUE
                    ) AS total_preguntas,
                    (
                        SELECT COUNT(DISTINCT pe.pregunta_evaluacion_id)
                        FROM respuestas r
                        INNER JOIN preguntas_evaluacion pe
                            ON pe.pregunta_evaluacion_id =
                               r.pregunta_evaluacion_id
                        WHERE r.usuario_id = %s
                          AND pe.evaluacion_id = e.evaluacion_id
                          AND r.estado = TRUE
                    ) AS total_respuestas
                FROM evaluaciones e
                INNER JOIN carga_docente cd
                    ON cd.carga_id = e.carga_id
                WHERE cd.user_id = %s
                  AND cd.estado = TRUE
                  AND e.estado = TRUE
                ORDER BY e.evaluacion_id ASC;
            """, (usuario_id, usuario_id))

            evaluaciones = cursor.fetchall()

            return evaluaciones

        except Exception:
            logger.exception(
                "Error al obtener evaluaciones del docente %s",
                usuario_id,
            )
            raise

        finally:
            if conn:
                conn.close()

    def pertenece_a_docente(
        self,
        evaluacion_id: int,
        usuario_id: int,
    ) -> bool:
        """Comprueba si la evaluación pertenece a una carga activa del docente."""
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 1
                FROM evaluaciones e
                INNER JOIN carga_docente cd
                    ON cd.carga_id = e.carga_id
                WHERE e.evaluacion_id = %s
                  AND cd.user_id = %s
                  AND cd.estado = TRUE
                  AND e.estado = TRUE
                LIMIT 1;
            """, (evaluacion_id, usuario_id))

            return cursor.fetchone() is not None

        except Exception:
            logger.exception(
                "Error al verificar la pertenencia de la evaluación"
            )
            raise

        finally:
            if conn:
                conn.close()

    def crear(self, evaluacion: Evaluacion):
        """Crea una evaluación asociada a una carga docente existente."""
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO evaluaciones (
                    carga_id,
                    periodo_id,
                    tipo_evaluacion,
                    titulo,
                    fecha_envio,
                    estado
                )
                VALUES (
                    %s,
                    COALESCE(
                        %s,
                        (
                            SELECT periodo_id
                            FROM carga_docente
                            WHERE carga_id = %s
                        )
                    ),
                    %s,
                    %s,
                    %s,
                    %s
                )
                RETURNING evaluacion_id;
            """, (
                evaluacion.carga_id,
                evaluacion.periodo_id,
                evaluacion.carga_id,
                evaluacion.tipo_evaluacion,
                evaluacion.titulo,
                evaluacion.fecha_envio,
                evaluacion.estado,
            ))

            fila = cursor.fetchone()
            nuevo_id = self._valor(fila, "evaluacion_id", 0)

            if nuevo_id is None:
                raise ValueError("No se pudo crear la evaluación.")

            conn.commit()
            return nuevo_id

        except Exception:
            if conn:
                conn.rollback()

            logger.exception("Error al crear evaluación")
            raise

        finally:
            if conn:
                conn.close()

    def asignar_carga(self, evaluacion_id: int, carga_id: int):
        """Asigna una evaluación a una carga docente existente."""
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT periodo_id
                FROM carga_docente
                WHERE carga_id = %s
                  AND estado = TRUE;
            """, (carga_id,))

            carga = cursor.fetchone()

            if carga is None:
                return False

            periodo_carga = self._valor(carga, "periodo_id", 0)

            cursor.execute("""
                UPDATE evaluaciones
                SET carga_id = %s,
                    periodo_id = COALESCE(periodo_id, %s)
                WHERE evaluacion_id = %s
                RETURNING evaluacion_id;
            """, (carga_id, periodo_carga, evaluacion_id))

            actualizado = cursor.fetchone()
            conn.commit()

            return actualizado is not None

        except Exception:
            if conn:
                conn.rollback()

            logger.exception("Error al asignar carga docente")
            raise

        finally:
            if conn:
                conn.close()

    def actualizar(self, evaluacion_id: int, evaluacion: Evaluacion):
        """Actualiza los datos de una evaluación."""
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE evaluaciones
                SET carga_id = %s,
                    periodo_id = COALESCE(%s, periodo_id),
                    tipo_evaluacion = %s,
                    titulo = %s,
                    fecha_envio = %s,
                    estado = %s
                WHERE evaluacion_id = %s
                RETURNING evaluacion_id;
            """, (
                evaluacion.carga_id,
                evaluacion.periodo_id,
                evaluacion.tipo_evaluacion,
                evaluacion.titulo,
                evaluacion.fecha_envio,
                evaluacion.estado,
                evaluacion_id,
            ))

            actualizado = cursor.fetchone()
            conn.commit()

            return actualizado is not None

        except Exception:
            if conn:
                conn.rollback()

            logger.exception(
                "Error al actualizar evaluación %s",
                evaluacion_id,
            )
            raise

        finally:
            if conn:
                conn.close()

    def eliminar(self, evaluacion_id: int):
        """Elimina una evaluación si las relaciones de la base de datos lo permiten."""
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM evaluaciones
                WHERE evaluacion_id = %s
                RETURNING evaluacion_id;
            """, (evaluacion_id,))

            eliminado = cursor.fetchone()
            conn.commit()

            return eliminado is not None

        except Exception:
            if conn:
                conn.rollback()

            logger.exception(
                "Error al eliminar evaluación %s",
                evaluacion_id,
            )
            raise

        finally:
            if conn:
                conn.close()
