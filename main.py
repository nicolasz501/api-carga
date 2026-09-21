from fastapi import FastAPI 

from app.api import roles
from app.api import modulos
from app.api import modulos_rol
from app.api import facultades
from app.api import usuarios
from app.api import periodos_academicos
from app.api import programas_academicos
from app.api import asignaturas
from app.api import grupos
from app.api import carga_docente
from app.api import horarios
from app.api import evaluaciones
from app.api import preguntas
from app.api import respuestas

app = FastAPI( 

    title="API de Desempeño Estudiantil", 

    description="Backend modular para monitoreo académico usando FastAPI y PostgreSQL puro", 

    version="1.0.0" 

) 

 

# Conectamos el módulo de rutas a la aplicación principal 

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
 

@app.get("/") 

def estado_api(): 

    return {"mensaje": "La API de monitoreo se encuentra en línea y funcional"} 