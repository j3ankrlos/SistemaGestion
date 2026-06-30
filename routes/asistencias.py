from flask import Blueprint, render_template, request, jsonify, session
from flask_login import current_user
from database.connection import execute_query, get_connection
from utils.decorators import login_required, permission_required
from datetime import datetime, timedelta, time

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
                  p.NumeroFicha, t.H_Entrada, t.H_Salida, t.IdTurno
           FROM (Personal p
           LEFT JOIN Turnos t ON p.FK_IdTurno = t.IdTurno)
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
            """SELECT Fk_IdPersonal, Estado, Fk_IdIncidencia, Observacion,
                      HoraEntrada, HoraSalida,
                      Diurnas, Nocturnas, TotalHorasExtras
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
                'hora_entrada': r[4].strftime('%H:%M') if r[4] else None,
                'hora_salida': r[5].strftime('%H:%M') if r[5] else None,
                'diurnas': float(r[6]) if r[6] is not None else None,
                'nocturnas': float(r[7]) if r[7] is not None else None,
                'total_horas_extras': float(r[8]) if r[8] is not None else None,
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

        # Horas del turno (valores por defecto)
        h_entrada_turno = p[5].strftime('%H:%M') if p[5] else ''
        h_salida_turno = p[6].strftime('%H:%M') if p[6] else ''
        id_turno = p[7]

        if pid in asistencias_dict:
            # Ya tiene asistencia registrada → respetar ese dato
            estado = asist.get('estado', 'Asistente')
            id_inc = asist.get('id_incidencia')
            obs = asist.get('observacion', '')
            sigla_inc = ''
            hora_entrada = asist.get('hora_entrada') or h_entrada_turno
            hora_salida = asist.get('hora_salida') or h_salida_turno
        elif pid in incidencias_activas:
            # Incidencia activa detectada → auto-asignar
            ia = incidencias_activas[pid]
            estado = 'Incidencia'
            id_inc = ia['id_incidencia']
            obs = ia['observacion']
            sigla_inc = ia['sigla_incidencia']
            hora_entrada = h_entrada_turno
            hora_salida = h_salida_turno
        else:
            estado = 'Asistente'
            id_inc = None
            obs = ''
            sigla_inc = ''
            hora_entrada = h_entrada_turno
            hora_salida = h_salida_turno

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
            'hora_entrada': hora_entrada,
            'hora_salida': hora_salida,
            'h_entrada_turno': h_entrada_turno,
            'h_salida_turno': h_salida_turno,
            'id_turno': id_turno,
            'diurnas': asist.get('diurnas') if isinstance(asist, dict) else None,
            'nocturnas': asist.get('nocturnas') if isinstance(asist, dict) else None,
            'total_horas_extras': asist.get('total_horas_extras') if isinstance(asist, dict) else None,
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

        from database.connection import get_connection, close_connection
        conn = get_connection()
        cursor = conn.cursor()

        try:
            for reg in registros:
                id_personal = reg.get('id_personal')
                estado = reg.get('estado', 'Asistente')
                id_incidencia = reg.get('id_incidencia')
                observacion = reg.get('observacion', '')
                fecha_inicio_hi = reg.get('fecha_inicio', fecha)  # Para HistorialIncidencias
                fecha_fin_hi = reg.get('fecha_fin', None)         # Opcional
                hora_entrada = reg.get('hora_entrada')
                hora_salida = reg.get('hora_salida')

                if not id_personal:
                    continue

                # Convertir horas string a datetime.time para guardar en Access
                hora_entrada_val = None
                hora_salida_val = None
                if hora_entrada:
                    try:
                        partes = hora_entrada.split(':')
                        hora_entrada_val = time(int(partes[0]), int(partes[1]))
                    except:
                        pass
                if hora_salida:
                    try:
                        partes = hora_salida.split(':')
                        hora_salida_val = time(int(partes[0]), int(partes[1]))
                    except:
                        pass

                # ── Calcular horas extras ──
                diurnas_val = 0
                nocturnas_val = 0
                total_he_val = 0
                if hora_salida_val:
                    try:
                        cursor.execute(
                            """SELECT t.H_Salida FROM Turnos t
                               INNER JOIN Personal p ON p.FK_IdTurno = t.IdTurno
                               WHERE p.IdPersonal = ?""",
                            (id_personal,)
                        )
                        turno_row = cursor.fetchone()
                        if turno_row and turno_row[0]:
                            he = _calcular_horas_extras(hora_salida_val, turno_row[0])
                            diurnas_val = he['diurnas']
                            nocturnas_val = he['nocturnas']
                            total_he_val = he['total_horas']
                    except:
                        pass

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
                            Estado=?, Fk_IdIncidencia=?, Observacion=?,
                            HoraEntrada=?, HoraSalida=?,
                            Diurnas=?, Nocturnas=?, TotalHorasExtras=?
                           WHERE IdAsistencia=?""",
                        (estado, id_incidencia, observacion,
                         hora_entrada_val, hora_salida_val,
                         diurnas_val, nocturnas_val, total_he_val, existing[0])
                    )
                else:
                    # Insertar
                    cursor.execute(
                        """INSERT INTO Asistencias
                           (Fk_IdPersonal, FechaAsistencia, Estado, Fk_IdIncidencia,
                            Observacion, FechaRegistro, Fk_IdUsuario,
                            HoraEntrada, HoraSalida,
                            Diurnas, Nocturnas, TotalHorasExtras)
                           VALUES (?, ?, ?, ?, ?, Now(), ?, ?, ?, ?, ?, ?)""",
                        (id_personal, fecha, estado, id_incidencia,
                         observacion, usuario_id,
                         hora_entrada_val, hora_salida_val,
                         diurnas_val, nocturnas_val, total_he_val)
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
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
            close_connection()

        return jsonify({'success': True, 'message': f'Asistencias guardadas correctamente ({len(registros)} registros).'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ──────────────────────────────────────────────
#  Función: Calcular horas extras
# ──────────────────────────────────────────────
def _time_to_min(t):
    """Convierte un time a minutos del día (0-1439)."""
    return t.hour * 60 + t.minute

def _calcular_horas_extras(hora_salida_real, h_salida_turno):
    """
    Calcula horas extras comparando la hora real de salida vs la programada.
    Retorna dict con total_horas, diurnas, nocturnas según rangos de HorasExtras.
    """
    if not hora_salida_real or not h_salida_turno:
        return {'total_horas': 0, 'diurnas': 0, 'nocturnas': 0, 'texto': ''}

    # Obtener rangos de horas extras desde la BD
    rangos = execute_query("SELECT HorasE, Desde, Hasta FROM HorasExtras", fetchall=True) or []

    real_min = _time_to_min(hora_salida_real)
    turno_min = _time_to_min(h_salida_turno)

    # Si real <= turno, no hay horas extras
    if real_min <= turno_min:
        return {'total_horas': 0, 'diurnas': 0, 'nocturnas': 0, 'texto': ''}

    # Total de minutos extras
    total_min = real_min - turno_min

    # Distribuir minutos extras según rangos
    diurnas_min = 0
    nocturnas_min = 0

    for r in rangos:
        tipo = r[0]
        r_desde = r[1]
        r_hasta = r[2]
        r_desde_min = _time_to_min(r_desde)
        r_hasta_min = _time_to_min(r_hasta)

        es_nocturno = 'NOCTURN' in tipo.upper()
        es_diurno = 'DIURN' in tipo.upper()

        for m in range(1, total_min + 1):
            min_actual = (turno_min + m) % 1440  # wrappear a 24h
            if _en_rango(min_actual, r_desde_min, r_hasta_min):
                if es_nocturno:
                    nocturnas_min += 1
                elif es_diurno:
                    diurnas_min += 1

    # Redondear a 1 decimal (convertir a horas)
    diurnas = round(diurnas_min / 60, 1)
    nocturnas = round(nocturnas_min / 60, 1)
    total = round(diurnas + nocturnas, 1)

    # Texto descriptivo
    partes = []
    if diurnas > 0:
        partes.append(f"{diurnas} D")
    if nocturnas > 0:
        partes.append(f"{nocturnas} N")
    texto = ' + '.join(partes) if partes else ''

    return {
        'total_horas': total,
        'diurnas': diurnas,
        'nocturnas': nocturnas,
        'texto': texto,
    }

def _en_rango(minuto, inicio, fin):
    """Verifica si un minuto cae dentro de un rango (maneja wraparound)."""
    if inicio <= fin:
        return inicio <= minuto <= fin
    else:
        # Rango que cruza la medianoche (ej: 19:00-04:59)
        return minuto >= inicio or minuto <= fin


# ──────────────────────────────────────────────
#  API: Calcular horas extras dinámicamente
# ──────────────────────────────────────────────
@asistencias_bp.route('/api/calcular-horas-extras', methods=['POST'])
@login_required
def api_calcular_horas_extras():
    """
    Recibe la hora de salida real y el id del turno,
    devuelve el cálculo de horas extras.
    """
    try:
        data = request.get_json()
        hora_real_str = data.get('hora_salida_real', '').strip()
        id_turno = data.get('id_turno')

        if not hora_real_str or not id_turno:
            return jsonify({'total_horas': 0, 'diurnas': 0, 'nocturnas': 0, 'texto': ''})

        # Obtener hora de salida del turno
        turno = execute_query(
            "SELECT H_Salida FROM Turnos WHERE IdTurno = ?",
            (id_turno,), fetchone=True
        )
        if not turno or not turno[0]:
            return jsonify({'total_horas': 0, 'diurnas': 0, 'nocturnas': 0, 'texto': ''})

        h_salida_turno = turno[0]

        # Convertir hora real string a time
        partes = hora_real_str.split(':')
        hora_real = time(int(partes[0]), int(partes[1]))

        resultado = _calcular_horas_extras(hora_real, h_salida_turno)
        return jsonify(resultado)

    except Exception as e:
        return jsonify({'total_horas': 0, 'diurnas': 0, 'nocturnas': 0, 'texto': str(e)})
# ──────────────────────────────────────────────
@asistencias_bp.route('/api/historial')
@login_required
@permission_required('asistencias.ver')
def api_historial():
    """Devuelve el historial de asistencias con filtros opcionales."""
    id_area = request.args.get('area', type=int)
    fecha_desde = request.args.get('desde', '').strip()
    fecha_hasta = request.args.get('hasta', '').strip()
    search = request.args.get('search', '').strip()
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

    if search:
        where.append("(p.Nombres LIKE ? OR p.Apellidos LIKE ? OR p.Cedula LIKE ?)")
        like_val = f"%{search}%"
        params.extend([like_val, like_val, like_val])

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
                   ar.Area, a.HoraEntrada, a.HoraSalida,
                   a.Diurnas, a.Nocturnas, a.TotalHorasExtras
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
        hora_entrada = r[13].strftime('%H:%M') if r[13] else ''
        hora_salida = r[14].strftime('%H:%M') if r[14] else ''
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
            'hora_entrada': hora_entrada,
            'hora_salida': hora_salida,
            'diurnas': float(r[15]) if r[15] is not None else None,
            'nocturnas': float(r[16]) if r[16] is not None else None,
            'total_horas_extras': float(r[17]) if r[17] is not None else None,
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
        "observacion": "...",
        "hora_entrada": "07:30",
        "hora_salida": "16:00"
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

        from database.connection import get_connection, close_connection
        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Convertir horas string a datetime.time
            hora_entrada_str = data.get('hora_entrada')
            hora_salida_str = data.get('hora_salida')
            hora_entrada_val = None
            hora_salida_val = None
            if hora_entrada_str:
                try:
                    partes = hora_entrada_str.split(':')
                    hora_entrada_val = time(int(partes[0]), int(partes[1]))
                except:
                    pass
            if hora_salida_str:
                try:
                    partes = hora_salida_str.split(':')
                    hora_salida_val = time(int(partes[0]), int(partes[1]))
                except:
                    pass

            # ── Calcular horas extras ──
            diurnas_val = 0
            nocturnas_val = 0
            total_he_val = 0
            if hora_salida_val:
                try:
                    cursor.execute(
                        """SELECT t.H_Salida FROM Turnos t
                           INNER JOIN Personal p ON p.FK_IdTurno = t.IdTurno
                           WHERE p.IdPersonal = ?""",
                        (id_personal,)
                    )
                    turno_row = cursor.fetchone()
                    if turno_row and turno_row[0]:
                        he = _calcular_horas_extras(hora_salida_val, turno_row[0])
                        diurnas_val = he['diurnas']
                        nocturnas_val = he['nocturnas']
                        total_he_val = he['total_horas']
                except:
                    pass

            # Actualizar la asistencia
            cursor.execute(
                """UPDATE Asistencias SET
                    Estado=?, Fk_IdIncidencia=?, Observacion=?,
                    HoraEntrada=?, HoraSalida=?,
                    Diurnas=?, Nocturnas=?, TotalHorasExtras=?
                   WHERE IdAsistencia=?""",
                (estado, id_incidencia if estado == 'Incidencia' else None,
                 observacion,
                 hora_entrada_val, hora_salida_val,
                 diurnas_val, nocturnas_val, total_he_val,
                 id_asistencia)
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
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
            close_connection()

        return jsonify({'success': True, 'message': 'Asistencia actualizada correctamente.'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
