from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.connection import execute_query
from utils.decorators import login_required, permission_required

permisos_bp = Blueprint('permisos', __name__)

@permisos_bp.route('/')
@login_required
@permission_required('permisos.ver')
def index():
    # Obtener todos los roles
    roles = execute_query("SELECT IdRol, Rol FROM Roles", fetchall=True)
    
    # Obtener todos los permisos agrupados por Modulo
    permisos_raw = execute_query("SELECT IdPermiso, Modulo, Accion, Slug FROM Permisos ORDER BY Modulo, Accion", fetchall=True)
    
    # Obtener la matriz de asignación actual
    asignaciones_raw = execute_query("SELECT Fk_IdRol, Fk_IdPermiso FROM Permiso_Rol", fetchall=True)
    asignaciones = {}
    if asignaciones_raw:
        for r_id, p_id in asignaciones_raw:
            if r_id not in asignaciones:
                asignaciones[r_id] = []
            asignaciones[r_id].append(p_id)
            
    # Estructurar permisos por módulo
    permisos_por_modulo = {}
    for p in permisos_raw:
        mod = p[1]
        if mod not in permisos_por_modulo:
            permisos_por_modulo[mod] = []
        permisos_por_modulo[mod].append(p)
        
    return render_template('permisos/index.html', roles=roles, permisos_por_modulo=permisos_por_modulo, asignaciones=asignaciones)

@permisos_bp.route('/guardar', methods=['POST'])
@login_required
@permission_required('permisos.editar')
def guardar():
    try:
        # La tabla se envía como un formulario con checkboxes.
        # Checkbox name format: permiso_{id_rol}_{id_permiso}
        
        # Primero obtenemos todos los roles y permisos para borrar la matriz actual
        # y luego insertar solo los marcados (para simplificar la lógica)
        execute_query("DELETE FROM Permiso_Rol", commit=True)
        
        # Recorremos el request.form buscando los checkboxes marcados
        insert_queries = []
        for key in request.form.keys():
            if key.startswith('permiso_'):
                parts = key.split('_')
                if len(parts) == 3:
                    id_rol = int(parts[1])
                    id_permiso = int(parts[2])
                    insert_queries.append((id_rol, id_permiso))
                    
        # Insertar nuevas relaciones
        from database.connection import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        for rol, perm in insert_queries:
            cursor.execute("INSERT INTO Permiso_Rol (Fk_IdRol, Fk_IdPermiso) VALUES (?, ?)", (rol, perm))
        conn.commit()
        conn.close()
        
        flash('Matriz de permisos actualizada correctamente.', 'success')
    except Exception as e:
        flash(f'Error al guardar permisos: {str(e)}', 'danger')
        
    return redirect(url_for('permisos.index'))
