from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database.connection import execute_query
from utils.decorators import login_required, permission_required
import bcrypt

usuarios_bp = Blueprint('usuarios', __name__)

PER_PAGE = 10

@usuarios_bp.route('/')
@login_required
@permission_required('usuarios.ver')
def index():
    """Renderiza la página principal del módulo usuarios."""
    roles = execute_query("SELECT IdRol, Rol FROM Roles ORDER BY Rol", fetchall=True)
    return render_template('usuarios/index.html', roles=roles)

# ──────────────────────────────────────────────
#  API: Obtener datos paginados + búsqueda
# ──────────────────────────────────────────────
@usuarios_bp.route('/data')
@login_required
@permission_required('usuarios.ver')
def get_usuarios_data():
    """Devuelve JSON con la lista de usuarios paginada y filtrada."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    per_page = PER_PAGE

    base_query = """
        FROM (Usuarios u
        LEFT JOIN Roles r ON u.Fk_IdRol = r.IdRol)
        LEFT JOIN Personal p ON u.Fk_IdPersonal = p.IdPersonal
    """

    if search:
        where = " WHERE u.Usuario LIKE ? OR u.NombreCorto LIKE ? OR r.Rol LIKE ?"
        params = (f'%{search}%', f'%{search}%', f'%{search}%')
    else:
        where = ""
        params = ()

    # Total de registros
    count_row = execute_query("SELECT COUNT(*)" + base_query + where, params, fetchone=True)
    total = count_row[0] if count_row else 0
    total_pages = max(1, (total + per_page - 1) // per_page)

    # Obtener página actual
    select_query = """
        SELECT u.IdUsuario, u.Usuario, u.NombreCorto,
               r.Rol,
               u.Fk_Status,
               p.Nombres, p.Apellidos, u.Fk_IdPersonal
    """ + base_query + where + " ORDER BY u.IdUsuario"

    all_rows = execute_query(select_query, params, fetchall=True) or []

    # Paginar en Python
    start = (page - 1) * per_page
    end = start + per_page
    page_rows = all_rows[start:end]

    usuarios = []
    for row in page_rows:
        usuarios.append({
            'id': row[0],
            'usuario': row[1],
            'nombre_corto': row[2],
            'rol': row[3] or 'Sin Rol',
            'status': row[4] if row[4] is not None else 1,
            'nombres_personal': row[5] or '',
            'apellidos_personal': row[6] or '',
            'id_personal': row[7],
        })

    return jsonify({
        'usuarios': usuarios,
        'total': total,
        'page': page,
        'total_pages': total_pages,
        'per_page': per_page,
    })

# ──────────────────────────────────────────────
#  API: Buscar personas en tabla Personal
# ──────────────────────────────────────────────
@usuarios_bp.route('/buscar_personal')
@login_required
@permission_required('usuarios.crear')
def buscar_personal():
    """Busca personas en la tabla Personal para auto-completar."""
    q = request.args.get('q', '').strip()
    if len(q) < 1:
        return jsonify([])

    rows = execute_query(
        "SELECT IdPersonal, Nombres, Apellidos FROM Personal WHERE Nombres LIKE ? OR Apellidos LIKE ? ORDER BY Nombres, Apellidos",
        (f'%{q}%', f'%{q}%'),
        fetchall=True
    ) or []

    results = [{'id': r[0], 'nombres': r[1], 'apellidos': r[2]} for r in rows]
    return jsonify(results)

# ──────────────────────────────────────────────
#  API: Sugerir nombres de usuario
# ──────────────────────────────────────────────
@usuarios_bp.route('/sugerir_usuario')
@login_required
@permission_required('usuarios.crear')
def sugerir_usuario():
    """Sugiere 3 nombres de usuario basados en nombre y apellido, o nombre corto."""
    nombres = request.args.get('nombres', '').strip()
    apellidos = request.args.get('apellidos', '').strip()
    nombre_corto = request.args.get('nombre_corto', '').strip()

    # Si no hay nombres/apellidos, intentar con nombre_corto
    if not nombres and not apellidos and nombre_corto:
        partes = nombre_corto.strip().split()
        if len(partes) >= 2:
            nombres = partes[0]
            apellidos = partes[-1]
        else:
            nombres = nombre_corto
            apellidos = 'user'

    if not nombres or not apellidos:
        return jsonify({'base': '', 'sugerencias': []})

    primer_nombre = nombres.split()[0]
    primer_apellido = apellidos.split()[0]
    base = primer_nombre[0].upper() + primer_apellido.lower()

    # Obtener usuarios existentes que empiecen con la base
    existing = execute_query(
        "SELECT Usuario FROM Usuarios WHERE Usuario LIKE ?",
        (f'{base}%',),
        fetchall=True
    ) or []
    existing_set = set(r[0].lower() for r in existing)

    sugerencias = []
    if base.lower() not in existing_set:
        sugerencias.append(base)
        # Si el base está libre, sugerimos base, base1, base2
        i = 1
        while len(sugerencias) < 3:
            sug = f"{base}{i}"
            if sug.lower() not in existing_set:
                sugerencias.append(sug)
            i += 1
    else:
        i = 1
        while len(sugerencias) < 3:
            sug = f"{base}{i}"
            if sug.lower() not in existing_set:
                sugerencias.append(sug)
            i += 1

    return jsonify({'base': base, 'sugerencias': sugerencias})

# ──────────────────────────────────────────────
#  API: Verificar disponibilidad de usuario
# ──────────────────────────────────────────────
@usuarios_bp.route('/verificar_usuario')
@login_required
@permission_required('usuarios.crear')
def verificar_usuario():
    """Verifica si un nombre de usuario ya está en uso."""
    usuario = request.args.get('usuario', '').strip()
    if not usuario:
        return jsonify({'disponible': False})

    row = execute_query(
        "SELECT COUNT(*) FROM Usuarios WHERE Usuario = ?",
        (usuario,),
        fetchone=True
    )
    disponible = (row and row[0] == 0)
    return jsonify({'disponible': disponible})

# ──────────────────────────────────────────────
#  API: Crear usuario (desde modal)
# ──────────────────────────────────────────────
@usuarios_bp.route('/crear', methods=['POST'])
@login_required
@permission_required('usuarios.crear')
def crear():
    """Crea un nuevo usuario vía AJAX desde el modal."""
    data = request.get_json(force=True) or {}
    usuario = data.get('usuario', '').strip()
    clave = data.get('clave', '')
    nombre_corto = data.get('nombre_corto', '').strip()
    id_rol = data.get('id_rol')
    id_personal = data.get('id_personal')  # Puede ser None

    # Validaciones
    if not usuario:
        return jsonify({'success': False, 'error': 'El nombre de usuario es obligatorio.'})
    if not clave or len(clave) < 4:
        return jsonify({'success': False, 'error': 'La contraseña debe tener al menos 4 caracteres.'})
    if not nombre_corto:
        return jsonify({'success': False, 'error': 'El nombre corto es obligatorio.'})
    if not id_rol:
        return jsonify({'success': False, 'error': 'Debe seleccionar un rol.'})

    # Verificar duplicado
    existing = execute_query(
        "SELECT COUNT(*) FROM Usuarios WHERE Usuario = ?",
        (usuario,), fetchone=True
    )
    if existing and existing[0] > 0:
        return jsonify({'success': False, 'error': f'El usuario "{usuario}" ya existe.'})

    hashed_pw = bcrypt.hashpw(clave.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        if id_personal and id_personal > 0:
            execute_query(
                "INSERT INTO Usuarios (Usuario, Clave, NombreCorto, Fk_IdRol, Fk_IdPersonal, Fk_Sitio, Fk_Status) VALUES (?, ?, ?, ?, ?, 1, 1)",
                (usuario, hashed_pw, nombre_corto, id_rol, id_personal),
                commit=True
            )
        else:
            execute_query(
                "INSERT INTO Usuarios (Usuario, Clave, NombreCorto, Fk_IdRol, Fk_Sitio, Fk_Status) VALUES (?, ?, ?, ?, 1, 1)",
                (usuario, hashed_pw, nombre_corto, id_rol),
                commit=True
            )
        return jsonify({'success': True, 'message': 'Usuario creado exitosamente.'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error al crear usuario: {str(e)}'})

# ──────────────────────────────────────────────
#  API: Obtener datos de un usuario (para editar)
# ──────────────────────────────────────────────
@usuarios_bp.route('/<int:id>/editar', methods=['GET'])
@login_required
@permission_required('usuarios.editar')
def obtener_usuario(id):
    """Devuelve JSON con los datos del usuario para editar."""
    row = execute_query(
        """SELECT u.IdUsuario, u.Usuario, u.NombreCorto, u.Fk_IdRol,
                  u.Fk_IdPersonal, u.Fk_Status,
                  p.Nombres, p.Apellidos
           FROM Usuarios u
           LEFT JOIN Personal p ON u.Fk_IdPersonal = p.IdPersonal
           WHERE u.IdUsuario = ?""",
        (id,), fetchone=True
    )
    if not row:
        return jsonify({'success': False, 'error': 'Usuario no encontrado.'})

    return jsonify({
        'success': True,
        'usuario': {
            'id': row[0],
            'usuario': row[1],
            'nombre_corto': row[2],
            'id_rol': row[3],
            'id_personal': row[4],
            'status': row[5],
            'nombres_personal': row[6] or '',
            'apellidos_personal': row[7] or '',
        }
    })

# ──────────────────────────────────────────────
#  API: Actualizar usuario
# ──────────────────────────────────────────────
@usuarios_bp.route('/<int:id>/editar', methods=['POST'])
@login_required
@permission_required('usuarios.editar')
def actualizar_usuario(id):
    """Actualiza un usuario vía AJAX."""
    data = request.get_json(force=True) or {}
    nombre_corto = data.get('nombre_corto', '').strip()
    id_rol = data.get('id_rol')
    id_personal = data.get('id_personal')  # None = sin personal
    nueva_clave = data.get('clave', '').strip()

    if not nombre_corto:
        return jsonify({'success': False, 'error': 'El nombre corto es obligatorio.'})
    if not id_rol:
        return jsonify({'success': False, 'error': 'Debe seleccionar un rol.'})

    try:
        if nueva_clave:
            hashed_pw = bcrypt.hashpw(nueva_clave.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            execute_query(
                "UPDATE Usuarios SET NombreCorto=?, Fk_IdRol=?, Fk_IdPersonal=?, Clave=? WHERE IdUsuario=?",
                (nombre_corto, id_rol, id_personal if id_personal and id_personal > 0 else None, hashed_pw, id),
                commit=True
            )
        else:
            execute_query(
                "UPDATE Usuarios SET NombreCorto=?, Fk_IdRol=?, Fk_IdPersonal=? WHERE IdUsuario=?",
                (nombre_corto, id_rol, id_personal if id_personal and id_personal > 0 else None, id),
                commit=True
            )
        return jsonify({'success': True, 'message': 'Usuario actualizado exitosamente.'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error al actualizar: {str(e)}'})

# ──────────────────────────────────────────────
#  API: Desactivar / Activar usuario
# ──────────────────────────────────────────────
@usuarios_bp.route('/<int:id>/toggle-status', methods=['POST'])
@login_required
@permission_required('usuarios.desactivar')
def toggle_status(id):
    """Cambia el estado del usuario (activo/inactivo)."""
    data = request.get_json(force=True) or {}
    nuevo_status = data.get('status', 2)
    # Mapear: 0 (frontend) -> 2 (Inactivo en tabla Estatus)
    if nuevo_status == 0 or nuevo_status is None:
        nuevo_status = 2

    try:
        execute_query(
            "UPDATE Usuarios SET Fk_Status = ? WHERE IdUsuario = ?",
            (nuevo_status, id), commit=True
        )
        msg = 'Usuario activado.' if nuevo_status == 1 else 'Usuario desactivado.'
        return jsonify({'success': True, 'message': msg})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error al cambiar estado: {str(e)}'})
