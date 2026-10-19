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
        Devuelve únicamente las autoevaluaciones activas asignadas al
        docente, con preguntas activas pendientes por responder.

        Las evaluaciones cuyo título comienza con [PLANTILLA]
        nunca se muestran como asignaciones a los docentes.
        """
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT e.*
                FROM evaluaciones e
                INNER JOIN carga_docente cd
                    ON cd.carga_id = e.carga_id
                WHERE cd.user_id = %s
                  AND e.estado = TRUE
                  AND UPPER(e.tipo_evaluacion) = 'AUTOEVALUACION'

                  -- Excluir modelos que no son asignaciones.
                  AND COALESCE(e.titulo, '') NOT ILIKE '[PLANTILLA]%%'

                  -- Debe quedar al menos una pregunta activa sin responder.
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
                    ON cd.carga_id = e.carga_id
                WHERE e.evaluacion_id = %s
                  AND cd.user_id = %s
                LIMIT 1;
            """, (evaluacion_id, usuario_id))

            return cursor.fetchone() is not None

        except Exception as e:
            print(f"Error al verificar pertenencia de evaluación: {e}")
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
                        (SELECT periodo_id FROM carga_docente
                         WHERE carga_id = %s)
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
                evaluacion.estado
            ))

            fila = cursor.fetchone()
            conn.commit()

            return fila["evaluacion_id"] if fila else None

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
        Crea una sola autoevaluación por docente activo (con carga
        activa) para el periodo de la plantilla, reutilizando las
        tablas existentes.

        Excluye la plantilla al comprobar asignaciones existentes,
        copia sus preguntas y evita duplicar autoevaluaciones activas.
        Un lock por periodo evita ejecuciones concurrentes duplicadas.
        """
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # 1. Consultar la plantilla.
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

            periodo_id = plantilla["periodo_id"]
            fecha_envio = plantilla["fecha_envio"]
            titulo_plantilla = plantilla["titulo"] or "Autoevaluación"

            # 1.1 Serializar ejecuciones por periodo (el lock se libera
            #     solo al terminar la transacción).
            cursor.execute(
                "SELECT pg_advisory_xact_lock(1001, %s);", (periodo_id,)
            )

            # 2. Obtener las preguntas activas de la plantilla.
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

            # 3. Obtener una sola carga por docente activo.
            # Se prefiere la carga del periodo de la plantilla; si el
            # docente no tiene una en ese periodo, se usa su carga activa
            # más reciente, para no dejar docentes sin evaluación.
            cursor.execute("""
                SELECT DISTINCT ON (cd.user_id)
                    cd.user_id,
                    cd.carga_id
                FROM carga_docente cd
                INNER JOIN usuarios u
                    ON u.usuario_id = cd.user_id
                WHERE u.estado = TRUE
                  AND cd.estado = TRUE
                ORDER BY cd.user_id,
                         (cd.periodo_id = %s) DESC,
                         cd.periodo_id DESC,
                         cd.carga_id ASC;
            """, (periodo_id,))

            docentes = cursor.fetchall()

            creadas = 0
            omitidas = 0

            for docente in docentes:
                usuario_id = docente["user_id"]
                carga_id = docente["carga_id"]

                # 4. No contar la propia plantilla como asignación.
                cursor.execute("""
                    SELECT 1
                    FROM evaluaciones e
                    INNER JOIN carga_docente cd
                        ON cd.carga_id = e.carga_id
                    WHERE cd.user_id = %s
                      AND COALESCE(e.periodo_id, cd.periodo_id) = %s
                      AND e.tipo_evaluacion = 'AUTOEVALUACION'
                      AND e.estado = TRUE
                      AND e.evaluacion_id <> %s
                      AND COALESCE(e.titulo, '') NOT ILIKE '[PLANTILLA]%%'
                    LIMIT 1;
                """, (
                    usuario_id,
                    periodo_id,
                    plantilla_evaluacion_id
                ))

                if cursor.fetchone():
                    omitidas += 1
                    continue

                # 5. Crear la evaluación individual del docente.
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
                    "Autoevaluación individual",
                    fecha_envio
                ))

                nueva = cursor.fetchone()
                nuevo_id = nueva["evaluacion_id"]

                # 6. Copiar las preguntas activas.
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
                    ORDER BY pregunta_evaluacion_id ASC;
                """, (nuevo_id, plantilla_evaluacion_id))

                creadas += 1

            # 7. Marcar la plantilla para que no se muestre al docente.
            if not str(titulo_plantilla).upper().startswith("[PLANTILLA]"):
                titulo_nuevo = f"[PLANTILLA] {titulo_plantilla}"

                cursor.execute("""
                    UPDATE evaluaciones
                    SET titulo = %s
                    WHERE evaluacion_id = %s;
                """, (titulo_nuevo, plantilla_evaluacion_id))

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

            print(
                f"Error en asignación masiva de autoevaluaciones: {e}"
            )
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