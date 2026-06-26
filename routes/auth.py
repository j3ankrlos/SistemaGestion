from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.connection import execute_query
import bcrypt

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        clave = request.form.get('clave')
        
        user_data = execute_query(
            """SELECT u.IdUsuario, u.Usuario, u.Clave, u.NombreCorto, u.Fk_IdRol,
                      u.Fk_IdPersonal, r.Rol, p.Nombres, p.Apellidos
               FROM (Usuarios u
               LEFT JOIN Roles r ON u.Fk_IdRol = r.IdRol)
               LEFT JOIN Personal p ON u.Fk_IdPersonal = p.IdPersonal
               WHERE u.Usuario = ?""",
            (usuario,), fetchone=True
        )
        
        if user_data:
            id_usuario, db_usuario, db_clave, nombre, id_rol, id_personal, rol_nombre, nombres, apellidos = user_data
            
            # Verificar contraseña hasheada
            if bcrypt.checkpw(clave.encode('utf-8'), db_clave.encode('utf-8')):
                session['usuario_id'] = id_usuario
                session['usuario'] = db_usuario
                session['nombre'] = nombre
                session['rol_id'] = id_rol
                session['rol_nombre'] = rol_nombre or ''
                session['id_personal'] = id_personal or 0
                
                # Calcular iniciales
                iniciales = ''
                if nombres and apellidos:
                    iniciales = (nombres[0] + apellidos[0]).upper()
                elif nombre:
                    partes = nombre.split()
                    if len(partes) >= 2:
                        iniciales = (partes[0][0] + partes[1][0]).upper()
                    else:
                        iniciales = nombre[0].upper()
                session['iniciales'] = iniciales
                
                # Cargar permisos en memoria (RBAC)
                permisos_query = """
                SELECT p.Slug 
                FROM Permisos p
                INNER JOIN Permiso_Rol pr ON p.IdPermiso = pr.Fk_IdPermiso
                WHERE pr.Fk_IdRol = ?
                """
                permisos_raw = execute_query(permisos_query, (id_rol,), fetchall=True)
                # Extraer slugs
                slugs = [row[0] for row in permisos_raw] if permisos_raw else []
                session['permisos'] = slugs
                
                return redirect(url_for('index'))
            else:
                flash('Credenciales incorrectas.', 'danger')
        else:
            flash('El usuario no existe.', 'danger')
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
