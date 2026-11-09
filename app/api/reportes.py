
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.models.reportes import FiltrosReporte
from app.services.reportes_service import ReportesService


router = APIRouter(
    prefix="/reportes",
    tags=["Reportes"]
)

service = ReportesService()


# ==========================================
# RESPUESTA DE DESCARGA
# ==========================================

def crear_descarga(archivo, nombre, tipo):

    archivo.seek(0)

    return StreamingResponse(
        archivo,
        media_type=tipo,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{nombre}"'
            )
        }
    )


# ==========================================
# CREAR FILTROS
# ==========================================

def crear_filtros(
    fecha_inicio,
    fecha_fin,
    programa,
    apellido,
    tipo_evaluacion=None
):

    if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
        raise HTTPException(
            status_code=400,
            detail=(
                "La fecha inicial no puede ser "
                "posterior a la fecha final"
            )
        )

    return FiltrosReporte(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        programa=programa,
        apellido=apellido,
        tipo_evaluacion=tipo_evaluacion
    )


# ==========================================
# REPORTE CARGA DOCENTE PDF
# ==========================================

@router.get("/carga-docente/pdf")
def descargar_carga_pdf(
    usuario_id: int = Query(..., gt=0),
    fecha_inicio: date | None = Query(None),
    fecha_fin: date | None = Query(None),
    programa: str | None = Query(None),
    apellido: str | None = Query(None)
):

    try:
        filtros = crear_filtros(
            fecha_inicio,
            fecha_fin,
            programa,
            apellido
        )

        archivo = service.reporte_carga_pdf(
            filtros,
            usuario_id
        )

        return crear_descarga(
            archivo,
            "reporte_carga_docente.pdf",
            "application/pdf"
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando reporte: {str(e)}"
        )


# ==========================================
# REPORTE CARGA DOCENTE EXCEL
# ==========================================

@router.get("/carga-docente/excel")
def descargar_carga_excel(
    usuario_id: int = Query(..., gt=0),
    fecha_inicio: date | None = Query(None),
    fecha_fin: date | None = Query(None),
    programa: str | None = Query(None),
    apellido: str | None = Query(None)
):

    try:
        filtros = crear_filtros(
            fecha_inicio,
            fecha_fin,
            programa,
            apellido
        )

        archivo = service.reporte_carga_excel(
            filtros,
            usuario_id
        )

        return crear_descarga(
            archivo,
            "reporte_carga_docente.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando reporte: {str(e)}"
        )


# ==========================================
# REPORTE EVALUACIONES PDF
# ==========================================

@router.get("/evaluaciones/pdf")
def descargar_evaluaciones_pdf(
    usuario_id: int = Query(..., gt=0),
    fecha_inicio: date | None = Query(None),
    fecha_fin: date | None = Query(None),
    programa: str | None = Query(None),
    apellido: str | None = Query(None),
    tipo_evaluacion: str | None = Query(None)
):

    try:
        filtros = crear_filtros(
            fecha_inicio,
            fecha_fin,
            programa,
            apellido,
            tipo_evaluacion
        )

        archivo = service.reporte_evaluaciones_pdf(
            filtros,
            usuario_id
        )

        return crear_descarga(
            archivo,
            "reporte_evaluaciones.pdf",
            "application/pdf"
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando reporte: {str(e)}"
        )


# ==========================================
# REPORTE EVALUACIONES EXCEL
# ==========================================

@router.get("/evaluaciones/excel")
def descargar_evaluaciones_excel(
    usuario_id: int = Query(..., gt=0),
    fecha_inicio: date | None = Query(None),
    fecha_fin: date | None = Query(None),
    programa: str | None = Query(None),
    apellido: str | None = Query(None),
    tipo_evaluacion: str | None = Query(None)
):

    try:
        filtros = crear_filtros(
            fecha_inicio,
            fecha_fin,
            programa,
            apellido,
            tipo_evaluacion
        )

        archivo = service.reporte_evaluaciones_excel(
            filtros,
            usuario_id
        )

        return crear_descarga(
            archivo,
            "reporte_evaluaciones.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando reporte: {str(e)}"
        )
