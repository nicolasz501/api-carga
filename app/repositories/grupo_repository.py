
from app.core.database import Database
from app.models.Grupo import Grupo


class GrupoRepository:

    def __init__(self):
        self.db = Database()

    @staticmethod
    def obtener_id(fila):
        if fila is None:
            return None
        if isinstance(fila, dict):
            return fila.get("grupos_id")
        return fila[0]

    def obtener_todos(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    grupos_id,
                    asignaturas_id,
                    nombre_grupos,
                    capacidad,
                    estado,
                    created_at,
                    updated_at
                FROM grupos
                ORDER BY grupos_id ASC;
            """)

            return cursor.fetchall()

        except Exception as e:
            print(f"Error al obtener grupos: {e}")
            raise

        finally:
            if conn:
                conn.close()

    def obtener_por_id(self, grupos_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    grupos_id,
                    asignaturas_id,
                    nombre_grupos,
                    capacidad,
                    estado,
                    created_at,
                    updated_at
                FROM grupos
                WHERE grupos_id = %s;
            """, (grupos_id,))

            return cursor.fetchone()

        except Exception as e:
            print(f"Error al obtener grupo: {e}")
            raise

        finally:
            if conn:
                conn.close()

    def crear(self, grupo: Grupo):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO grupos (
                    asignaturas_id,
                    nombre_grupos,
                    capacidad,
                    estado
                )
                VALUES (%s, %s, %s, %s)
                RETURNING grupos_id;
            """, (
                grupo.asignaturas_id,
                grupo.nombre_grupos.strip(),
                grupo.capacidad,
                grupo.estado
            ))

            nuevo_id = self.obtener_id(cursor.fetchone())

            if nuevo_id is None:
                raise RuntimeError(
                    "No se obtuvo el identificador del grupo creado."
                )

            conn.commit()
            return nuevo_id

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error al crear grupo: {e}")
            raise

        finally:
            if conn:
                conn.close()

    def actualizar(self, grupos_id: int, grupo: Grupo):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE grupos
                SET asignaturas_id = %s,
                    nombre_grupos = %s,
                    capacidad = %s,
                    estado = %s,
                    updated_at = NOW()
                WHERE grupos_id = %s
                RETURNING grupos_id;
            """, (
                grupo.asignaturas_id,
                grupo.nombre_grupos.strip(),
                grupo.capacidad,
                grupo.estado,
                grupos_id
            ))

            fila = cursor.fetchone()

            if fila is None:
                conn.rollback()
                return False

            conn.commit()
            return True

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error al actualizar grupo: {e}")
            raise

        finally:
            if conn:
                conn.close()

    def eliminar(self, grupos_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM grupos
                WHERE grupos_id = %s
                RETURNING grupos_id;
            """, (grupos_id,))

            fila = cursor.fetchone()

            if fila is None:
                conn.rollback()
                return False

            conn.commit()
            return True

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error al eliminar grupo: {e}")
            raise

        finally:
            if conn:
                conn.close()
