
from app.repositories.reportes_repository import ReportesRepository
from app.utils.generar_archivos import generar_pdf, generar_excel


class ReportesService:

    def __init__(self):
        self.repository = ReportesRepository()

    # ==========================================
    # COLUMNAS DE LOS REPORTES
    # ==========================================

    def columnas_carga(self):
        return [
            "docente",
            "programa",
            "asignatura",
            "grupo",
            "periodo",
            "fecha_inicio",
            "fecha_finalizar",
            "estado"
        ]

    def columnas_evaluaciones(self):
        return [
            "docente",
            "programa",
            "tipo_evaluacion",
            "titulo",
            "fecha_envio",
            "promedio",
            "preguntas_respondidas",
            "comentarios"
        ]

    # ==========================================
    # REPORTE CARGA DOCENTE PDF
    # ==========================================

    def reporte_carga_pdf(self, filtros, usuario_id):

        datos = self.repository.obtener_carga_docente(filtros)

        archivo = generar_pdf(
            datos,
            "REPORTE DE CARGA DOCENTE",
            self.columnas_carga()
        )

        self.repository.registrar_historial(
            usuario_id=usuario_id,
            tipo_reporte="CARGA_DOCENTE",
            formato="PDF",
            filtros=filtros
        )

        return archivo

    # ==========================================
    # REPORTE CARGA DOCENTE EXCEL
    # ==========================================

    def reporte_carga_excel(self, filtros, usuario_id):

        datos = self.repository.obtener_carga_docente(filtros)

        archivo = generar_excel(
            datos,
            "REPORTE DE CARGA DOCENTE",
            self.columnas_carga()
        )

        self.repository.registrar_historial(
            usuario_id=usuario_id,
            tipo_reporte="CARGA_DOCENTE",
            formato="EXCEL",
            filtros=filtros
        )

        return archivo

    # ==========================================
    # REPORTE EVALUACIONES PDF
    # ==========================================

    def reporte_evaluaciones_pdf(self, filtros, usuario_id):

        datos = self.repository.obtener_evaluaciones(filtros)

        archivo = generar_pdf(
            datos,
            "REPORTE DE EVALUACIÓN DE DESEMPEÑO",
            self.columnas_evaluaciones()
        )

        self.repository.registrar_historial(
            usuario_id=usuario_id,
            tipo_reporte="EVALUACIONES",
            formato="PDF",
            filtros=filtros
        )

        return archivo

    # ==========================================
    # REPORTE EVALUACIONES EXCEL
    # ==========================================

    def reporte_evaluaciones_excel(self, filtros, usuario_id):

        datos = self.repository.obtener_evaluaciones(filtros)

        archivo = generar_excel(
            datos,
            "REPORTE DE EVALUACIÓN DE DESEMPEÑO",
            self.columnas_evaluaciones()
        )

        self.repository.registrar_historial(
            usuario_id=usuario_id,
            tipo_reporte="EVALUACIONES",
            formato="EXCEL",
            filtros=filtros
        )

        return archivo
