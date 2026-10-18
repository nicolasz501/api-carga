from app.core.database import Database
from app.models.Usuario import Usuario
import psycopg2.errors
import bcrypt


class UsuarioRepository:

    def __init__(self):
        self.db = Database()

    def obtener_todos(self):
        conn = None

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

            if conn:
                conn.close()

            return []

    def obtener_por_id(self, usuario_id: int):
        conn = None

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

            if conn:
                conn.close()

            return None

    def crear(self, usuario: Usuario):
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            contraseña_hash = bcrypt.hashpw(
                usuario.contraseña.encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8")

            cursor.execute("""
                INSERT INTO usuarios
                (
                    rol_id, primer_nombre, segundo_nombre,
                    primer_apellido, segundo_apellido, correo, contraseña,
                    numero_documento, codigo_personal, titulo_academico, estado
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING usuario_id;
            """, (
                usuario.rol_id,
                usuario.primer_nombre,
                usuario.segundo_nombre,
                usuario.primer_apellido,
                usuario.segundo_apellido,
                usuario.correo,
                contraseña_hash,
                usuario.numero_documento,
                usuario.codigo_personal,
                usuario.titulo_academico,
                usuario.estado
            ))

            nuevo_id = cursor.fetchone()["usuario_id"]
            conn.commit()

            cursor.close()
            conn.close()

            return nuevo_id

        except psycopg2.errors.UniqueViolation:
            if conn:
                conn.rollback()
                conn.close()
            raise ValueError("Ya existe un usuario con ese correo, documento o código personal")

        except Exception as e:
            print(f"Error al crear usuario: {e}")

            if conn:
                conn.rollback()
                conn.close()

            return None

    def login(self, correo: str, password: str):

        conn = None

        try:

            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    u.usuario_id,
                    u.rol_id,
                    u.primer_nombre,
                    u.segundo_nombre,
                    u.primer_apellido,
                    u.segundo_apellido,
                    u.correo,
                    u.contraseña,
                    u.codigo_personal,
                    u.titulo_academico,
                    u.estado,

                    r.rol_id AS rol_id_real,
                    r.nombre_rol

                FROM usuarios u

                LEFT JOIN roles r
                    ON r.rol_id = u.rol_id

                WHERE LOWER(u.correo) = LOWER(%s)
                AND u.estado = TRUE;
            """, (correo,))

            usuario = cursor.fetchone()

            # Usuario no encontrado
            if not usuario:

                cursor.close()
                conn.close()

                return None

            contraseña_guardada = usuario["contraseña"]

            contraseña_valida = False

            try:

                contraseña_valida = bcrypt.checkpw(
                    password.encode("utf-8"),
                    contraseña_guardada.encode("utf-8")
                )

            except Exception:

                # Compatibilidad temporal con contraseñas
                # almacenadas como texto plano
                contraseña_valida = (
                    contraseña_guardada == password
                )

            if not contraseña_valida:

                cursor.close()
                conn.close()

                return None

            cursor.execute("""
                SELECT
                    m.modulos_id,
                    m.nombre_modulo,

                    mr.puede_ver,
                    mr.puede_crear,
                    mr.puede_editar,
                    mr.puede_eliminar

                FROM modulos_rol mr

                INNER JOIN modulos m
                    ON m.modulos_id = mr.module_id

                WHERE mr.role_id = %s
                AND mr.estado = TRUE
                AND m.estado = TRUE

                ORDER BY m.modulos_id ASC;
            """, (usuario["rol_id"],))

            modulos = cursor.fetchall()

            lista_modulos = []

            for modulo in modulos:

                lista_modulos.append({
                    "id": modulo["modulos_id"],
                    "nombre": modulo["nombre_modulo"],
                    "puede_ver": modulo["puede_ver"],
                    "puede_crear": modulo["puede_crear"],
                    "puede_editar": modulo["puede_editar"],
                    "puede_eliminar": modulo["puede_eliminar"]
                })

            usuario_data = {

                "usuario_id": usuario["usuario_id"],
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

            rol_data = {

                "rol_id": usuario["rol_id_real"],
                "nombre": usuario["nombre_rol"]
            }

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

    def actualizar(self, usuario_id: int, usuario):
        conn = None

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # Solo se encripta si llegó una contraseña nueva
            contraseña_hash = None
            if usuario.contraseña and usuario.contraseña.strip():
                contraseña_hash = bcrypt.hashpw(
                    usuario.contraseña.strip().encode("utf-8"),
                    bcrypt.gensalt()
                ).decode("utf-8")

            cursor.execute("""
                UPDATE usuarios
                SET
                    rol_id = %s,
                    primer_nombre = %s,
                    segundo_nombre = %s,
                    primer_apellido = %s,
                    segundo_apellido = %s,
                    correo = %s,
                    contraseña = COALESCE(%s, contraseña),
                    numero_documento = %s,
                    codigo_personal = %s,
                    titulo_academico = %s,
                    estado = %s,
                    updated_at = NOW()
                WHERE usuario_id = %s
                RETURNING usuario_id;
            """, (
                usuario.rol_id,
                usuario.primer_nombre,
                usuario.segundo_nombre,
                usuario.primer_apellido,
                usuario.segundo_apellido,
                usuario.correo,
                contraseña_hash,
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

        except psycopg2.errors.UniqueViolation:
            if conn:
                conn.rollback()
                conn.close()
            raise ValueError("Ya existe un usuario con ese correo, documento o código personal")

        except Exception as e:
            print(f"Error al actualizar usuario: {e}")

            if conn:
                conn.rollback()
                conn.close()

            return False

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

        except psycopg2.errors.ForeignKeyViolation:
            if conn:
                conn.rollback()
                conn.close()
            raise ValueError("No se puede eliminar: el usuario tiene registros asociados (carga docente, etc.)")

        except Exception as e:
            print(f"Error al eliminar usuario: {e}")

            if conn:
                conn.rollback()
                conn.close()

            return False