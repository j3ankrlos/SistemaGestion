from flask import Blueprint, render_template, request, jsonify, session
from flask_login import current_user
from database.connection import execute_query
from utils.decorators import login_required, permission_required

incidencias_bp = Blueprint('incidencias', __name__)

PER_PAGE = 15


# ──────────────────────────────────────────────
#  Página principal (listado del historial)
# ──────────────────────────────────────────────
@incidencias_bp.route('/')
@login_required
@permission_required('incidencias.ver')
def index():
    """Renderiza la página de gestión de incidencias."""
    # Obtener catálogo de tipos para el formulario
    tipos = execute_query("SELECT IdIncidencia, Incidencia, SiglaIncidencia FROM Incidencias ORDER BY Incidencia", fetchall=True) or []
    # Obtener personal para el selector
    personal = execute_query(
        "SELECT IdPersonal, Nombres, Apellidos, Cedula FROM Personal ORDER BY Apellidos, Nombres",
        fetchall=True
    ) or []
    return render_template('incidencias/index.html', tipos=tipos, personal=personal)


# ──────────────────────────────────────────────
#  API: Datos paginados del historial
# ──────────────────────────────────────────────
@incidencias_bp.route('/data')
@login_required
@permission_required('incidencias.ver')
def get_historial_data():
    """Devuelve JSON paginado del historial de incidencias."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    filtro_tipo = request.args.get('tipo', '', type=str)
    per_page = PER_PAGE

    where_clauses = []
    params = []

    if search:
        where_clauses.append("(p.Nombres LIKE ? OR p.Apellidos LIKE ? OR p.Cedula LIKE ? OR i.Incidencia LIKE ?)")
        s = f'%{search}%'
        params.extend([s, s, s, s])

    if filtro_tipo and filtro_tipo.isdigit():
        where_clauses.append("h.Fk_IdIncidencia = ?")
        params.append(int(filtro_tipo))

    where_sql = ""
    if where_clauses:
        where_sql = " WHERE " + " AND ".join(where_clauses)

    # Total de registros
    count_sql = f"SELECT COUNT(*) FROM ((((HistorialIncidencias h INNER JOIN Incidencias i ON h.Fk_IdIncidencia = i.IdIncidencia) INNER JOIN Personal p ON h.Fk_IdPersonal = p.IdPersonal) INNER JOIN Usuarios u ON h.Fk_IdUsuario = u.IdUsuario)){where_sql}"
    count_row = execute_query(count_sql, params, fetchone=True)
    total = count_row[0] if count_row else 0
    total_pages = max(1, (total + per_page - 1) // per_page)

    # Datos
    select_sql = f"""SELECT h.IdHistorial, h.FechaInicio, h.FechaFin, h.Observacion, h.Fk_Status, h.FechaRegistro,
                            i.IdIncidencia, i.Incidencia, i.SiglaIncidencia,
                            p.IdPersonal, p.Nombres, p.Apellidos, p.Cedula,
                            h.Fk_IdUsuario, u.Usuario
                     FROM ((((HistorialIncidencias h
                     INNER JOIN Incidencias i ON h.Fk_IdIncidencia = i.IdIncidencia)
                     INNER JOIN Personal p ON h.Fk_IdPersonal = p.IdPersonal)
                     INNER JOIN Usuarios u ON h.Fk_IdUsuario = u.IdUsuario))
                     {where_sql}
                     ORDER BY h.IdHistorial DESC"""

    all_rows = execute_query(select_sql, params, fetchall=True) or []
    start = (page - 1) * per_page
    end = start + per_page
    page_rows = all_rows[start:end]

    data = []
    for r in page_rows:
        data.append({
            'id': r[0],
            'fecha_inicio': r[1].strftime('%d/%m/%Y') if r[1] else '',
            'fecha_fin': r[2].strftime('%d/%m/%Y') if r[2] else '',
            'observacion': r[3] or '',
            'status': r[4] or 1,
            'fecha_registro': r[5].strftime('%d/%m/%Y %H:%M') if r[5] else '',
            'id_incidencia': r[6],
            'incidencia': r[7] or '',
            'sigla': r[8] or '',
            'id_personal': r[9],
            'registrado_por': r[14] or '',
            'nombres': r[10] or '',
            'apellidos': r[11] or '',
            'cedula': r[12] or '',
        })

    return jsonify({
        'data': data,
        'total': total,
        'page': page,
        'total_pages': total_pages,
        'per_page': per_page,
    })


# ──────────────────────────────────────────────
#  API: Crear nueva incidencia en el historial
# ──────────────────────────────────────────────
@incidencias_bp.route('/crear', methods=['POST'])
@login_required
@permission_required('incidencias.crear')
def crear_historial():
    """Crea un nuevo registro en HistorialIncidencias."""
    try:
        id_incidencia = request.form.get('id_incidencia', type=int)
        id_personal = request.form.get('id_personal', type=int)
        fecha_inicio = request.form.get('fecha_inicio', '').strip()
        fecha_fin = request.form.get('fecha_fin', '').strip() or None
        observacion = request.form.get('observacion', '').strip() or None

        if not id_incidencia or not id_personal or not fecha_inicio:
            return jsonify({'success': False, 'error': 'Faltan campos requeridos (tipo, personal, fecha inicio).'})

        usuario_id = current_user.id
        if not usuario_id:
            return jsonify({'success': False, 'error': 'Sesión no válida.'})

        execute_query(
            """INSERT INTO HistorialIncidencias (Fk_IdIncidencia, Fk_IdPersonal, FechaInicio, FechaFin, Observacion, Fk_Status, Fk_IdUsuario)
               VALUES (?, ?, ?, ?, ?, 1, ?)""",
            (id_incidencia, id_personal, fecha_inicio, fecha_fin, observacion, usuario_id),
            commit=True
        )
        return jsonify({'success': True, 'message': 'Incidencia registrada correctamente.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ──────────────────────────────────────────────
#  API: Eliminar una incidencia del historial
# ──────────────────────────────────────────────
@incidencias_bp.route('/<int:id>/eliminar', methods=['POST'])
@login_required
@permission_required('incidencias.eliminar')
def eliminar_historial(id):
    """Elimina un registro del historial."""
    try:
        execute_query("DELETE FROM HistorialIncidencias WHERE IdHistorial = ?", (id,), commit=True)
        return jsonify({'success': True, 'message': 'Incidencia eliminada correctamente.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ──────────────────────────────────────────────
#  API: Obtener tipos de incidencias (select)
# ──────────────────────────────────────────────
@incidencias_bp.route('/api/tipos')
@login_required
def api_tipos():
    """Devuelve el catálogo de tipos de incidencias."""
    rows = execute_query("SELECT IdIncidencia, Incidencia, SiglaIncidencia FROM Incidencias ORDER BY Incidencia", fetchall=True) or []
    return jsonify([{'id': r[0], 'nombre': r[1], 'sigla': r[2]} for r in rows])


# ──────────────────────────────────────────────
#  API: Crear nuevo tipo de incidencia (catálogo)
# ──────────────────────────────────────────────
@incidencias_bp.route('/api/tipos/crear', methods=['POST'])
@login_required
@permission_required('incidencias.crear')
def crear_tipo():
    """Crea un nuevo tipo en el catálogo Incidencias."""
    try:
        nombre = request.form.get('nombre', '').strip()
        sigla = request.form.get('sigla', '').strip().upper()
        if not nombre or not sigla:
            return jsonify({'success': False, 'error': 'Nombre y sigla son requeridos.'})
        execute_query(
            "INSERT INTO Incidencias (Incidencia, SiglaIncidencia) VALUES (?, ?)",
            (nombre, sigla), commit=True
        )
        return jsonify({'success': True, 'message': 'Tipo de incidencia creado correctamente.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ──────────────────────────────────────────────
#  API: Eliminar tipo de incidencia (catálogo)
# ──────────────────────────────────────────────
@incidencias_bp.route('/api/tipos/<int:id>/eliminar', methods=['POST'])
@login_required
@permission_required('incidencias.eliminar')
def eliminar_tipo(id):
    """Elimina un tipo del catálogo Incidencias."""
    try:
        # Verificar si hay historial usando este tipo
        count = execute_query(
            "SELECT COUNT(*) FROM HistorialIncidencias WHERE Fk_IdIncidencia = ?",
            (id,), fetchone=True
        )
        if count and count[0] > 0:
            return jsonify({'success': False, 'error': f'No se puede eliminar: {count[0]} registro(s) de historial usan este tipo.'})
        execute_query(
            "DELETE FROM Incidencias WHERE IdIncidencia = ?",
            (id,), commit=True
        )
        return jsonify({'success': True, 'message': 'Tipo de incidencia eliminado correctamente.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ──────────────────────────────────────────────
#  API: Editar tipo de incidencia (catálogo)
# ──────────────────────────────────────────────
@incidencias_bp.route('/api/tipos/<int:id>/editar', methods=['POST'])
@login_required
@permission_required('incidencias.crear')
def editar_tipo(id):
    """Actualiza un tipo del catálogo Incidencias."""
    try:
        nombre = request.form.get('nombre', '').strip()
        sigla = request.form.get('sigla', '').strip().upper()
        if not nombre or not sigla:
            return jsonify({'success': False, 'error': 'Nombre y sigla son requeridos.'})
        execute_query(
            "UPDATE Incidencias SET Incidencia = ?, SiglaIncidencia = ? WHERE IdIncidencia = ?",
            (nombre, sigla, id), commit=True
        )
        return jsonify({'success': True, 'message': 'Tipo de incidencia actualizado correctamente.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ──────────────────────────────────────────────
#  API: Buscar personal (autocomplete)
# ──────────────────────────────────────────────
@incidencias_bp.route('/api/personal')
@login_required
def api_personal():
    """Busca personal por nombre, apellido o cédula."""
    q = request.args.get('q', '', type=str).strip()
    if len(q) < 1:
        return jsonify([])
    s = f'%{q}%'
    rows = execute_query(
        "SELECT IdPersonal, Nombres, Apellidos, Cedula FROM Personal WHERE Nombres LIKE ? OR Apellidos LIKE ? OR Cedula LIKE ? ORDER BY Apellidos, Nombres",
        (s, s, s), fetchall=True
    ) or []
    return jsonify([{'id': r[0], 'nombres': r[1], 'apellidos': r[2], 'cedula': r[3]} for r in rows])
