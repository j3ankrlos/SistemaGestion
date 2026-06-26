from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.connection import execute_query
from utils.decorators import login_required, permission_required

roles_bp = Blueprint('roles', __name__)

@roles_bp.route('/')
@login_required
@permission_required('roles.ver')
def index():
    query = "SELECT IdRol, Rol FROM Roles"
    roles = execute_query(query, fetchall=True)
    return render_template('roles/index.html', roles=roles)

@roles_bp.route('/crear', methods=['GET', 'POST'])
@login_required
@permission_required('roles.crear')
def crear():
    if request.method == 'POST':
        rol = request.form.get('rol')
        
        try:
            execute_query("INSERT INTO Roles (Rol) VALUES (?)", (rol,), commit=True)
            flash('Rol creado exitosamente.', 'success')
            return redirect(url_for('roles.index'))
        except Exception as e:
            flash(f'Error al crear rol: {str(e)}', 'danger')
            
    return render_template('roles/crear.html')

@roles_bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
@permission_required('roles.eliminar')
def eliminar(id):
    try:
        # Primero eliminar la relación en Permiso_Rol para mantener integridad
        execute_query("DELETE FROM Permiso_Rol WHERE Fk_IdRol = ?", (id,), commit=True)
        # Luego eliminar el rol
        execute_query("DELETE FROM Roles WHERE IdRol = ?", (id,), commit=True)
        flash('Rol eliminado.', 'success')
    except Exception as e:
        flash(f'Error al eliminar: {str(e)}', 'danger')
    return redirect(url_for('roles.index'))
