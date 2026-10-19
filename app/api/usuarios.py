import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.models.Usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/usuarios",
    tags=["Gestión de Usuarios"]
)

repo = UsuarioRepository()


# ======================================================================
# Autenticación por token (JWT HS256, sin dependencias nuevas).
# Configura la variable de entorno SECRET_KEY en Render. Si no existe,
# se usa una clave temporal: los tokens dejan de valer al reiniciar.
# ======================================================================
_SECRET = os.getenv("SECRET_KEY")
if not _SECRET:
    logger.warning(
        "SECRET_KEY no está definida; se usa una clave temporal. "
        "Configúrala en las variables de entorno de Render."
    )
    _SECRET = secrets.token_hex(32)

_DURACION_TOKEN = 8 * 60 * 60  # 8 horas

_bearer = HTTPBearer(auto_error=False)


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


def _b64_decode(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _firmar(mensaje: str) -> str:
    return _b64(
        hmac.new(_SECRET.encode(), mensaje.encode(), hashlib.sha256).digest()
    )


def crear_token(usuario_id: int, rol: str) -> str:
    cabecera = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    carga = _b64(json.dumps({
        "sub": str(usuario_id),
        "rol": rol,
        "exp": int(time.time()) + _DURACION_TOKEN
    }).encode())
    return f"{cabecera}.{carga}.{_firmar(f'{cabecera}.{carga}')}"


def verificar_token(token: str):
    try:
        cabecera, carga, firma = token.split(".")
        if not hmac.compare_digest(firma, _firmar(f"{cabecera}.{carga}")):
            return None
        datos = json.loads(_b64_decode(carga))
        if datos["exp"] < time.time():
            return None
        return datos
    except Exception:
        return None


class UsuarioActual(BaseModel):
    usuario_id: int
    rol: str


def get_usuario_actual(
    credenciales: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UsuarioActual:
    if credenciales is None:
        raise HTTPException(status_code=401, detail="No autenticado.")

    datos = verificar_token(credenciales.credentials)
    if not datos:
        raise HTTPException(
            status_code=401,
            detail="Sesión inválida o expirada. Inicia sesión nuevamente."
        )

    return UsuarioActual(
        usuario_id=int(datos["sub"]),
        rol=datos.get("rol") or ""
    )


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", str(texto or ""))
        if unicodedata.category(c) != "Mn"
    )
    return sin_tildes.replace("_", " ").strip().lower()


def es_administrador(rol: str) -> bool:
    """Jefe de departamento o dirección académica (igual que el frontend)."""
    r = _normalizar(rol)
    return "jefe de departamento" in r or "direccion academica" in r


def requiere_jefe(
    usuario: UsuarioActual = Depends(get_usuario_actual),
) -> UsuarioActual:
    if not es_administrador(usuario.rol):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    return usuario


# ======================================================================
# Modelos
# ======================================================================
class LoginRequest(BaseModel):
    correo: str
    password: str


class UsuarioUpdate(BaseModel):
    primer_nombre: str
    segundo_nombre: str | None = None
    primer_apellido: str
    segundo_apellido: str | None = None

    correo: str
    codigo_personal: str | None = None
    titulo_academico: str | None = None

    estado: bool

    rol_id: int
    numero_documento: str

    # Opcional al actualizar.
    # Si no se envía, se conserva la contraseña actual.
    contraseña: str | None = None


# ======================================================================
# Rutas
# ======================================================================
@router.get("/")
def listar_usuarios():

    return repo.obtener_todos()


@router.post("/login")
def login(datos: LoginRequest):

    resultado = repo.login(
        datos.correo,
        datos.password
    )

    if not resultado:

        raise HTTPException(
            status_code=401,
            detail="Correo o contraseña incorrectos"
        )

    # Token firmado con el id y el rol del usuario.
    resultado["token"] = crear_token(
        resultado["usuario"]["usuario_id"],
        resultado["rol"]["nombre"] or ""
    )

    return resultado


@router.get("/{usuario_id}")
def obtener_usuario(usuario_id: int):

    usuario = repo.obtener_por_id(usuario_id)

    if not usuario:

        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )

    return usuario


@router.post("/")
def crear_usuario(usuario: Usuario):
    try:
        nuevo_id = repo.crear(usuario)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not nuevo_id:
        raise HTTPException(status_code=500, detail="No se pudo crear el usuario")

    return {"mensaje": "Usuario registrado exitosamente", "id": nuevo_id}


@router.delete("/{usuario_id}")
def eliminar_usuario(usuario_id: int):
    try:
        exito = repo.eliminar(usuario_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not exito:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {"mensaje": "Usuario eliminado correctamente"}


@router.put("/{usuario_id}")
def actualizar_usuario(usuario_id: int, usuario: UsuarioUpdate):
    try:
        exito = repo.actualizar(usuario_id, usuario)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not exito:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o no se pudo actualizar")

    return {"mensaje": "Usuario actualizado correctamente"}