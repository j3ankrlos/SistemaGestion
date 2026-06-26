from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
import os
import json
import threading
import datetime
from utils.decorators import login_required
from database.connection import get_connection
from config import Config

config_bp = Blueprint('config', __name__)


def config_required(f):
    """Permite acceso si tiene el permiso 'configuracion.ver' O es SuperAdmin (rol_id=1)."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        permisos = session.get('permisos', [])
        if 'configuracion.ver' not in permisos and session.get('rol_id') != 1:
            flash('No tienes permisos para acceder a Configuración.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


@config_bp.route('/')
@login_required
@config_required
def index():
    """Página principal de configuración - redirige a base de datos."""
    return redirect(url_for('config.database'))

@config_bp.route('/database', methods=['GET', 'POST'])
@login_required
@config_required
def database():
    """Configuración de la ruta de la base de datos."""
    db_path = current_app.config.get('DB_PATH', '')
    db_connected = False
    db_size = ''
    db_modified = ''

    # Verificar estado actual de la BD
    if db_path:
        # Verificar existencia con timeout (evita cuelgues en rutas de red)
        _exists = [False]
        def _check_exists():
            _exists[0] = os.path.exists(db_path)
        t = threading.Thread(target=_check_exists)
        t.daemon = True
        t.start()
        t.join(3)
        if t.is_alive() or not _exists[0]:
            db_path_exists = False
        else:
            db_path_exists = True
    else:
        db_path_exists = False
    
    if db_path_exists:
        db_connected = True
        try:
            size_bytes = [0]
            get_size = lambda: size_bytes.__setitem__(0, os.path.getsize(db_path))
            t = threading.Thread(target=get_size)
            t.daemon = True
            t.start()
            t.join(3)
            if not t.is_alive() and size_bytes[0] > 0:
                if size_bytes[0] < 1024:
                    db_size = f'{size_bytes[0]} bytes'
                elif size_bytes[0] < 1024 ** 2:
                    db_size = f'{size_bytes[0] / 1024:.1f} KB'
                else:
                    db_size = f'{size_bytes[0] / (1024 ** 2):.1f} MB'

            modified_ts = [0.0]
            get_mtime = lambda: modified_ts.__setitem__(0, os.path.getmtime(db_path))
            t2 = threading.Thread(target=get_mtime)
            t2.daemon = True
            t2.start()
            t2.join(3)
            if not t2.is_alive() and modified_ts[0] > 0:
                db_modified = datetime.datetime.fromtimestamp(modified_ts[0]).strftime('%d/%m/%Y %I:%M %p')
        except Exception:
            pass

    if request.method == 'POST':
        # Verificar permiso específico para editar configuración
        if 'configuracion.editar' not in session.get('permisos', []):
            flash('No tienes permiso para modificar la configuración.', 'danger')
            return redirect(url_for('config.database'))

        new_path = request.form.get('db_path', '').strip()

        if not new_path:
            flash('Debes especificar una ruta de base de datos.', 'danger')
            return render_template('configuracion/database.html',
                                   db_path=db_path, db_connected=db_connected,
                                   db_size=db_size, db_modified=db_modified)

        # Verificar existencia con timeout
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

        if not (new_path.endswith('.accdb') or new_path.endswith('.mdb')):
            flash('El archivo debe ser una base de datos Access (.accdb o .mdb).', 'danger')
            return render_template('configuracion/database.html',
                                   db_path=db_path, db_connected=db_connected,
                                   db_size=db_size, db_modified=db_modified)

        # Probar conexión con la nueva ruta
        old_cfg = Config.DB_PATH
        Config.DB_PATH = new_path
        current_app.config['DB_PATH'] = new_path
        try:
            conn = get_connection()
            conn.close()
        except Exception as e:
            Config.DB_PATH = old_cfg
            current_app.config['DB_PATH'] = old_cfg
            flash(f'Error al conectar con la nueva base de datos: {e}', 'danger')
            return render_template('configuracion/database.html',
                                   db_path=old_cfg, db_connected=db_connected,
                                   db_size=db_size, db_modified=db_modified)

        # Guardar en config.json
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.json')
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
