from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
import os
import json
import threading
import datetime
from utils.decorators import login_required
from database.connection import get_connection
from config import Config

config_bp = Blueprint('config', __name__)


# ──────────────────────────────────────────────
#  Decorador: Acceso a configuración
# ──────────────────────────────────────────────
def config_required(f):
    """
    Decorador que permite acceso si el usuario tiene el permiso
    'configuracion.ver' O es SuperAdmin (rol_id=1).
    """
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        permisos = session.get('permisos', [])
        if 'configuracion.ver' not in permisos and session.get('rol_id') != 1:
            flash('No tienes permisos para acceder a Configuración.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


# ──────────────────────────────────────────────
#  Página principal de configuración
# ──────────────────────────────────────────────
@config_bp.route('/')
@login_required
@config_required
def index():
    """Redirige a la configuración de base de datos (única opción por ahora)."""
    return redirect(url_for('config.database'))


# ──────────────────────────────────────────────
#  Configuración de ruta de base de datos
# ──────────────────────────────────────────────
@config_bp.route('/database', methods=['GET', 'POST'])
@login_required
@config_required
def database():
    """
    Página para cambiar la ruta de la base de datos Access en tiempo real.
    - GET: Muestra información de la BD actual (tamaño, fecha modificación, conectividad).
    - POST: Valida la nueva ruta, prueba conexión y guarda en config.json.
    """
    db_path = current_app.config.get('DB_PATH', '')
    db_connected = False
    db_size = ''
    db_modified = ''

    # ── Verificar estado actual de la BD ──
    if db_path:
        # Verificar existencia con timeout (evita cuelgues en rutas de red)
        _exists = [False]
        def _check_exists():
            _exists[0] = os.path.exists(db_path)
        t = threading.Thread(target=_check_exists)
        t.daemon = True
        t.start()
        t.join(3)  # Espera máximo 3 segundos (si es ruta de red)
        if t.is_alive() or not _exists[0]:
            db_path_exists = False
        else:
            db_path_exists = True
    else:
        db_path_exists = False

    # Si la BD existe, obtener tamaño y fecha de modificación
    if db_path_exists:
        db_connected = True
        try:
            # Obtener tamaño con timeout (para evitar cuelgues en red)
            size_bytes = [0]
            get_size = lambda: size_bytes.__setitem__(0, os.path.getsize(db_path))
            t = threading.Thread(target=get_size)
            t.daemon = True
            t.start()
            t.join(3)
            if not t.is_alive() and size_bytes[0] > 0:
                # Formatear tamaño legible
                if size_bytes[0] < 1024:
                    db_size = f'{size_bytes[0]} bytes'
                elif size_bytes[0] < 1024 ** 2:
                    db_size = f'{size_bytes[0] / 1024:.1f} KB'
                else:
                    db_size = f'{size_bytes[0] / (1024 ** 2):.1f} MB'

            # Obtener fecha de modificación con timeout
            modified_ts = [0.0]
            get_mtime = lambda: modified_ts.__setitem__(0, os.path.getmtime(db_path))
            t2 = threading.Thread(target=get_mtime)
            t2.daemon = True
            t2.start()
            t2.join(3)
            if not t2.is_alive() and modified_ts[0] > 0:
                db_modified = datetime.datetime.fromtimestamp(
                    modified_ts[0]
                ).strftime('%d/%m/%Y %I:%M %p')
        except Exception:
            pass  # Si falla, mostrar valores vacíos

    # ── Procesar cambio de ruta (POST) ──
    if request.method == 'POST':
        # Verificar permiso específico para editar configuración
        if 'configuracion.editar' not in session.get('permisos', []):
            flash('No tienes permiso para modificar la configuración.', 'danger')
            return redirect(url_for('config.database'))

        new_path = request.form.get('db_path', '').strip()

        # Validar que no esté vacío
        if not new_path:
            flash('Debes especificar una ruta de base de datos.', 'danger')
            return render_template('configuracion/database.html',
                                   db_path=db_path, db_connected=db_connected,
                                   db_size=db_size, db_modified=db_modified)

        # Verificar que el archivo existe (con timeout)
        _post_exists = [False]
        def _check_post_path():
            _post_exists[0] = os.path.exists(new_path)
        t = threading.Thread(target=_check_post_path)
        t.daemon = True
        t.start()
        t.join(5)
        if t.is_alive() or not _post_exists[0]:
            flash(f'El archivo no existe o no es accesible: {new_path}', 'danger')
            return render_template('configuracion/database.html',
                                   db_path=db_path, db_connected=db_connected,
                                   db_size=db_size, db_modified=db_modified)

        # Validar extensión
        if not (new_path.endswith('.accdb') or new_path.endswith('.mdb')):
            flash('El archivo debe ser una base de datos Access (.accdb o .mdb).', 'danger')
            return render_template('configuracion/database.html',
                                   db_path=db_path, db_connected=db_connected,
                                   db_size=db_size, db_modified=db_modified)

        # Probar conexión con la nueva ruta antes de guardar
        old_cfg = Config.DB_PATH
        Config.DB_PATH = new_path
        current_app.config['DB_PATH'] = new_path
        try:
            conn = get_connection()
            conn.close()  # Si conecta, la ruta es válida
        except Exception as e:
            # Si falla, restaurar ruta anterior
            Config.DB_PATH = old_cfg
            current_app.config['DB_PATH'] = old_cfg
            flash(f'Error al conectar con la nueva base de datos: {e}', 'danger')
            return render_template('configuracion/database.html',
                                   db_path=old_cfg, db_connected=db_connected,
                                   db_size=db_size, db_modified=db_modified)

        # Guardar la nueva ruta en config.json para que persista
        config_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'config.json'
        )
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump({"db_path": new_path}, f, indent=4)
            flash('Ruta de base de datos actualizada correctamente.', 'success')
        except Exception as e:
            flash(f'Error al guardar la configuración: {e}', 'danger')

        return redirect(url_for('config.database'))

    return render_template('configuracion/database.html',
                           db_path=db_path, db_connected=db_connected,
                           db_size=db_size, db_modified=db_modified)


# ──────────────────────────────────────────────
#  Administrar tipos de incidencia
# ──────────────────────────────────────────────
@config_bp.route('/incidencias/tipos')
@login_required
@config_required
def admin_tipos_incidencias():
    """
    Página para administrar el catálogo de tipos de incidencia.
    (reposos, vacaciones, permisos, etc.)
    """
    return render_template('configuracion/incidencias_tipos.html')
