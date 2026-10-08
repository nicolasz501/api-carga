import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    roles,
    modulos,
    modulos_rol,
    facultades,
    usuarios,
    periodos_academicos,
    programas_academicos,
    asignaturas,
    grupos,
    carga_docente,
    horarios,
    evaluaciones,
    preguntas,
    respuestas,
)


app = FastAPI(
    title="API Carga docente",
    description="Backend modular para monitoreo académico usando FastAPI y PostgreSQL puro",
    version="1.0.0"
)


# =========================================================
# CORS
# =========================================================

# 1. Lista base de orígenes de desarrollo local y producción
ALLOWED_ORIGINS_DEFAULT = [
    "http://localhost:5173",
    "http://localhost:4173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

# 2. Obtener la variable de entorno
origins_env = os.getenv("ALLOWED_ORIGINS", "")

# 3. Construir la lista combinada sin duplicados
origins_list = ALLOWED_ORIGINS_DEFAULT.copy()

if origins_env:
    extra_origins = [
        o.strip().strip("'\"") 
        for o in origins_env.split(",") 
        if o.strip()
    ]
    origins_list.extend(extra_origins)

# Eliminar duplicados manteniendo el orden
origins = list(dict.fromkeys(origins_list))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # Lista explícita de orígenes permitidos
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


# =========================================================
# ROUTERS
# =========================================================

app.include_router(roles.router)
app.include_router(modulos.router)
app.include_router(modulos_rol.router)
app.include_router(facultades.router)
app.include_router(usuarios.router)

app.include_router(periodos_academicos.router)
app.include_router(programas_academicos.router)
app.include_router(asignaturas.router)
app.include_router(grupos.router)
app.include_router(carga_docente.router)
app.include_router(horarios.router)
app.include_router(evaluaciones.router)
app.include_router(preguntas.router)
app.include_router(respuestas.router)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/", tags=["Health"])
def estado_api():
    return {
        "status": "ok",
        "mensaje": "La API de monitoreo se encuentra en línea y funcional",
        "version": app.version
    }