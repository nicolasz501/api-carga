import psycopg2
from psycopg2.extras import RealDictCursor

from app.database import get_connection  # ajusta a tu conexión real
from app.models.PreguntaEvaluacion import PreguntaEvaluacion


class PreguntaEvaluacionRepository:

    def obtener_todos(self):
        with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT pe.pregunta_evaluacion_id, pe.pregunta_id, pe.evaluacion_id,
                       pe.numero_orden, pe.estado, pe.created_at, pe.updated_at,
                       p.texto_pregunta
                FROM public.preguntas_evaluacion pe
                JOIN public.preguntas p ON p.pregunta_id = pe.pregunta_id
                ORDER BY pe.evaluacion_id, pe.numero_orden
            """)
            return cur.fetchall()

    def obtener_por_id(self, pregunta_evaluacion_id: int):
        with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT pe.pregunta_evaluacion_id, pe.pregunta_id, pe.evaluacion_id,
                       pe.numero_orden, pe.estado, pe.created_at, pe.updated_at,
                       p.texto_pregunta
                FROM public.preguntas_evaluacion pe
                JOIN public.preguntas p ON p.pregunta_id = pe.pregunta_id
                WHERE pe.pregunta_evaluacion_id = %s
            """, (pregunta_evaluacion_id,))
            return cur.fetchone()

    def obtener_por_evaluacion(self, evaluacion_id: int):
        with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT pe.pregunta_evaluacion_id, pe.pregunta_id, pe.evaluacion_id,
                       pe.numero_orden, pe.estado, p.texto_pregunta
                FROM public.preguntas_evaluacion pe
                JOIN public.preguntas p ON p.pregunta_id = pe.pregunta_id
                WHERE pe.evaluacion_id = %s AND pe.estado = true
                ORDER BY pe.numero_orden
            """, (evaluacion_id,))
            return cur.fetchall()

    def crear(self, d: PreguntaEvaluacion):
        try:
            with get_connection() as conn, conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO public.preguntas_evaluacion
                        (pregunta_id, evaluacion_id, numero_orden, estado)
                    VALUES (%s, %s, %s, %s)
                    RETURNING pregunta_evaluacion_id
                """, (d.pregunta_id, d.evaluacion_id, d.numero_orden, d.estado))
                return cur.fetchone()[0]
        except psycopg2.errors.UniqueViolation:
            raise ValueError("Esa pregunta ya está asignada a la evaluación")
        except psycopg2.errors.ForeignKeyViolation:
            raise ValueError("La pregunta o la evaluación no existe")

    def actualizar(self, pregunta_evaluacion_id: int, d: PreguntaEvaluacion):
        try:
            with get_connection() as conn, conn.cursor() as cur:
                cur.execute("""
                    UPDATE public.preguntas_evaluacion
                    SET pregunta_id = %s, evaluacion_id = %s,
                        numero_orden = %s, estado = %s, updated_at = now()
                    WHERE pregunta_evaluacion_id = %s
                """, (d.pregunta_id, d.evaluacion_id, d.numero_orden,
                      d.estado, pregunta_evaluacion_id))
                return cur.rowcount > 0
        except psycopg2.errors.UniqueViolation:
            raise ValueError("Esa pregunta ya está asignada a la evaluación")
        except psycopg2.errors.ForeignKeyViolation:
            raise ValueError("La pregunta o la evaluación no existe")

    def eliminar(self, pregunta_evaluacion_id: int):
        try:
            with get_connection() as conn, conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM public.preguntas_evaluacion
                    WHERE pregunta_evaluacion_id = %s
                """, (pregunta_evaluacion_id,))
                return cur.rowcount > 0
        except psycopg2.errors.ForeignKeyViolation:
            raise ValueError("No se puede eliminar: tiene respuestas asociadas")