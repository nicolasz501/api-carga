
from app.core.database import Database


class ReportesRepository:

    # ==========================================
    # REGISTRAR HISTORIAL DE REPORTES
    # ==========================================

    def registrar_historial(
        self,
        usuario_id,
        tipo_reporte,
        formato,
        filtros
    ):
        conexion = Database().get_connection()

        if conexion is None:
            raise Exception(
                "No se pudo conectar con PostgreSQL"
            )

        cursor = None

        try:
            cursor = conexion.cursor()

            sql = """
                INSERT INTO historial_reportes (
                    usuario_id,
                    tipo_reporte,
                    formato,
                    fecha_inicio,
                    fecha_fin,
                    programa,
                    apellido,
                    tipo_evaluacion,
                    fecha_generacion
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )
                RETURNING reporte_id
            """

            parametros = (
                usuario_id,
                tipo_reporte,
                formato,
                getattr(filtros, "fecha_inicio", None),
                getattr(filtros, "fecha_fin", None),
                getattr(filtros, "programa", None),
                getattr(filtros, "apellido", None),
                getattr(filtros, "tipo_evaluacion", None)
            )

            cursor.execute(sql, parametros)

            resultado = cursor.fetchone()

            conexion.commit()

            return dict(resultado) if resultado else None

        except Exception:
            conexion.rollback()
            raise

        finally:
            if cursor:
                cursor.close()

            conexion.close()

    # ==========================================
    # REPORTE DE CARGA DOCENTE
    # ==========================================

    def obtener_carga_docente(self, filtros):

        conexion = Database().get_connection()

        if conexion is None:
            raise Exception(
                "No se pudo conectar con PostgreSQL"
            )

        cursor = None

        try:
            cursor = conexion.cursor()

            sql = """
                SELECT
                    CONCAT_WS(
                        ' ',
                        u.primer_nombre,
                        u.segundo_nombre,
                        u.primer_apellido,
                        u.segundo_apellido
                    ) AS docente,

                    pr.nombre_programa AS programa,

                    a.nombres_asignaturas AS asignatura,

                    g.nombre_grupos AS grupo,

                    pa.codigo_periodo AS periodo,

                    pa.fecha_inicio,

                    pa.fecha_finalizar,

                    CASE
                        WHEN cd.estado = TRUE THEN 'Activa'
                        ELSE 'Inactiva'
                    END AS estado

                FROM carga_docente cd

                INNER JOIN usuarios u
                    ON cd.user_id = u.usuario_id

                INNER JOIN periodos_academicos pa
                    ON cd.periodo_id = pa.periodo_id

                INNER JOIN grupos g
                    ON cd.id_grupo = g.grupos_id

                INNER JOIN asignaturas a
                    ON g.asignaturas_id = a.asignatura_id

                INNER JOIN programas_academicos pr
                    ON a.programa_id = pr.programa_id

                WHERE 1 = 1
            """

            parametros = []

            # Filtro por fecha inicial
            if filtros.fecha_inicio:
                sql += """
                    AND pa.fecha_finalizar >= %s
                """
                parametros.append(filtros.fecha_inicio)

            # Filtro por fecha final
            if filtros.fecha_fin:
                sql += """
                    AND pa.fecha_inicio <= %s
                """
                parametros.append(filtros.fecha_fin)

            # Filtro por programa
            if filtros.programa:
                sql += """
                    AND pr.nombre_programa ILIKE %s
                """
                parametros.append(
                    f"%{filtros.programa}%"
                )

            # Filtro por apellido
            if filtros.apellido:
                sql += """
                    AND (
                        u.primer_apellido ILIKE %s
                        OR u.segundo_apellido ILIKE %s
                    )
                """

                parametros.extend([
                    f"%{filtros.apellido}%",
                    f"%{filtros.apellido}%"
                ])

            sql += """
                ORDER BY
                    u.primer_apellido,
                    u.primer_nombre,
                    pa.fecha_inicio
            """

            cursor.execute(sql, parametros)

            filas = cursor.fetchall()

            return [dict(fila) for fila in filas]

        finally:
            if cursor:
                cursor.close()

            conexion.close()

    # ==========================================
    # REPORTE DE EVALUACIONES
    # ==========================================

    def obtener_evaluaciones(self, filtros):

        conexion = Database().get_connection()

        if conexion is None:
            raise Exception(
                "No se pudo conectar con PostgreSQL"
            )

        cursor = None

        try:
            cursor = conexion.cursor()

            sql = """
                SELECT
                    CONCAT_WS(
                        ' ',
                        u.primer_nombre,
                        u.segundo_nombre,
                        u.primer_apellido,
                        u.segundo_apellido
                    ) AS docente,

                    pr.nombre_programa AS programa,

                    e.tipo_evaluacion,

                    e.titulo,

                    e.fecha_envio,

                    ROUND(
                        AVG(r.puntaje)::numeric,
                        2
                    ) AS promedio,

                    COUNT(
                        DISTINCT r.pregunta_evaluacion_id
                    ) AS preguntas_respondidas,

                    STRING_AGG(
                        DISTINCT NULLIF(r.comentario, ''),
                        ' | '
                    ) AS comentarios

                FROM evaluaciones e

                INNER JOIN carga_docente cd
                    ON e.carga_id = cd.carga_id

                INNER JOIN usuarios u
                    ON cd.user_id = u.usuario_id

                INNER JOIN periodos_academicos pa
                    ON e.periodo_id = pa.periodo_id

                INNER JOIN grupos g
                    ON cd.id_grupo = g.grupos_id

                INNER JOIN asignaturas a
                    ON g.asignaturas_id = a.asignatura_id

                INNER JOIN programas_academicos pr
                    ON a.programa_id = pr.programa_id

                LEFT JOIN preguntas_evaluacion pe
                    ON pe.evaluacion_id = e.evaluacion_id

                LEFT JOIN respuestas r
                    ON r.pregunta_evaluacion_id =
                       pe.pregunta_evaluacion_id

                WHERE 1 = 1
            """

            parametros = []

            # Filtro por fecha inicial
            if filtros.fecha_inicio:
                sql += """
                    AND e.fecha_envio::date >= %s
                """
                parametros.append(filtros.fecha_inicio)

            # Filtro por fecha final
            if filtros.fecha_fin:
                sql += """
                    AND e.fecha_envio::date <= %s
                """
                parametros.append(filtros.fecha_fin)

            # Filtro por programa
            if filtros.programa:
                sql += """
                    AND pr.nombre_programa ILIKE %s
                """
                parametros.append(
                    f"%{filtros.programa}%"
                )

            # Filtro por apellido
            if filtros.apellido:
                sql += """
                    AND (
                        u.primer_apellido ILIKE %s
                        OR u.segundo_apellido ILIKE %s
                    )
                """

                parametros.extend([
                    f"%{filtros.apellido}%",
                    f"%{filtros.apellido}%"
                ])

            # Filtro por tipo de evaluación
            if filtros.tipo_evaluacion:
                sql += """
                    AND e.tipo_evaluacion ILIKE %s
                """

                parametros.append(
                    f"%{filtros.tipo_evaluacion}%"
                )

            sql += """
                GROUP BY
                    e.evaluacion_id,
                    u.primer_nombre,
                    u.segundo_nombre,
                    u.primer_apellido,
                    u.segundo_apellido,
                    pr.nombre_programa,
                    e.tipo_evaluacion,
                    e.titulo,
                    e.fecha_envio

                ORDER BY
                    e.fecha_envio DESC
            """

            cursor.execute(sql, parametros)

            filas = cursor.fetchall()

            return [dict(fila) for fila in filas]

        finally:
            if cursor:
                cursor.close()

            conexion.close()
