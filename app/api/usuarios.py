from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.Usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository


router = APIRouter(
    prefix="/usuarios",
    tags=["Gestión de Usuarios"]
)

repo = UsuarioRepository()


class LoginRequest(BaseModel):
    correo: str
    password: str


@router.get("/")
def listar_usuarios():
    return repo.obtener_todos()


# =========================================================
# LOGIN
# IMPORTANTE: va antes de /{usuario_id}
# =========================================================

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

    nuevo_id = repo.crear(usuario)

    if not nuevo_id:
        raise HTTPException(
            status_code=500,
            detail="No se pudo crear el usuario"
        )

    return {
        "mensaje": "Usuario registrado exitosamente",
        "id": nuevo_id
    }


@router.delete("/{usuario_id}")
def eliminar_usuario(usuario_id: int):

    exito = repo.eliminar(usuario_id)

    if not exito:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )

    return {
        "mensaje": "Usuario eliminado correctamente"
    }


@router.put("/{usuario_id}")
def actualizar_usuario(
    usuario_id: int,
    usuario: Usuario
):

    exito = repo.actualizar(
        usuario_id,
        usuario
    )

    if not exito:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )

    return {
        "mensaje": "Usuario actualizado correctamente"
    }