from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.connection import execute_query
from utils.decorators import login_required, permission_required

permisos_bp = Blueprint('permisos', __name__)


# ──────────────────────────────────────────────
#  Matriz de permisos (Roles × Permisos)
# ──────────────────────────────────────────────
@permisos_bp.route('/')
@login_required
@permission_required('permisos.ver')
def index():
    """
    Renderiza la matriz de asignación de permisos.
    Muestra una tabla con todos los roles vs todos los permisos,
    con checkboxes para marcar/desmarcar asignaciones.
    """
    # Obtener todos los roles del sistema
    roles = execute_query("SELECT IdRol, Rol FROM Roles", fetchall=True)

    # Obtener todos los permisos ordenados por módulo y acción
    permisos_raw = execute_query(
        "SELECT IdPermiso, Modulo, Accion, Slug FROM Permisos ORDER BY Modulo, Accion",
        fetchall=True
    )

    # Obtener la matriz actual de asignaciones (qué permisos tiene cada rol)
    asignaciones_raw = execute_query(
        "SELECT Fk_IdRol, Fk_IdPermiso FROM Permiso_Rol", fetchall=True
    )
    # Estructurar como dict: {id_rol: [id_permiso1, id_permiso2, ...]}
    asignaciones = {}
    if asignaciones_raw:
        for r_id, p_id in asignaciones_raw:
            if r_id not in asignaciones:
                asignaciones[r_id] = []
            asignaciones[r_id].append(p_id)

    # Agrupar permisos por módulo para mostrarlos organizados
    permisos_por_modulo = {}
    for p in permisos_raw:
        mod = p[1]  # Índice 1 = Modulo
        if mod not in permisos_por_modulo:
            permisos_por_modulo[mod] = []
        permisos_por_modulo[mod].append(p)

    return render_template(
        'permisos/index.html',
        roles=roles,
        permisos_por_modulo=permisos_por_modulo,
        asignaciones=asignaciones
    )


# ──────────────────────────────────────────────
#  Guardar matriz de permisos
# ──────────────────────────────────────────────
@permisos_bp.route('/guardar', methods=['POST'])
@login_required
@permission_required('permisos.editar')
def guardar():
    """
    Guarda la matriz de permisos: borra todas las asignaciones actuales
    y re-inserta solo los checkboxes marcados en el formulario.
    
    Los checkboxes se envían con el formato:
      permiso_{id_rol}_{id_permiso}
    """
    try:
        # Paso 1: Limpiar toda la matriz actual (borra todas las asignaciones)
        execute_query("DELETE FROM Permiso_Rol", commit=True)

        # Paso 2: Recorrer los checkboxes marcados en el formulario
        insert_queries = []
        for key in request.form.keys():
            if key.startswith('permiso_'):
                parts = key.split('_')
                if len(parts) == 3:
                    id_rol = int(parts[1])
                    id_permiso = int(parts[2])
                    insert_queries.append((id_rol, id_permiso))

        # Paso 3: Insertar las nuevas asignaciones una por una
        from database.connection import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        for rol, perm in insert_queries:
            cursor.execute(
                "INSERT INTO Permiso_Rol (Fk_IdRol, Fk_IdPermiso) VALUES (?, ?)",
                (rol, perm)
            )
        conn.commit()
        conn.close()

        flash('Matriz de permisos actualizada correctamente.', 'success')
    except Exception as e:
        flash(f'Error al guardar permisos: {str(e)}', 'danger')

    return redirect(url_for('permisos.index'))
