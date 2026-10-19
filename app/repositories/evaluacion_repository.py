
from app.core.database import Database
from app.models.Evaluacion import Evaluacion


class EvaluacionRepository:

    def __init__(self):
        self.db = Database()

    def obtener_todos(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM evaluaciones
                ORDER BY evaluacion_id ASC;
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

            cursor.execute("""
                SELECT *
                FROM evaluaciones
                WHERE evaluacion_id = %s;
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
        Devuelve las evaluaciones activas asignadas al docente
        que tengan preguntas activas pendientes de responder.
        """
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT e.*
                FROM evaluaciones e
                INNER JOIN carga_docente cd
                    ON cd.carga_id = e.carga_id
                WHERE cd.user_id = %s
                  AND e.estado = TRUE
                  AND EXISTS (
                      SELECT 1
                      FROM preguntas_evaluacion pe
                      WHERE pe.evaluacion_id = e.evaluacion_id
                        AND pe.estado = TRUE
                  )
                  AND EXISTS (
                      SELECT 1
                      FROM preguntas_evaluacion pe
                      WHERE pe.evaluacion_id = e.evaluacion_id
                        AND pe.estado = TRUE
                        AND NOT EXISTS (
                            SELECT 1
                            FROM respuestas r
                            WHERE r.pregunta_evaluacion_id =
                                  pe.pregunta_evaluacion_id
                              AND r.usuario_id = %s
                              AND r.estado = TRUE
                        )
                  )
                ORDER BY e.evaluacion_id ASC;
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
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING evaluacion_id;
            """, (
                evaluacion.carga_id,
                evaluacion.periodo_id,
                evaluacion.tipo_evaluacion,
                evaluacion.titulo,
                evaluacion.fecha_envio,
                evaluacion.estado
            ))

            fila = cursor.fetchone()
            conn.commit()

            return fila["evaluacion_id"] if fila else None

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error al crear evaluación: {e}")
            return None

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
                SELECT carga_id
                FROM carga_docente
                WHERE carga_id = %s;
            """, (carga_id,))

            if not cursor.fetchone():
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

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error al asignar evaluación: {e}")
            raise

        finally:
            if conn:
                conn.close()

    def asignar_autoevaluacion_a_todos(
        self,
        plantilla_evaluacion_id: int
    ):
        """
        Asigna una autoevaluación a cada docente activo del periodo
        de la plantilla, sin crear tablas nuevas.

        Copia las preguntas activas de la plantilla y evita duplicar
        una autoevaluación activa para el mismo docente y periodo.
        """
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # 1. Obtener la evaluación que servirá como plantilla.
            cursor.execute("""
                SELECT
                    evaluacion_id,
                    periodo_id,
                    tipo_evaluacion,
                    fecha_envio
                FROM evaluaciones
                WHERE evaluacion_id = %s
                  AND estado = TRUE;
            """, (plantilla_evaluacion_id,))

            plantilla = cursor.fetchone()

            if not plantilla:
                raise ValueError(
                    "No existe una evaluación activa para utilizar "
                    "como plantilla."
                )

            if plantilla["tipo_evaluacion"] != "AUTOEVALUACION":
                raise ValueError(
                    "La plantilla debe ser de tipo AUTOEVALUACION."
                )

            periodo_id = plantilla["periodo_id"]
            fecha_envio = plantilla["fecha_envio"]

            # 2. Comprobar que la plantilla tenga preguntas activas.
            cursor.execute("""
                SELECT pregunta_id
                FROM preguntas_evaluacion
                WHERE evaluacion_id = %s
                  AND estado = TRUE
                ORDER BY pregunta_evaluacion_id ASC;
            """, (plantilla_evaluacion_id,))

            preguntas = cursor.fetchall()

            if not preguntas:
                raise ValueError(
                    "La evaluación plantilla no tiene preguntas activas."
                )

            # 3. Obtener una sola carga por docente para el periodo.
            # DISTINCT ON evita contar varias veces al docente.
            cursor.execute("""
                SELECT DISTINCT ON (cd.user_id)
                    cd.user_id,
                    cd.carga_id
                FROM carga_docente cd
                INNER JOIN usuarios u
                    ON u.usuario_id = cd.user_id
                WHERE cd.periodo_id = %s
                  AND u.estado = TRUE
                ORDER BY cd.user_id, cd.carga_id;
            """, (periodo_id,))

            docentes = cursor.fetchall()

            creadas = 0
            omitidas = 0

            for docente in docentes:
                usuario_id = docente["user_id"]
                carga_id = docente["carga_id"]

                # 4. Si ya tiene una autoevaluación activa para este
                # periodo, no crear otra.
                cursor.execute("""
                    SELECT 1
                    FROM evaluaciones e
                    INNER JOIN carga_docente cd
                        ON cd.carga_id = e.carga_id
                    WHERE cd.user_id = %s
                      AND e.periodo_id = %s
                      AND e.tipo_evaluacion = 'AUTOEVALUACION'
                      AND e.estado = TRUE
                    LIMIT 1;
                """, (usuario_id, periodo_id))

                if cursor.fetchone():
                    omitidas += 1
                    continue

                # 5. Crear una evaluación individual para el docente.
                cursor.execute("""
                    INSERT INTO evaluaciones (
                        carga_id,
                        periodo_id,
                        tipo_evaluacion,
                        titulo,
                        fecha_envio,
                        estado
                    )
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                    RETURNING evaluacion_id;
                """, (
                    carga_id,
                    periodo_id,
                    "AUTOEVALUACION",
                    "Autoevaluación",
                    fecha_envio
                ))

                nueva = cursor.fetchone()
                nuevo_id = nueva["evaluacion_id"]

                # 6. Copiar las preguntas activas de la plantilla.
                cursor.execute("""
                    INSERT INTO preguntas_evaluacion (
                        evaluacion_id,
                        pregunta_id,
                        estado
                    )
                    SELECT
                        %s,
                        pregunta_id,
                        TRUE
                    FROM preguntas_evaluacion
                    WHERE evaluacion_id = %s
                      AND estado = TRUE;
                """, (nuevo_id, plantilla_evaluacion_id))

                creadas += 1

            conn.commit()

            return {
                "mensaje": "Asignación masiva finalizada.",
                "periodo_id": periodo_id,
                "evaluaciones_creadas": creadas,
                "docentes_omitidos_por_ya_tener_autoevaluacion": omitidas
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
                WHERE evaluacion_id = %s
                RETURNING evaluacion_id;
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
                SET carga_id = %s,
                    periodo_id = %s,
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
