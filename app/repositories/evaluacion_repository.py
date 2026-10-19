from app.core.database import Database
from app.models.Evaluacion import Evaluacion

# Columnas devueltas con los alias que espera el frontend.
_COLUMNAS = """
    e.*,
    e.id_evaluaciones AS evaluacion_id,
    e.id_carga AS carga_id
"""


class EvaluacionRepository:

    def __init__(self):
        self.db = Database()

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def obtener_todos(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute(f"""
                SELECT {_COLUMNAS}
                FROM evaluaciones e
                ORDER BY e.id_evaluaciones ASC;
            """)

            return cursor.fetchall()

        except Exception as e:
            print(f"Error al obtener evaluaciones: {e}")
            raise

        finally:
            if conn:
                conn.close()

    def obtener_por_id(self, evaluacion_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute(f"""
                SELECT {_COLUMNAS}
                FROM evaluaciones e
                WHERE e.id_evaluaciones = %s;
            """, (evaluacion_id,))

            return cursor.fetchone()

        except Exception as e:
            print(f"Error al obtener evaluación: {e}")
            raise

        finally:
            if conn:
                conn.close()

    def obtener_para_docente(self, usuario_id: int):
        """
        Devuelve únicamente las autoevaluaciones activas asignadas al
        docente que aún tienen preguntas activas sin responder.

        Las evaluaciones cuyo título comienza con [PLANTILLA] nunca se
        muestran como asignaciones.
        """
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute(f"""
                SELECT {_COLUMNAS}
                FROM evaluaciones e
                INNER JOIN carga_docente cd
                    ON cd.id_carga = e.id_carga
                WHERE cd.id_usuario = %s
                  AND cd.estado = TRUE
                  AND e.estado = TRUE
                  AND e.tipo_evaluacion = 'AUTOEVALUACION'
                  AND e.titulo NOT ILIKE '[PLANTILLA]%%'
                  AND EXISTS (
                      SELECT 1
                      FROM preguntas_evaluaciones pe
                      WHERE pe.id_evaluacion = e.id_evaluaciones
                        AND pe.estado = TRUE
                        AND NOT EXISTS (
                            SELECT 1
                            FROM respuestas r
                            WHERE r.id_pregunta_evaluacion =
                                  pe.id_pregunta_evaluacion
                              AND r.id_usuario = %s
                              AND r.estado = TRUE
                        )
                  )
                ORDER BY e.id_evaluaciones ASC;
            """, (usuario_id, usuario_id))

            return cursor.fetchall()

        except Exception as e:
            print(
                f"Error al consultar evaluaciones del docente "
                f"{usuario_id}: {e}"
            )
            raise

        finally:
            if conn:
                conn.close()

    def pertenece_a_docente(self, evaluacion_id: int, usuario_id: int) -> bool:
        """True si la evaluación está ligada a una carga del docente."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 1
                FROM evaluaciones e
                INNER JOIN carga_docente cd
                    ON cd.id_carga = e.id_carga
                WHERE e.id_evaluaciones = %s
                  AND cd.id_usuario = %s
                LIMIT 1;
            """, (evaluacion_id, usuario_id))

            return cursor.fetchone() is not None

        except Exception as e:
            print(f"Error al verificar pertenencia de evaluación: {e}")
            raise

        finally:
            if conn:
                conn.close()

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------
    def crear(self, evaluacion: Evaluacion):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO evaluaciones (
                    id_carga,
                    tipo_evaluacion,
                    titulo,
                    fecha_envio,
                    estado
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id_evaluaciones;
            """, (
                evaluacion.carga_id,
                evaluacion.tipo_evaluacion,
                evaluacion.titulo,
                evaluacion.fecha_envio,
                evaluacion.estado
            ))

            fila = cursor.fetchone()
            conn.commit()

            return fila["id_evaluaciones"] if fila else None

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error al crear evaluación: {e}")
            raise

        finally:
            if conn:
                conn.close()

    def asignar_carga(self, evaluacion_id: int, carga_id: int):
        """Asocia una evaluación a una carga docente existente."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id_carga
                FROM carga_docente
                WHERE id_carga = %s;
            """, (carga_id,))

            if not cursor.fetchone():
                return False

            cursor.execute("""
                UPDATE evaluaciones
                SET id_carga = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id_evaluaciones = %s
                RETURNING id_evaluaciones;
            """, (carga_id, evaluacion_id))

            actualizado = cursor.fetchone()
            conn.commit()

            return actualizado is not None

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error al asignar evaluación: {e}")
            raise

        finally:
            if conn:
                conn.close()

    def asignar_autoevaluacion_a_todos(self, plantilla_evaluacion_id: int):
        """
        Crea una autoevaluación por cada docente activo con carga activa
        en el periodo de la plantilla y copia las preguntas de la plantilla.

        - El periodo se obtiene de carga_docente.id_periodo.
        - Se omiten los docentes que ya tienen una autoevaluación activa
          (distinta de la plantilla) en ese periodo.
        - Un lock por periodo evita ejecuciones concurrentes duplicadas.
        - Todo ocurre en una sola transacción.
        """
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # 1. Plantilla y su periodo (vía carga_docente).
            cursor.execute("""
                SELECT
                    e.titulo,
                    e.tipo_evaluacion,
                    e.fecha_envio,
                    cd.id_periodo
                FROM evaluaciones e
                INNER JOIN carga_docente cd
                    ON cd.id_carga = e.id_carga
                WHERE e.id_evaluaciones = %s
                  AND e.estado = TRUE;
            """, (plantilla_evaluacion_id,))

            plantilla = cursor.fetchone()

            if not plantilla:
                raise ValueError(
                    "No existe una evaluación activa para utilizar "
                    "como plantilla."
                )

            if str(plantilla["tipo_evaluacion"]).upper() != "AUTOEVALUACION":
                raise ValueError(
                    "La plantilla debe ser de tipo AUTOEVALUACION."
                )

            periodo_id = plantilla["id_periodo"]
            fecha_envio = plantilla["fecha_envio"]
            titulo_plantilla = plantilla["titulo"] or "Autoevaluación"

            # 2. Serializar ejecuciones por periodo (se libera al terminar
            #    la transacción).
            cursor.execute(
                "SELECT pg_advisory_xact_lock(1001, %s);", (periodo_id,)
            )

            # 3. La plantilla debe tener preguntas activas.
            cursor.execute("""
                SELECT COUNT(*) AS n
                FROM preguntas_evaluaciones
                WHERE id_evaluacion = %s
                  AND estado = TRUE;
            """, (plantilla_evaluacion_id,))

            if cursor.fetchone()["n"] == 0:
                raise ValueError(
                    "La evaluación plantilla no tiene preguntas activas."
                )

            # 4. Marcar la plantilla antes de insertar, para que no se
            #    muestre al docente ni cuente como asignación.
            if not str(titulo_plantilla).upper().startswith("[PLANTILLA]"):
                cursor.execute("""
                    UPDATE evaluaciones
                    SET titulo = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id_evaluaciones = %s;
                """, (f"[PLANTILLA] {titulo_plantilla}",
                      plantilla_evaluacion_id))

            # 5. Total de docentes elegibles (para calcular los omitidos).
            cursor.execute("""
                SELECT COUNT(DISTINCT cd.id_usuario) AS total
                FROM carga_docente cd
                INNER JOIN usuarios u
                    ON u.id_usuario = cd.id_usuario
                   AND u.estado = TRUE
                WHERE cd.id_periodo = %s
                  AND cd.estado = TRUE;
            """, (periodo_id,))

            total = cursor.fetchone()["total"]

            # 6. Crear las evaluaciones y copiar las preguntas.
            cursor.execute("""
                WITH docentes AS (
                    SELECT DISTINCT ON (cd.id_usuario)
                        cd.id_usuario,
                        cd.id_carga
                    FROM carga_docente cd
                    INNER JOIN usuarios u
                        ON u.id_usuario = cd.id_usuario
                       AND u.estado = TRUE
                    WHERE cd.id_periodo = %s
                      AND cd.estado = TRUE
                      AND NOT EXISTS (
                          SELECT 1
                          FROM evaluaciones e2
                          INNER JOIN carga_docente cd2
                              ON cd2.id_carga = e2.id_carga
                          WHERE cd2.id_usuario = cd.id_usuario
                            AND cd2.id_periodo = %s
                            AND e2.tipo_evaluacion = 'AUTOEVALUACION'
                            AND e2.estado = TRUE
                            AND e2.id_evaluaciones <> %s
                            AND e2.titulo NOT ILIKE '[PLANTILLA]%%'
                      )
                    ORDER BY cd.id_usuario, cd.id_carga
                ),
                nuevas AS (
                    INSERT INTO evaluaciones (
                        id_carga,
                        tipo_evaluacion,
                        titulo,
                        fecha_envio,
                        estado
                    )
                    SELECT
                        id_carga,
                        'AUTOEVALUACION',
                        'Autoevaluación',
                        %s,
                        TRUE
                    FROM docentes
                    RETURNING id_evaluaciones
                ),
                copiadas AS (
                    INSERT INTO preguntas_evaluaciones (
                        id_preguntas,
                        id_evaluacion,
                        numero_orden,
                        estado
                    )
                    SELECT
                        pe.id_preguntas,
                        n.id_evaluaciones,
                        pe.numero_orden,
                        TRUE
                    FROM nuevas n
                    CROSS JOIN preguntas_evaluaciones pe
                    WHERE pe.id_evaluacion = %s
                      AND pe.estado = TRUE
                    RETURNING 1
                )
                SELECT (SELECT COUNT(*) FROM nuevas) AS creadas;
            """, (
                periodo_id,
                periodo_id,
                plantilla_evaluacion_id,
                fecha_envio,
                plantilla_evaluacion_id
            ))

            creadas = cursor.fetchone()["creadas"]

            conn.commit()

            return {
                "mensaje": "Asignación masiva finalizada.",
                "periodo_id": periodo_id,
                "evaluaciones_creadas": creadas,
                "docentes_omitidos_por_ya_tener_autoevaluacion":
                    total - creadas
            }

        except Exception as e:
            if conn:
                conn.rollback()

            print(f"Error en asignación masiva de autoevaluaciones: {e}")
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
                WHERE id_evaluaciones = %s
                RETURNING id_evaluaciones;
            """, (evaluacion_id,))

            eliminado = cursor.fetchone()
            conn.commit()

            return eliminado is not None

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error al eliminar evaluación: {e}")
            return False

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
                SET id_carga = %s,
                    tipo_evaluacion = %s,
                    titulo = %s,
                    fecha_envio = %s,
                    estado = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id_evaluaciones = %s
                RETURNING id_evaluaciones;
            """, (
                evaluacion.carga_id,
                evaluacion.tipo_evaluacion,
                evaluacion.titulo,
                evaluacion.fecha_envio,
                evaluacion.estado,
                evaluacion_id
            ))

            actualizado = cursor.fetchone()
            conn.commit()

            return actualizado is not None

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error al actualizar evaluación: {e}")
            return False

        finally:
            if conn:
                conn.close()