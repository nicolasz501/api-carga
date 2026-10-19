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
            return []
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
            return None
        finally:
            if conn:
                conn.close()

    
def obtener_para_docente(self, usuario_id: int):
    """
    Devuelve las evaluaciones activas asignadas al docente,
    siempre que tengan preguntas activas y aún no hayan sido
    respondidas completamente por ese docente.
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

              -- La evaluación debe tener preguntas activas.
              AND EXISTS (
                  SELECT 1
                  FROM preguntas_evaluacion pe
                  WHERE pe.evaluacion_id = e.evaluacion_id
                    AND pe.estado = TRUE
              )

              -- Mostrar la evaluación si existe al menos
              -- una pregunta activa que aún no ha respondido.
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
        print(f"Error al consultar evaluaciones del docente: {e}")
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