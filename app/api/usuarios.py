
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
    tags=["Gestión de Usuarios"],
)

repo = UsuarioRepository()

# Configurar SECRET_KEY como variable de entorno en Render.
_SECRET = os.getenv("SECRET_KEY")

if not _SECRET:
    logger.warning(
        "SECRET_KEY no está configurada. "
        "Configúrala en Render y vuelve a iniciar sesión."
    )
    _SECRET = secrets.token_hex(32)

_DURACION_TOKEN = 8 * 60 * 60

_bearer = HTTPBearer(auto_error=False)


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode("utf-8")


def _b64_decode(texto: str) -> bytes:
    return base64.urlsafe_b64decode(
        texto + "=" * (-len(texto) % 4)
    )


def _firmar(mensaje: str) -> str:
    return _b64(
        hmac.new(
            _SECRET.encode("utf-8"),
            mensaje.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    )


def crear_token(usuario_id: int, rol: str) -> str:
    cabecera = _b64(
        json.dumps(
            {"alg": "HS256", "typ": "JWT"},
            separators=(",", ":"),
        ).encode("utf-8")
    )

    carga = _b64(
        json.dumps(
            {
                "sub": str(usuario_id),
                "rol": rol,
                "exp": int(time.time()) + _DURACION_TOKEN,
            },
            separators=(",", ":"),
        ).encode("utf-8")
    )

    mensaje = f"{cabecera}.{carga}"
    return f"{mensaje}.{_firmar(mensaje)}"


def verificar_token(token: str):
    try:
        partes = token.split(".")
        if len(partes) != 3:
            return None

        cabecera, carga, firma = partes

        datos_cabecera = json.loads(_b64_decode(cabecera))

        if datos_cabecera.get("alg") != "HS256":
            return None

        firma_esperada = _firmar(f"{cabecera}.{carga}")

        if not hmac.compare_digest(firma, firma_esperada):
            return None

        datos = json.loads(_b64_decode(carga))

        if int(datos.get("exp", 0)) <= int(time.time()):
            return None

        usuario_id = int(datos["sub"])

        if usuario_id <= 0:
            return None

        return datos

    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None
    except Exception:
        logger.exception("Error inesperado al verificar token")
        return None


class UsuarioActual(BaseModel):
    usuario_id: int
    rol: str


def get_usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UsuarioActual:
    if credenciales is None:
        raise HTTPException(
            status_code=401,
            detail="Falta el token. Inicia sesión y autoriza la petición.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credenciales.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Tipo de autenticación inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    datos = verificar_token(credenciales.credentials)

    if not datos:
        raise HTTPException(
            status_code=401,
            detail="Sesión inválida o expirada. Inicia sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UsuarioActual(
        usuario_id=int(datos["sub"]),
        rol=str(datos.get("rol") or ""),
    )


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", str(texto or ""))
        if unicodedata.category(caracter) != "Mn"
    )

    return sin_tildes.replace("_", " ").strip().lower()


def es_administrador(rol: str) -> bool:
    rol_normalizado = _normalizar(rol)

    return (
        "jefe de departamento" in rol_normalizado
        or "direccion academica" in rol_normalizado
    )


def requiere_jefe(
    usuario: UsuarioActual = Depends(get_usuario_actual),
) -> UsuarioActual:
    if not es_administrador(usuario.rol):
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado.",
        )

    return usuario


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
    contraseña: str | None = None


@router.get("/")
def listar_usuarios():
    return repo.obtener_todos()


@router.post("/login")
def login(datos: LoginRequest):
    resultado = repo.login(datos.correo, datos.password)

    if not resultado:
        raise HTTPException(
            status_code=401,
            detail="Correo o contraseña incorrectos.",
        )

    usuario = resultado.get("usuario") or {}
    rol = resultado.get("rol") or {}

    usuario_id = usuario.get("usuario_id")
    nombre_rol = rol.get("nombre") or ""

    if not usuario_id:
        logger.error("El login no devolvió un usuario_id válido.")
        raise HTTPException(
            status_code=500,
            detail="No fue posible generar la sesión.",
        )

    resultado["token"] = crear_token(
        int(usuario_id),
        nombre_rol,
    )

    return resultado


@router.get("/{usuario_id}")
def obtener_usuario(usuario_id: int):
    usuario = repo.obtener_por_id(usuario_id)

    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado.",
        )

    return usuario


@router.post("/")
def crear_usuario(usuario: Usuario):
    try:
        nuevo_id = repo.crear(usuario)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))

    if not nuevo_id:
        raise HTTPException(
            status_code=500,
            detail="No se pudo crear el usuario.",
        )

    return {
        "mensaje": "Usuario registrado exitosamente.",
        "id": nuevo_id,
    }


@router.delete("/{usuario_id}")
def eliminar_usuario(usuario_id: int):
    try:
        exito = repo.eliminar(usuario_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))

    if not exito:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado.",
        )

    return {"mensaje": "Usuario eliminado correctamente."}


@router.put("/{usuario_id}")
def actualizar_usuario(usuario_id: int, usuario: UsuarioUpdate):
    try:
        exito = repo.actualizar(usuario_id, usuario)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))

    if not exito:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado o no se pudo actualizar.",
        )

    return {"mensaje": "Usuario actualizado correctamente."}
