from flask import Flask, render_template, redirect, url_for, session, request
import os
from config import Config
from routes.auth import auth_bp
from routes.usuarios import usuarios_bp
from routes.roles import roles_bp
from routes.permisos import permisos_bp
from routes.configuracion import config_bp
from routes.personal import personal_bp
from utils.decorators import login_required

app = Flask(__name__)
app.config.from_object(Config)
app.config['TEMPLATES_AUTO_RELOAD'] = True

import threading
import time

# ─── Heartbeat: apaga el servidor al cerrar el navegador ───
# Si AUTO_SHUTDOWN=0 (entorno), el servidor NO se apaga solo.
# Por defecto: se apaga a los 10s sin heartbeat (pestaña/ventana cerrada)
_AUTO_SHUTDOWN = os.environ.get('AUTO_SHUTDOWN', '1') == '1'

last_heartbeat = time.time()
server_started_at = time.time()

# Tiempo máximo sin heartbeat antes de apagar (10 segundos = ~5 beats perdidos)
_HEARTBEAT_IDLE_MAX = int(os.environ.get('HEARTBEAT_IDLE_MAX', '10'))
# Periodo de gracia inicial (30s para dar tiempo a cargar el login)
_HEARTBEAT_GRACE    = int(os.environ.get('HEARTBEAT_GRACE', '30'))

# Cache para evitar verificar la unidad de red en cada petición
_db_check_cache = {}
_db_check_cache_ttl = 30  # segundos

def _db_path_exists(path, timeout=3):
    """
    Verifica si la ruta existe con timeout usando un hilo daemon.
    Incluye caché para no bloquear en cada petición.
    Los hilos daemon no bloquean el cierre del executor.
    """
    now = time.time()
    
    # Usar caché si está vigente
    if path in _db_check_cache:
        cached_value, cached_time = _db_check_cache[path]
        if now - cached_time < _db_check_cache_ttl:
            return cached_value
    
    # Verificar con timeout usando hilo daemon
    exists = [False]
    t = threading.Thread(target=lambda: exists.__setitem__(0, os.path.exists(path)))
    t.daemon = True
    t.start()
    t.join(timeout)
    
    result = exists[0] if not t.is_alive() else False
    
    if t.is_alive():
        print(f"Timeout al verificar ruta de red (3s): {path}")
    
    # Guardar en caché
    _db_check_cache[path] = (result, now)
    return result

def check_heartbeat():
    while True:
        time.sleep(2)  # Revisar cada 2s (misma frecuencia que el heartbeat JS)
        if not _AUTO_SHUTDOWN:
            continue
        # Periodo de gracia al iniciar
        if time.time() - server_started_at < _HEARTBEAT_GRACE:
            continue
        # Apagar tras inactividad (pestaña/ventana cerrada)
        if time.time() - last_heartbeat > _HEARTBEAT_IDLE_MAX:
            print("Navegador cerrado o sin actividad. Apagando servidor...")
            os._exit(0)

threading.Thread(target=check_heartbeat, daemon=True).start()

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    global last_heartbeat
    last_heartbeat = time.time()
    return '', 204

@app.route('/end-session', methods=['POST'])
def end_session():
    """Llamado vía navigator.sendBeacon() cuando se cierra el navegador.
    Limpia la sesión del usuario y elimina la cookie."""
    session.clear()
    resp = '', 200
    return resp

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Llamado vía navigator.sendBeacon() cuando se cierra el navegador.
    Apaga el servidor inmediatamente."""
    print("Recibida señal de cierre del navegador. Apagando servidor...")
    os._exit(0)
    return '', 200

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(usuarios_bp, url_prefix='/usuarios')
app.register_blueprint(roles_bp, url_prefix='/usuarios/roles')
app.register_blueprint(permisos_bp, url_prefix='/usuarios/permisos')
app.register_blueprint(config_bp, url_prefix='/config')
app.register_blueprint(personal_bp, url_prefix='/personal')

@app.before_request
def check_db():
    if request.endpoint not in ('setup_db', 'static', 'auth.login', 'browse_db', 'config.database', 'config.index'):
        if not _db_path_exists(app.config['DB_PATH']):
            return redirect(url_for('setup_db'))

@app.route('/browse_db')
def browse_db():
    import subprocess
    import sys
    try:
        helper = os.path.join(os.path.dirname(__file__), 'utils', 'seleccionar_archivo.py')
        resultado = subprocess.run(
            [sys.executable, helper],
            capture_output=True,
            text=True,
            timeout=120
        )
        file_path = resultado.stdout.strip()
        # El script imprime la ruta o queda vacío si canceló
        return {'path': file_path}
    except subprocess.TimeoutExpired:
        return {'error': 'El selector de archivos tardó demasiado. Intenta de nuevo.'}, 500
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/setup', methods=['GET', 'POST'])
def setup_db():
    if request.method == 'POST':
        db_path = request.form.get('db_path')
        if db_path and os.path.exists(db_path) and db_path.endswith('.accdb'):
            from database.connection import get_connection
            old_path = Config.DB_PATH
            Config.DB_PATH = db_path
            try:
                conn = get_connection()
                conn.close()
            except Exception as e:
                Config.DB_PATH = old_path
                return render_template('setup_db.html', error=f"Error al conectar a la base de datos: {e}")

            import json
            config_file = os.path.join(os.path.dirname(__file__), 'config.json')
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump({"db_path": db_path}, f, indent=4)
            except Exception as e:
                print(f"Error saving config.json: {e}")

            app.config['DB_PATH'] = db_path
            return redirect(url_for('auth.login'))
        else:
            return render_template('setup_db.html', error="Ruta inválida o archivo inexistente.")
    return render_template('setup_db.html')

@app.route('/avatar')
@login_required
def user_avatar():
    """Sirve la foto del usuario desde la tabla Personal."""
    from database.connection import get_connection
    id_personal = session.get('id_personal', 0)
    if not id_personal:
        return '', 404
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Fotografia FROM Personal WHERE IdPersonal = ?", (id_personal,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] is not None:
            foto = row[0]
            # Si es bytes, servirlo como imagen
            if isinstance(foto, bytes):
                # Intentar detectar tipo de imagen por los primeros bytes
                content_type = 'image/png'
                if len(foto) > 3:
                    if foto[:3] == b'\xff\xd8\xff':
                        content_type = 'image/jpeg'
                    elif foto[:4] == b'\x89PNG':
                        content_type = 'image/png'
                    elif foto[:2] == b'BM':
                        content_type = 'image/bmp'
                return foto, 200, {'Content-Type': content_type}
            # Si es string, podría ser una ruta de archivo
            elif isinstance(foto, str) and os.path.exists(foto):
                from flask import send_file
                return send_file(foto)
    except Exception as e:
        print(f"Error al servir avatar: {e}")
    
    return '', 404

@app.route('/')
@login_required
def index():
    return render_template('base.html')

def liberar_puerto(port):
    """Fuerza el cierre de procesos Python que ocupen el puerto especificado (Windows)."""
    import subprocess
    try:
        resultado = subprocess.run(
            f'netstat -ano | findstr :{port}',
            capture_output=True, text=True, shell=True, timeout=5
        )
        for linea in resultado.stdout.strip().split('\n'):
            if 'LISTENING' in linea:
                partes = linea.strip().split()
                if partes:
                    pid = partes[-1]
                    try:
                        subprocess.run(['taskkill', '/F', '/PID', pid],
                                     capture_output=True, timeout=3)
                        print(f"  ✓ Puerto {port} liberado (PID {pid})")
                    except Exception:
                        pass
    except Exception:
        pass

if __name__ == '__main__':
    from waitress import serve
    
    PORT = int(os.environ.get('PORCINO_PORT', '5000'))
    
    # Intentar liberar el puerto antes de iniciar
    liberar_puerto(PORT)
    
    print("╔══════════════════════════════════════════╗")
    print("║     SISTEMA PORCINO - Gestión           ║")
    print("╠══════════════════════════════════════════╣")
    print(f"║  Servidor: http://localhost:{PORT}         ║")
    print("║  Para APAGAR: Cierra esta ventana       ║")
    print("║  o pulsa Ctrl+C                         ║")
    print("╚══════════════════════════════════════════╝")
    print("")
    serve(app, host='0.0.0.0', port=PORT)
