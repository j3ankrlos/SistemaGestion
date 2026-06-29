from flask import Blueprint, render_template, request, jsonify, session
from flask_login import current_user
from database.connection import execute_query, get_connection
from utils.decorators import login_required, permission_required
from datetime import datetime

asistencias_bp = Blueprint('asistencias', __name__)


# ──────────────────────────────────────────────
#  Página principal
# ──────────────────────────────────────────────
@asistencias_bp.route('/')
@login_required
@permission_required('asistencias.ver')
def index():
    """Renderiza la página de asistencias diarias."""
    # Áreas filtradas por sitio si no es SuperAdmin
    is_admin = current_user.rol_id == 1
    user_sitio = current_user.fk_sitio
    if is_admin or not user_sitio:
        areas = execute_query("SELECT IdArea, Area FROM Areas ORDER BY Area", fetchall=True) or []
    else:
        areas = execute_query("SELECT IdArea, Area FROM Areas WHERE Fk_IdSitio = ? ORDER BY Area", (user_sitio,), fetchall=True) or []
    tipos_incidencias = execute_query(
        "SELECT IdIncidencia, Incidencia, SiglaIncidencia FROM Incidencias ORDER BY Incidencia",
        fetchall=True
    ) or []
    return render_template('asistencias/index.html', areas=areas, tipos_incidencias=tipos_incidencias)


# ──────────────────────────────────────────────
#  Página de historial de asistencias
# ──────────────────────────────────────────────
@asistencias_bp.route('/historial')
@login_required
@permission_required('asistencias.ver')
def historial():
    """Renderiza la página de historial de asistencias."""
    is_admin = current_user.rol_id == 1
    user_sitio = current_user.fk_sitio
    if is_admin or not user_sitio:
        areas = execute_query("SELECT IdArea, Area FROM Areas ORDER BY Area", fetchall=True) or []
    else:
        areas = execute_query("SELECT IdArea, Area FROM Areas WHERE Fk_IdSitio = ? ORDER BY Area", (user_sitio,), fetchall=True) or []
    tipos_incidencias = execute_query(
        "SELECT IdIncidencia, Incidencia, SiglaIncidencia FROM Incidencias ORDER BY Incidencia",
        fetchall=True
    ) or []
    return render_template('asistencias/historial.html', areas=areas, tipos_incidencias=tipos_incidencias)


# ──────────────────────────────────────────────
#  API: Personal por área + estado de asistencia
# ──────────────────────────────────────────────
@asistencias_bp.route('/api/personal')
@login_required
@permission_required('asistencias.ver')
def api_personal_por_area():
    """
    Devuelve el personal activo de un área, con su estado de asistencia
    para la fecha indicada (si ya fue registrado).
    """
    id_area = request.args.get('area', type=int)
    fecha_str = request.args.get('fecha', '').strip()

    if not id_area:
        return jsonify({'success': False, 'error': 'Debe seleccionar un área.'})

    if not fecha_str:
        fecha_str = datetime.now().strftime('%Y-%m-%d')

    # Personal activo del área seleccionada
    is_admin = current_user.rol_id == 1
    user_sitio = current_user.fk_sitio
    sitio_filter = ""
    sitio_params = ()
    if not is_admin and user_sitio:
        sitio_filter = " AND p.Fk_IdCentroCosto IN (SELECT IdCentroCosto FROM CentrosCostos WHERE Fk_IdSitio = ?)"
        sitio_params = (user_sitio,)

    personal = execute_query(
        """SELECT p.IdPersonal, p.Nombres, p.Apellidos, p.Cedula,
                  p.NumeroFicha
           FROM Personal p
           INNER JOIN EstatusActual ea ON p.FK_IdEstatusActual = ea.IdEstatusA
           WHERE p.Fk_Area = ?
             AND ea.EstatusA = 'ACTIVO'
             {}
           ORDER BY p.Apellidos, p.Nombres""".format(sitio_filter),
        (id_area,) + sitio_params,
        fetchall=True
    ) or []

    # Si ya hay asistencias registradas para esta fecha, las obtenemos
    asistencias_dict = {}
    if personal:
        rows = execute_query(
            """SELECT Fk_IdPersonal, Estado, Fk_IdIncidencia, Observacion
               FROM Asistencias
               WHERE FechaAsistencia = ? AND Fk_IdPersonal IN ({})""".format(
                ','.join('?' for _ in personal)
            ),
            (fecha_str,) + tuple(p[0] for p in personal),
            fetchall=True
        ) or []
        for r in rows:
            asistencias_dict[r[0]] = {
                'estado': r[1] or 'Asistente',
                'id_incidencia': r[2],
                'observacion': r[3] or '',
            }

    # ── Auto-detectar incidencias activas desde HistorialIncidencias ──
    # Para personal sin asistencia registrada, ver si hay una incidencia
    # activa (con FechaInicio <= fecha_consulta y FechaFin >= fecha_consulta o NULL)
    ids_sin_asistencia = [p[0] for p in personal if p[0] not in asistencias_dict]
    incidencias_activas = {}
    if ids_sin_asistencia:
        placeholders = ','.join('?' for _ in ids_sin_asistencia)
        hi_rows = execute_query(
            f"""SELECT h.Fk_IdPersonal, h.Fk_IdIncidencia, i.Incidencia, i.SiglaIncidencia,
                       h.FechaInicio, h.FechaFin, h.Observacion
                FROM HistorialIncidencias h
                INNER JOIN Incidencias i ON h.Fk_IdIncidencia = i.IdIncidencia
                WHERE h.Fk_IdPersonal IN ({placeholders})
                  AND h.FechaInicio <= ?
                  AND (h.FechaFin IS NULL OR h.FechaFin >= ?)
                ORDER BY h.FechaInicio DESC""",
            tuple(ids_sin_asistencia) + (fecha_str, fecha_str),
            fetchall=True
        ) or []
        for hr in hi_rows:
            pid = hr[0]
            # Solo la primera (más reciente) por empleado
            if pid not in incidencias_activas:
                incidencias_activas[pid] = {
                    'id_incidencia': hr[1],
                    'incidencia': hr[2] or '',
                    'sigla_incidencia': hr[3] or '',
                    'observacion': hr[6] or '',
                }

    data = []
    for p in personal:
        pid = p[0]
        asist = asistencias_dict.get(pid, {})

        if pid in asistencias_dict:
            # Ya tiene asistencia registrada → respetar ese dato
            estado = asist.get('estado', 'Asistente')
            id_inc = asist.get('id_incidencia')
            obs = asist.get('observacion', '')
            sigla_inc = ''
        elif pid in incidencias_activas:
            # Incidencia activa detectada → auto-asignar
            ia = incidencias_activas[pid]
            estado = 'Incidencia'
            id_inc = ia['id_incidencia']
            obs = ia['observacion']
            sigla_inc = ia['sigla_incidencia']
        else:
            estado = 'Asistente'
            id_inc = None
            obs = ''
            sigla_inc = ''

        data.append({
            'id': pid,
            'nombres': p[1] or '',
            'apellidos': p[2] or '',
            'cedula': p[3] or '',
            'num_ficha': p[4] or '',
            'estado': estado,
            'id_incidencia': id_inc,
            'observacion': obs,
            'sigla_incidencia': sigla_inc,
            'procesado': pid in asistencias_dict,
        })

    ya_procesado = len(asistencias_dict) == len(personal) and len(personal) > 0

    return jsonify({'success': True, 'data': data, 'ya_procesado': ya_procesado})


# ──────────────────────────────────────────────
#  API: Guardar asistencias (lote)
# ──────────────────────────────────────────────
@asistencias_bp.route('/guardar', methods=['POST'])
@login_required
@permission_required('asistencias.registrar')
def guardar_asistencias():
    """
    Guarda o actualiza las asistencias del día para un área.
    Recibe JSON con:
    {
        "fecha": "2025-01-15",
        "registros": [
            {"id_personal": 1, "estado": "Asistente", "id_incidencia": null, "observacion": ""},
            ...
        ]
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Datos inválidos.'})

        fecha = data.get('fecha', '').strip()
        registros = data.get('registros', [])
        usuario_id = current_user.id

        if not fecha:
            return jsonify({'success': False, 'error': 'Fecha requerida.'})
        if not registros:
            return jsonify({'success': False, 'error': 'No hay registros para guardar.'})
        if not usuario_id:
            return jsonify({'success': False, 'error': 'Sesión no válida.'})

        from database.connection import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        for reg in registros:
            id_personal = reg.get('id_personal')
            estado = reg.get('estado', 'Asistente')
            id_incidencia = reg.get('id_incidencia')
            observacion = reg.get('observacion', '')
            fecha_inicio_hi = reg.get('fecha_inicio', fecha)  # Para HistorialIncidencias
            fecha_fin_hi = reg.get('fecha_fin', None)         # Opcional

            if not id_personal:
                continue

            # Verificar si ya existe registro para este personal+fecha
            cursor.execute(
                "SELECT IdAsistencia FROM Asistencias WHERE Fk_IdPersonal=? AND FechaAsistencia=?",
                (id_personal, fecha)
            )
            existing = cursor.fetchone()

            if existing:
                # Actualizar
                cursor.execute(
                    """UPDATE Asistencias SET
                        Estado=?, Fk_IdIncidencia=?, Observacion=?
                       WHERE IdAsistencia=?""",
                    (estado, id_incidencia, observacion, existing[0])
                )
            else:
                # Insertar
                cursor.execute(
                    """INSERT INTO Asistencias
                       (Fk_IdPersonal, FechaAsistencia, Estado, Fk_IdIncidencia, Observacion, FechaRegistro, Fk_IdUsuario)
                       VALUES (?, ?, ?, ?, ?, Now(), ?)""",
                    (id_personal, fecha, estado, id_incidencia, observacion, usuario_id)
                )

            # ── Si es Incidencia, también registrar en HistorialIncidencias ──
            if estado == 'Incidencia' and id_incidencia:
                # Verificar si ya existe un registro similar
                cursor.execute(
                    """SELECT IdHistorial FROM HistorialIncidencias
                       WHERE Fk_IdPersonal = ? AND Fk_IdIncidencia = ?
                         AND FechaInicio = ? AND (FechaFin = ? OR (FechaFin IS NULL AND ? IS NULL))""",
                    (id_personal, id_incidencia, fecha_inicio_hi, fecha_fin_hi, fecha_fin_hi)
                )
                if not cursor.fetchone():
                    cursor.execute(
                        """INSERT INTO HistorialIncidencias
                           (Fk_IdIncidencia, Fk_IdPersonal, FechaInicio, FechaFin,
                            Observacion, Fk_Status, Fk_IdUsuario, FechaRegistro)
                           VALUES (?, ?, ?, ?, ?, 1, ?, Now())""",
                        (id_incidencia, id_personal, fecha_inicio_hi, fecha_fin_hi,
                         observacion, usuario_id)
                    )

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': f'Asistencias guardadas correctamente ({len(registros)} registros).'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ──────────────────────────────────────────────
#  API: Historial de asistencias
# ──────────────────────────────────────────────
@asistencias_bp.route('/api/historial')
@login_required
@permission_required('asistencias.ver')
def api_historial():
    """Devuelve el historial de asistencias con filtros opcionales."""
    id_area = request.args.get('area', type=int)
    fecha_desde = request.args.get('desde', '').strip()
    fecha_hasta = request.args.get('hasta', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    where = []
    params = []

    if id_area:
        where.append("p.Fk_Area = ?")
        params.append(id_area)

    if fecha_desde:
        where.append("a.FechaAsistencia >= ?")
        params.append(fecha_desde)

    if fecha_hasta:
        where.append("a.FechaAsistencia <= ?")
        params.append(fecha_hasta)

    # Filtro por sitio si no es SuperAdmin
    is_admin = current_user.rol_id == 1
    user_sitio = current_user.fk_sitio
    if not is_admin and user_sitio:
        where.append("p.Fk_IdCentroCosto IN (SELECT IdCentroCosto FROM CentrosCostos WHERE Fk_IdSitio = ?)")
        params.append(user_sitio)

    where_sql = ""
    if where:
        where_sql = " WHERE " + " AND ".join(where)

    # Total
    count_row = execute_query(
        f"SELECT COUNT(*) FROM Asistencias a INNER JOIN Personal p ON a.Fk_IdPersonal = p.IdPersonal{where_sql}",
        params, fetchone=True
    )
    total = count_row[0] if count_row else 0
    total_pages = max(1, (total + per_page - 1) // per_page)

    # Datos
    rows = execute_query(
        f"""SELECT a.IdAsistencia, p.IdPersonal, p.Nombres, p.Apellidos, p.Cedula,
                   a.FechaAsistencia, a.Estado,
                   i.Incidencia, i.SiglaIncidencia,
                   a.Observacion, a.FechaRegistro, u.Usuario,
                   ar.Area
            FROM ((((Asistencias a
            INNER JOIN Personal p ON a.Fk_IdPersonal = p.IdPersonal)
            LEFT JOIN Incidencias i ON a.Fk_IdIncidencia = i.IdIncidencia)
            LEFT JOIN Usuarios u ON a.Fk_IdUsuario = u.IdUsuario)
            LEFT JOIN Areas ar ON p.Fk_Area = ar.IdArea)
            {where_sql}
            ORDER BY a.FechaAsistencia DESC, p.Apellidos, p.Nombres""",
        params, fetchall=True
    ) or []

    # Paginar
    start = (page - 1) * per_page
    end = start + per_page
    page_rows = rows[start:end]

    data = []
    for r in page_rows:
        fecha = r[5]
        data.append({
            'id': r[0],
            'id_personal': r[1],
            'nombres': r[2] or '',
            'apellidos': r[3] or '',
            'cedula': r[4] or '',
            'fecha': fecha.strftime('%d/%m/%Y') if fecha else '',
            'fecha_raw': fecha.strftime('%Y-%m-%d') if fecha else '',
            'estado': r[6] or '',
            'incidencia': r[7] or '',
            'sigla': r[8] or '',
            'observacion': r[9] or '',
            'fecha_registro': r[10].strftime('%d/%m/%Y %H:%M') if r[10] else '',
            'registrado_por': r[11] or '',
            'area': r[12] or '',
        })

    return jsonify({
        'success': True,
        'data': data,
        'total': total,
        'page': page,
        'total_pages': total_pages,
    })


# ──────────────────────────────────────────────
#  API: Actualizar una asistencia individual
# ──────────────────────────────────────────────
@asistencias_bp.route('/api/actualizar', methods=['POST'])
@login_required
@permission_required('asistencias.registrar')
def api_actualizar_asistencia():
    """
    Actualiza el estado de una asistencia individual desde el historial.
    Recibe JSON con:
    {
        "id_asistencia": 123,
        "estado": "Asistente" | "Dia Libre" | "Incidencia",
        "id_incidencia": null o int,
        "observacion": "..."
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Datos inválidos.'})

        id_asistencia = data.get('id_asistencia')
        estado = data.get('estado', 'Asistente')
        id_incidencia = data.get('id_incidencia')
        observacion = data.get('observacion', '')
        usuario_id = current_user.id

        if not id_asistencia:
            return jsonify({'success': False, 'error': 'ID de asistencia requerido.'})
        if not usuario_id:
            return jsonify({'success': False, 'error': 'Sesión no válida.'})

        # Obtener datos actuales de la asistencia
        current = execute_query(
            "SELECT Fk_IdPersonal, FechaAsistencia FROM Asistencias WHERE IdAsistencia=?",
            (id_asistencia,), fetchone=True
        )
        if not current:
            return jsonify({'success': False, 'error': 'Asistencia no encontrada.'})

        id_personal = current[0]
        fecha_asistencia = current[1]

        from database.connection import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        # Actualizar la asistencia
        cursor.execute(
            """UPDATE Asistencias SET
                Estado=?, Fk_IdIncidencia=?, Observacion=?
               WHERE IdAsistencia=?""",
            (estado, id_incidencia if estado == 'Incidencia' else None,
             observacion, id_asistencia)
        )

        # Si el estado cambió a Incidencia, registrar en HistorialIncidencias
        if estado == 'Incidencia' and id_incidencia:
            cursor.execute(
                """SELECT IdHistorial FROM HistorialIncidencias
                   WHERE Fk_IdPersonal = ? AND Fk_IdIncidencia = ?
                     AND FechaInicio = ? AND FechaFin IS NULL""",
                (id_personal, id_incidencia, fecha_asistencia)
            )
            if not cursor.fetchone():
                cursor.execute(
                    """INSERT INTO HistorialIncidencias
                       (Fk_IdIncidencia, Fk_IdPersonal, FechaInicio, FechaFin,
                        Observacion, Fk_Status, Fk_IdUsuario, FechaRegistro)
                       VALUES (?, ?, ?, NULL, ?, 1, ?, Now())""",
                    (id_incidencia, id_personal, fecha_asistencia,
                     observacion, usuario_id)
                )

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Asistencia actualizada correctamente.'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
