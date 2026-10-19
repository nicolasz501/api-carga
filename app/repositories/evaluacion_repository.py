
from app.core.database import Database
from app.models.Evaluacion import Evaluacion


class EvaluacionRepository:

    def __init__(self):
        self.db = Database()

    @staticmethod
    def _valor(fila, columna):
        if fila is None:
            return None

        if isinstance(fila, dict):
            return fila.get(columna)

        return fila[0]

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
                SELECT e.*
                FROM evaluaciones e
                INNER JOIN carga_docente cd
                    ON cd.carga_id = e.carga_id
                WHERE cd.user_id = %s
                  AND cd.estado = TRUE
                  AND e.estado = TRUE
                ORDER BY e.evaluacion_id ASC;
            """, (usuario_id,))

            return cursor.fetchall()

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
                  AND e.estado = TRUE
                LIMIT 1;
            """, (evaluacion_id, usuario_id))

            return cursor.fetchone() is not None

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
            nuevo_id = self._valor(fila, "evaluacion_id")

            conn.commit()
            return nuevo_id

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
            raise

        finally:
            if conn:
                conn.close()
