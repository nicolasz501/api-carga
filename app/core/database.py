
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


class Database:

    def __init__(self):
        self.host = os.getenv("DB_HOST")
        self.database = os.getenv("DB_NAME")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.port = os.getenv("DB_PORT", "5432")

    def get_connection(self):

        try:
            if not all([
                self.host,
                self.database,
                self.user,
                self.password
            ]):
                raise ValueError(
                    "Faltan variables de conexión en el archivo .env"
                )

            conexion = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port,
                sslmode="require",
                cursor_factory=RealDictCursor,
                connect_timeout=10
            )

            return conexion

        except Exception as e:
            print(f"Error de conexión a la BD: {e}")
            return None
