from app.core.database import Database
from app.models.Usuario import Usuario


class UsuarioRepository:

    def __init__(self):
        self.db = Database()

    # =========================================================
    # OBTENER TODOS
    # =========================================================

    def obtener_todos(self):
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM usuarios
                ORDER BY usuario_id ASC;
            """)

            usuarios = cursor.fetchall()

            cursor.close()
            conn.close()

            return usuarios

        except Exception as e:
            print(f"Error al obtener usuarios: {e}")
            return []

    # =========================================================
    # OBTENER POR ID
    # =========================================================

    def obtener_por_id(self, usuario_id: int):
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM usuarios
                WHERE usuario_id = %s;
            """, (usuario_id,))

            usuario = cursor.fetchone()

            cursor.close()
            conn.close()

            return usuario

        except Exception as e:
            print(f"Error al obtener usuario: {e}")
            return None

    # =========================================================
    # CREAR
    # =========================================================

    def crear(self, usuario: Usuario):
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO usuarios
                (
                    facultades_id,
                    rol_id,
                    primer_nombre,
                    segundo_nombre,
                    primer_apellido,
                    segundo_apellido,
                    correo,
                    contraseña,
                    numero_documento,
                    codigo_personal,
                    titulo_academico,
                    estado
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                RETURNING usuario_id;
            """, (
                usuario.facultades_id,
                usuario.rol_id,
                usuario.primer_nombre,
                usuario.segundo_nombre,
                usuario.primer_apellido,
                usuario.segundo_apellido,
                usuario.correo,
                usuario.contraseña,
                usuario.numero_documento,
                usuario.codigo_personal,
                usuario.titulo_academico,
                usuario.estado
            ))

            resultado = cursor.fetchone()
            nuevo_id = resultado["usuario_id"]

            conn.commit()

            cursor.close()
            conn.close()

            return nuevo_id

        except Exception as e:
            print(f"Error al crear usuario: {e}")

            if conn:
                conn.rollback()
                conn.close()

            return None

    # =========================================================
    # LOGIN
    # =========================================================

    def login(self, correo: str, password: str):

        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # -------------------------------------------------
            # 1. BUSCAR USUARIO + ROL
            # -------------------------------------------------

            cursor.execute("""
                SELECT
                    u.usuario_id,
                    u.facultades_id,
                    u.rol_id,
                    u.primer_nombre,
                    u.segundo_nombre,
                    u.primer_apellido,
                    u.segundo_apellido,
                    u.correo,
                    u.codigo_personal,
                    u.titulo_academico,
                    u.estado,

                    r.role_id,
                    r.nombre AS rol_nombre

                FROM usuarios u

                LEFT JOIN roles r
                    ON r.role_id = u.rol_id

                WHERE LOWER(u.correo) = LOWER(%s)
                  AND u.contraseña = %s
                  AND u.estado = TRUE;
            """, (correo, password))

            usuario = cursor.fetchone()

            # Usuario no encontrado
            if not usuario:
                cursor.close()
                conn.close()
                return None

            # -------------------------------------------------
            # 2. OBTENER MÓDULOS DEL ROL
            # -------------------------------------------------

            cursor.execute("""
                SELECT
                    m.module_id,
                    m.nombre

                FROM modulos_rol mr

                INNER JOIN modulos m
                    ON m.module_id = mr.module_id

                WHERE mr.role_id = %s

                ORDER BY m.module_id ASC;
            """, (usuario["rol_id"],))

            modulos = cursor.fetchall()

            # -------------------------------------------------
            # 3. CONVERTIR MÓDULOS
            # -------------------------------------------------

            lista_modulos = [
                modulo["nombre"]
                for modulo in modulos
            ]

            # -------------------------------------------------
            # 4. ARMAR USUARIO
            # -------------------------------------------------

            usuario_data = {
                "usuario_id": usuario["usuario_id"],
                "facultades_id": usuario["facultades_id"],
                "rol_id": usuario["rol_id"],
                "primer_nombre": usuario["primer_nombre"],
                "segundo_nombre": usuario["segundo_nombre"],
                "primer_apellido": usuario["primer_apellido"],
                "segundo_apellido": usuario["segundo_apellido"],
                "correo": usuario["correo"],
                "codigo_personal": usuario["codigo_personal"],
                "titulo_academico": usuario["titulo_academico"],
                "estado": usuario["estado"]
            }

            # -------------------------------------------------
            # 5. ARMAR ROL
            # -------------------------------------------------

            rol_data = {
                "role_id": usuario["role_id"],
                "nombre": usuario["rol_nombre"]
            }

            # -------------------------------------------------
            # 6. RESPUESTA FINAL
            # -------------------------------------------------

            resultado = {
                "usuario": usuario_data,
                "rol": rol_data,
                "modulos": lista_modulos
            }

            cursor.close()
            conn.close()

            return resultado

        except Exception as e:

            print(f"Error en login: {e}")

            if conn:
                conn.rollback()
                conn.close()

            return None

    # =========================================================
    # ELIMINAR
    # =========================================================

    def eliminar(self, usuario_id: int):
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM usuarios
                WHERE usuario_id = %s
                RETURNING usuario_id;
            """, (usuario_id,))

            eliminado = cursor.fetchone()

            conn.commit()

            cursor.close()
            conn.close()

            return eliminado is not None

        except Exception as e:
            print(f"Error al eliminar usuario: {e}")

            if conn:
                conn.rollback()
                conn.close()

            return False

    # =========================================================
    # ACTUALIZAR
    # =========================================================

    def actualizar(self, usuario_id: int, usuario: Usuario):
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE usuarios
                SET facultades_id = %s,
                    rol_id = %s,
                    primer_nombre = %s,
                    segundo_nombre = %s,
                    primer_apellido = %s,
                    segundo_apellido = %s,
                    correo = %s,
                    contraseña = %s,
                    numero_documento = %s,
                    codigo_personal = %s,
                    titulo_academico = %s,
                    estado = %s
                WHERE usuario_id = %s
                RETURNING usuario_id;
            """, (
                usuario.facultades_id,
                usuario.rol_id,
                usuario.primer_nombre,
                usuario.segundo_nombre,
                usuario.primer_apellido,
                usuario.segundo_apellido,
                usuario.correo,
                usuario.contraseña,
                usuario.numero_documento,
                usuario.codigo_personal,
                usuario.titulo_academico,
                usuario.estado,
                usuario_id
            ))

            actualizado = cursor.fetchone()

            conn.commit()

            cursor.close()
            conn.close()

            return actualizado is not None

        except Exception as e:
            print(f"Error al actualizar usuario: {e}")

            if conn:
                conn.rollback()
                conn.close()

            return False