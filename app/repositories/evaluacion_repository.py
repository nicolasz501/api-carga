
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
        """Devuelve las evaluaciones para el panel administrativo."""
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
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM evaluaciones
                WHERE evaluacion_id = %s;
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
        Devuelve las evaluaciones visibles asignadas al docente.

        Incluye evaluaciones pendientes y completadas.
        El estado se calcula usando el último envío registrado.
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
                    e.visible_docentes,
                    COALESCE(preguntas.total_preguntas, 0)
                        AS total_preguntas,
                    COALESCE(ultimo.total_respuestas, 0)
                        AS total_respuestas_ultimo_intento,
                    COALESCE(ultimo.total_respuestas, 0) >= 5
                        AS completada,
                    CASE
                        WHEN COALESCE(ultimo.total_respuestas, 0) >= 5
                            THEN 'Completada'
                        ELSE 'Pendiente'
                    END AS estado_respuesta
                FROM evaluaciones e
                INNER JOIN carga_docente cd
                    ON cd.carga_id = e.carga_id
                LEFT JOIN LATERAL (
                    SELECT COUNT(*) AS total_preguntas
                    FROM preguntas_evaluacion pe
                    INNER JOIN preguntas p
                        ON p.pregunta_id = pe.pregunta_id
                    WHERE pe.evaluacion_id = e.evaluacion_id
                      AND pe.estado = TRUE
                      AND p.estado = TRUE
                ) preguntas ON TRUE
                LEFT JOIN LATERAL (
                    SELECT COUNT(*) AS total_respuestas
                    FROM respuestas r
                    INNER JOIN preguntas_evaluacion pe
                        ON pe.pregunta_evaluacion_id =
                           r.pregunta_evaluacion_id
                    WHERE r.usuario_id = %s
                      AND pe.evaluacion_id = e.evaluacion_id
                      AND r.created_at = (
                          SELECT MAX(r2.created_at)
                          FROM respuestas r2
                          INNER JOIN preguntas_evaluacion pe2
                              ON pe2.pregunta_evaluacion_id =
                                 r2.pregunta_evaluacion_id
                          WHERE r2.usuario_id = %s
                            AND pe2.evaluacion_id = e.evaluacion_id
                      )
                ) ultimo ON TRUE
                WHERE cd.user_id = %s
                  AND cd.estado = TRUE
                  AND e.estado = TRUE
                  AND e.visible_docentes = TRUE
                  AND COALESCE(e.titulo, '')
                      NOT ILIKE '[PLANTILLA]%%'
                  AND EXISTS (
                      SELECT 1
                      FROM preguntas_evaluacion pe
                      INNER JOIN preguntas p
                          ON p.pregunta_id = pe.pregunta_id
                      WHERE pe.evaluacion_id = e.evaluacion_id
                        AND pe.estado = TRUE
                        AND p.estado = TRUE
                  )
                ORDER BY e.evaluacion_id ASC;
            """, (usuario_id, usuario_id, usuario_id))

            return cursor.fetchall()

        except Exception:
            logger.exception(
                "Error al consultar evaluaciones del docente %s",
                usuario_id,
            )
            raise
        finally:
            if conn:
                conn.close()

    def listar_plantillas_autoevaluacion(self):
        """Lista las plantillas institucionales para administración."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    e.evaluacion_id,
                    e.carga_id,
                    COALESCE(e.periodo_id, cd.periodo_id) AS periodo_id,
                    e.tipo_evaluacion,
                    e.titulo,
                    e.fecha_envio,
                    e.estado,
                    e.visible_docentes,
                    (
                        SELECT COUNT(*)
                        FROM preguntas_evaluacion pe
                        WHERE pe.evaluacion_id = e.evaluacion_id
                          AND pe.estado = TRUE
                    ) AS total_preguntas
                FROM evaluaciones e
                LEFT JOIN carga_docente cd
                    ON cd.carga_id = e.carga_id
                WHERE UPPER(e.tipo_evaluacion) = 'AUTOEVALUACION'
                  AND COALESCE(e.titulo, '')
                      ILIKE '[PLANTILLA]%%'
                ORDER BY
                    COALESCE(e.periodo_id, cd.periodo_id) DESC,
                    e.evaluacion_id DESC;
            """)

            return cursor.fetchall()

        except Exception:
            logger.exception("Error al listar plantillas")
            raise
        finally:
            if conn:
                conn.close()

    def cambiar_estado_plantilla(
        self,
        evaluacion_id: int,
        estado: bool,
    ):
        """Activa o desactiva una plantilla institucional."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE evaluaciones
                SET estado = %s
                WHERE evaluacion_id = %s
                  AND UPPER(tipo_evaluacion) = 'AUTOEVALUACION'
                  AND COALESCE(titulo, '')
                      ILIKE '[PLANTILLA]%%'
                RETURNING
                    evaluacion_id,
                    estado,
                    COALESCE(
                        periodo_id,
                        (
                            SELECT cd.periodo_id
                            FROM carga_docente cd
                            WHERE cd.carga_id = evaluaciones.carga_id
                        )
                    ) AS periodo_id;
            """, (estado, evaluacion_id))

            resultado = cursor.fetchone()
            conn.commit()
            return resultado

        except Exception:
            if conn:
                conn.rollback()
            logger.exception(
                "Error al cambiar estado de plantilla %s",
                evaluacion_id,
            )
            raise
        finally:
            if conn:
                conn.close()

    def cambiar_visibilidad(
        self,
        evaluacion_id: int,
        visible_docentes: bool,
    ):
        """Publica u oculta una evaluación para los docentes."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE evaluaciones
                SET visible_docentes = %s
                WHERE evaluacion_id = %s
                  AND COALESCE(titulo, '')
                      NOT ILIKE '[PLANTILLA]%%'
                RETURNING evaluacion_id, visible_docentes;
            """, (visible_docentes, evaluacion_id))

            resultado = cursor.fetchone()
            conn.commit()
            return resultado

        except Exception:
            if conn:
                conn.rollback()
            logger.exception(
                "Error cambiando visibilidad de evaluación %s",
                evaluacion_id,
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
                LIMIT 1;
            """, (evaluacion_id, usuario_id))

            return cursor.fetchone() is not None

        except Exception:
            logger.exception("Error verificando pertenencia")
            raise
        finally:
            if conn:
                conn.close()

    def crear(self, evaluacion: Evaluacion):
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
                    %s, %s, %s, %s
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
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT carga_id
                FROM carga_docente
                WHERE carga_id = %s;
            """, (carga_id,))

            if cursor.fetchone() is None:
                return False

            cursor.execute("""
                UPDATE evaluaciones
                SET carga_id = %s
                WHERE evaluacion_id = %s
                RETURNING evaluacion_id;
            """, (carga_id, evaluacion_id))

            actualizado = cursor.fetchone()
            conn.commit()
            return actualizado is not None

        except Exception:
            if conn:
                conn.rollback()
            logger.exception("Error al asignar carga")
            raise
        finally:
            if conn:
                conn.close()

    def asignar_autoevaluacion_a_todos(
        self,
        plantilla_evaluacion_id: int,
    ):
        """
        Crea una evaluación individual por docente para el periodo
        de la plantilla y copia las relaciones de preguntas.
        """
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    e.evaluacion_id,
                    COALESCE(e.periodo_id, cd.periodo_id) AS periodo_id,
                    e.tipo_evaluacion,
                    e.titulo,
                    e.fecha_envio
                FROM evaluaciones e
                LEFT JOIN carga_docente cd
                    ON cd.carga_id = e.carga_id
                WHERE e.evaluacion_id = %s
                  AND e.estado = TRUE
                  AND UPPER(e.tipo_evaluacion) = 'AUTOEVALUACION'
                  AND COALESCE(e.titulo, '')
                      ILIKE '[PLANTILLA]%%';
            """, (plantilla_evaluacion_id,))

            plantilla = cursor.fetchone()

            if not plantilla:
                raise ValueError(
                    "No existe una plantilla activa de autoevaluación."
                )

            periodo_id = self._valor(plantilla, "periodo_id", 1)
            fecha_envio = self._valor(plantilla, "fecha_envio", 4)
            titulo = self._valor(plantilla, "titulo", 3) or "Autoevaluación"

            cursor.execute(
                "SELECT pg_advisory_xact_lock(1001, %s);",
                (periodo_id,),
            )

            cursor.execute("""
                SELECT pregunta_id
                FROM preguntas_evaluacion
                WHERE evaluacion_id = %s
                  AND estado = TRUE
                ORDER BY pregunta_evaluacion_id;
            """, (plantilla_evaluacion_id,))

            if not cursor.fetchall():
                raise ValueError(
                    "La plantilla no tiene preguntas activas."
                )

            cursor.execute("""
                SELECT DISTINCT ON (cd.user_id)
                    cd.user_id,
                    cd.carga_id
                FROM carga_docente cd
                INNER JOIN usuarios u
                    ON u.usuario_id = cd.user_id
                WHERE u.estado = TRUE
                  AND cd.estado = TRUE
                  AND cd.periodo_id = %s
                ORDER BY cd.user_id, cd.carga_id;
            """, (periodo_id,))

            docentes = cursor.fetchall()
            creadas = 0
            omitidas = 0

            for docente in docentes:
                usuario_id = self._valor(docente, "user_id", 0)
                carga_id = self._valor(docente, "carga_id", 1)

                cursor.execute("""
                    SELECT 1
                    FROM evaluaciones e
                    WHERE e.carga_id = %s
                      AND e.periodo_id = %s
                      AND UPPER(e.tipo_evaluacion) = 'AUTOEVALUACION'
                      AND e.evaluacion_id <> %s
                      AND COALESCE(e.titulo, '')
                          NOT ILIKE '[PLANTILLA]%%'
                    LIMIT 1;
                """, (carga_id, periodo_id, plantilla_evaluacion_id))

                if cursor.fetchone():
                    omitidas += 1
                    continue

                cursor.execute("""
                    INSERT INTO evaluaciones (
                        carga_id,
                        periodo_id,
                        tipo_evaluacion,
                        titulo,
                        fecha_envio,
                        estado,
                        visible_docentes
                    )
                    VALUES (%s, %s, 'AUTOEVALUACION', %s, %s, TRUE, TRUE)
                    RETURNING evaluacion_id;
                """, (
                    carga_id,
                    periodo_id,
                    "Autoevaluación individual",
                    fecha_envio,
                ))

                nueva = cursor.fetchone()
                nuevo_id = self._valor(nueva, "evaluacion_id", 0)

                cursor.execute("""
                    INSERT INTO preguntas_evaluacion (
                        evaluacion_id,
                        pregunta_id,
                        numero_orden,
                        estado
                    )
                    SELECT
                        %s,
                        pregunta_id,
                        numero_orden,
                        TRUE
                    FROM preguntas_evaluacion
                    WHERE evaluacion_id = %s
                      AND estado = TRUE
                    ORDER BY pregunta_evaluacion_id;
                """, (nuevo_id, plantilla_evaluacion_id))

                creadas += 1

            conn.commit()

            return {
                "mensaje": "Asignación masiva finalizada.",
                "periodo_id": periodo_id,
                "evaluaciones_creadas": creadas,
                "docentes_omitidos": omitidas,
            }

        except Exception:
            if conn:
                conn.rollback()
            logger.exception("Error en asignación masiva")
            raise
        finally:
            if conn:
                conn.close()

    def eliminar(self, evaluacion_id: int):
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
            logger.exception("Error al eliminar evaluación")
            raise
        finally:
            if conn:
                conn.close()

    def actualizar(self, evaluacion_id: int, evaluacion: Evaluacion):
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
            logger.exception("Error al actualizar evaluación")
            raise
        finally:
            if conn:
                conn.close()
