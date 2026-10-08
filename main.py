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

# 1. Obtener los orígenes desde la variable de entorno
# 1. Obtener los orígenes desde la variable de entorno
origins_env = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:4173,http://127.0.0.1:5173"
)

# 2. Convertir la cadena en lista limpia
origins = [origin.strip() for origin in origins_env.split(",") if origin.strip()]

# Agrega la URL de tu frontend desplegado en Render / Vercel o Netlify si aplica
# origins.append("https://tu-frontend.onrender.com")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # <-- Usar la lista explicita en lugar de ["*"]
    allow_credentials=True,      # <-- Se mantiene en True
    allow_methods=["*"],
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