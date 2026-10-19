
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

        finally:
            if conn:
                conn.close()

    def obtener_para_docente(self, usuario_id: int):
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM evaluaciones
                WHERE usuario_id = %s
                  AND estado = TRUE
                ORDER BY evaluacion_id ASC;
            """, (usuario_id,))

            return cursor.fetchall()

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

            resultado = cursor.fetchone()
            conn.commit()

            return resultado[0] if resultado else None

        except Exception:
            if conn:
                conn.rollback()
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
                UPDATE evaluaciones
                SET carga_id = %s
                WHERE evaluacion_id = %s
                RETURNING evaluacion_id;
            """, (carga_id, evaluacion_id))

            resultado = cursor.fetchone()
            conn.commit()

            return resultado is not None

        except Exception:
            if conn:
                conn.rollback()
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

            resultado = cursor.fetchone()
            conn.commit()

            return resultado is not None

        except Exception:
            if conn:
                conn.rollback()
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

            resultado = cursor.fetchone()
            conn.commit()

            return resultado is not None

        except Exception:
            if conn:
                conn.rollback()
            raise

        finally:
            if conn:
                conn.close()
