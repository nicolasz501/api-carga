from app.core.database import Database
from app.models.PreguntaEvaluacion import PreguntaEvaluacion
import psycopg2.errors


class PreguntaEvaluacionRepository:

    def __init__(self):
        self.db = Database()

    SELECT_BASE = """
        SELECT pe.pregunta_evaluacion_id, pe.pregunta_id, pe.evaluacion_id,
               pe.numero_orden, pe.estado, pe.created_at, pe.updated_at,
               p.texto_pregunta
        FROM preguntas_evaluacion pe
        JOIN preguntas p ON p.pregunta_id = pe.pregunta_id
    """

    def _consultar(self, sql, params=(), uno=False):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params)
            datos = cursor.fetchone() if uno else cursor.fetchall()
            cursor.close()
            conn.close()
            return datos
        except Exception as e:
            print(f"Error en preguntas_evaluacion: {e}")
            if conn:
                conn.close()
            return None if uno else []

    def obtener_todos(self):
        return self._consultar(
            self.SELECT_BASE + " ORDER BY pe.evaluacion_id, pe.numero_orden;"
        )

    def obtener_por_id(self, pregunta_evaluacion_id: int):
        return self._consultar(
            self.SELECT_BASE + " WHERE pe.pregunta_evaluacion_id = %s;",
            (pregunta_evaluacion_id,), uno=True
        )

    def obtener_por_evaluacion(self, evaluacion_id: int):
        return self._consultar(
            self.SELECT_BASE +
            " WHERE pe.evaluacion_id = %s AND pe.estado = TRUE ORDER BY pe.numero_orden;",
            (evaluacion_id,)
        )

    def crear(self, d: PreguntaEvaluacion):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO preguntas_evaluacion
                    (pregunta_id, evaluacion_id, numero_orden, estado)
                VALUES (%s, %s, %s, %s)
                RETURNING pregunta_evaluacion_id;
            """, (d.pregunta_id, d.evaluacion_id, d.numero_orden, d.estado))
            nuevo_id = cursor.fetchone()["pregunta_evaluacion_id"]
            conn.commit()
            cursor.close()
            conn.close()
            return nuevo_id

        except psycopg2.errors.UniqueViolation:
            if conn:
                conn.rollback()
                conn.close()
            raise ValueError("Esa pregunta ya está asignada a la evaluación")

        except psycopg2.errors.ForeignKeyViolation:
            if conn:
                conn.rollback()
                conn.close()
            raise ValueError("La pregunta o la evaluación no existe")

        except Exception as e:
            print(f"Error al crear pregunta_evaluacion: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return None

    def actualizar(self, pregunta_evaluacion_id: int, d: PreguntaEvaluacion):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE preguntas_evaluacion
                SET pregunta_id = %s, evaluacion_id = %s,
                    numero_orden = %s, estado = %s, updated_at = NOW()
                WHERE pregunta_evaluacion_id = %s
                RETURNING pregunta_evaluacion_id;
            """, (d.pregunta_id, d.evaluacion_id, d.numero_orden,
                  d.estado, pregunta_evaluacion_id))
            actualizado = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()
            return actualizado is not None

        except psycopg2.errors.UniqueViolation:
            if conn:
                conn.rollback()
                conn.close()
            raise ValueError("Esa pregunta ya está asignada a la evaluación")

        except psycopg2.errors.ForeignKeyViolation:
            if conn:
                conn.rollback()
                conn.close()
            raise ValueError("La pregunta o la evaluación no existe")

        except Exception as e:
            print(f"Error al actualizar pregunta_evaluacion: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return False

    def eliminar(self, pregunta_evaluacion_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM preguntas_evaluacion
                WHERE pregunta_evaluacion_id = %s
                RETURNING pregunta_evaluacion_id;
            """, (pregunta_evaluacion_id,))
            eliminado = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()
            return eliminado is not None

        except psycopg2.errors.ForeignKeyViolation:
            if conn:
                conn.rollback()
                conn.close()
            raise ValueError("No se puede eliminar: tiene respuestas asociadas")

        except Exception as e:
            print(f"Error al eliminar pregunta_evaluacion: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return False