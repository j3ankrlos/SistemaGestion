from flask import Flask, render_template, redirect, url_for, session, request
import os
from config import Config
from routes.auth import auth_bp
from routes.usuarios import usuarios_bp
from routes.roles import roles_bp
from routes.permisos import permisos_bp
from routes.configuracion import config_bp
from routes.personal import personal_bp
from routes.incidencias import incidencias_bp
from routes.asistencias import asistencias_bp
from utils.decorators import login_required, login_required_api
from flask_login import LoginManager
from models.user import get_user_by_id, AnonymousUser

# ── Crear aplicación Flask ──
app = Flask(__name__)
app.config.from_object(Config)                    # Cargar config desde config.py
app.config['TEMPLATES_AUTO_RELOAD'] = True        # Recargar templates sin reiniciar

# ── Inicializar Flask-Login ──
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.anonymous_user = AnonymousUser
login_manager.login_message = None        # No mostrar mensaje en la pantalla de login


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login: reconstruye el usuario desde la BD en cada request."""
    return get_user_by_id(int(user_id))

import threading
import time


# ═══════════════════════════════════════════════
#  Heartbeat - Auto-apagado al cerrar navegador
# ═══════════════════════════════════════════════
# Si AUTO_SHUTDOWN=0 (variable de entorno), el servidor NO se apaga solo.
# Por defecto: se apaga a los 60min sin heartbeat, o inmediatamente al
# cerrar el navegador vía /shutdown (sendBeacon).
_AUTO_SHUTDOWN = os.environ.get('AUTO_SHUTDOWN', '1') == '1'

last_heartbeat = time.time()       # Último latido recibido
server_started_at = time.time()    # Momento en que arrancó el servidor

# Tiempo máximo sin heartbeat antes de apagar (3600s = 60 minutos)
# Al cerrar el navegador se envía una señal de apagado inmediato vía /shutdown,
# este valor es solo un fallback de seguridad por si no llega esa señal.
_HEARTBEAT_IDLE_MAX = int(os.environ.get('HEARTBEAT_IDLE_MAX', '3600'))
# Periodo de gracia inicial (30s para dar tiempo a cargar el login)
_HEARTBEAT_GRACE    = int(os.environ.get('HEARTBEAT_GRACE', '30'))

# Caché para evitar verificar la unidad de red en cada petición
_db_check_cache = {}
_db_check_cache_ttl = 30  # segundos


# ──────────────────────────────────────────────
#  Verificar existencia de ruta (con caché y timeout)
# ──────────────────────────────────────────────
def _db_path_exists(path, timeout=3):
    """
    Verifica si la ruta existe con timeout usando un hilo daemon.
    Incluye caché para no verificar en cada petición (útil en rutas de red).
    Los hilos daemon no bloquean el cierre del servidor.
    """
    now = time.time()

    # Usar caché si está vigente (TTL = 30 segundos)
    if path in _db_check_cache:
        cached_value, cached_time = _db_check_cache[path]
        if now - cached_time < _db_check_cache_ttl:
            return cached_value

    # Verificar con timeout usando hilo daemon (evita cuelgues en red)
    exists = [False]
    t = threading.Thread(target=lambda: exists.__setitem__(0, os.path.exists(path)))
    t.daemon = True
    t.start()
    t.join(timeout)

    result = exists[0] if not t.is_alive() else False

    if t.is_alive():
        print(f"Timeout al verificar ruta de red (3s): {path}")

    # Guardar en caché para la próxima vez
    _db_check_cache[path] = (result, now)
    return result


# ──────────────────────────────────────────────
#  Hilo heartbeat: apaga el servidor si el navegador se cierra
# ──────────────────────────────────────────────
def check_heartbeat():
    """Hilo daemon que monitorea el heartbeat del navegador.
    Si pasan más de _HEARTBEAT_IDLE_MAX segundos sin heartbeat,
    asume que el navegador se cerró y apaga el servidor."""
    while True:
        time.sleep(2)  # Revisar cada 2s (misma frecuencia que el heartbeat JS)
        if not _AUTO_SHUTDOWN:
            continue
        # Periodo de gracia al iniciar (evita apagado prematuro)
        if time.time() - server_started_at < _HEARTBEAT_GRACE:
            continue
        # Apagar tras inactividad (pestaña/ventana cerrada)
        if time.time() - last_heartbeat > _HEARTBEAT_IDLE_MAX:
            print("Navegador cerrado o sin actividad. Apagando servidor...")
            os._exit(0)

# Iniciar el hilo heartbeat al arrancar
threading.Thread(target=check_heartbeat, daemon=True).start()


# ──────────────────────────────────────────────
#  Endpoint: Heartbeat del navegador
# ──────────────────────────────────────────────
@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    """Recibe el latido del navegador (JS setInterval cada 2s).
    Responde 204 No Content para mantener la conexión ligera."""
    global last_heartbeat
    last_heartbeat = time.time()
    return '', 204


# ──────────────────────────────────────────────
#  Endpoint: Cerrar sesión al salir
# ──────────────────────────────────────────────
@app.route('/end-session', methods=['POST'])
def end_session():
    """Llamado vía navigator.sendBeacon() cuando se cierra el navegador.
    Usa logout_user() de Flask-Login para limpiar la sesión correctamente."""
    from flask_login import logout_user
    logout_user()
    return '', 200


# ──────────────────────────────────────────────
#  Endpoint: Apagar servidor al salir
# ──────────────────────────────────────────────
@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Llamado vía navigator.sendBeacon() cuando se cierra el navegador.
    Apaga el servidor inmediatamente para que no quede huérfano."""
    print("Recibida señal de cierre del navegador. Apagando servidor...")
    os._exit(0)
    return '', 200


# ═══════════════════════════════════════════════
#  Registro de Blueprints (rutas de cada módulo)
# ═══════════════════════════════════════════════
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(usuarios_bp, url_prefix='/usuarios')
app.register_blueprint(roles_bp, url_prefix='/usuarios/roles')
app.register_blueprint(permisos_bp, url_prefix='/usuarios/permisos')
app.register_blueprint(config_bp, url_prefix='/config')
app.register_blueprint(personal_bp, url_prefix='/personal')
app.register_blueprint(incidencias_bp, url_prefix='/incidencias')
app.register_blueprint(asistencias_bp, url_prefix='/asistencias')


# ──────────────────────────────────────────────
#  Filtro global: verificar BD antes de cada request
# ──────────────────────────────────────────────
@app.before_request
def check_db():
    """Verifica que la BD exista antes de cada petición.
    Si no existe, redirige a la pantalla de configuración inicial.
    Excluye rutas públicas (login, static, setup)."""
    if request.endpoint not in ('setup_db', 'static', 'auth.login', 'browse_db',
                                'config.database', 'config.index'):
        if not _db_path_exists(app.config['DB_PATH']):
            return redirect(url_for('setup_db'))

# ──────────────────────────────────────────────
#  Endpoint: Explorar archivo (selector nativo)
# ──────────────────────────────────────────────
@app.route('/browse_db')
def browse_db():
    """Abre el selector de archivos nativo de Windows para elegir la BD."""
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


# ──────────────────────────────────────────────
#  Setup inicial: elegir BD al primer inicio
# ──────────────────────────────────────────────
@app.route('/setup', methods=['GET', 'POST'])
def setup_db():
    """Pantalla de configuración inicial cuando no hay BD o no existe la ruta."""
    if request.method == 'POST':
        db_path = request.form.get('db_path')

        # Validar que el archivo exista y sea .accdb
        if db_path and os.path.exists(db_path) and db_path.endswith('.accdb'):
            from database.connection import get_connection
            old_path = Config.DB_PATH
            Config.DB_PATH = db_path
            app.config['DB_PATH'] = db_path
            try:
                conn = get_connection()
                conn.close()  # Si conecta, la BD es válida
            except Exception as e:
                Config.DB_PATH = old_path  # Restaurar ruta anterior
                app.config['DB_PATH'] = old_path
                return render_template('setup_db.html',
                                       error=f"Error al conectar a la base de datos: {e}")

            # Guardar la ruta en config.json para que persista
            import json
            config_file = os.path.join(os.path.dirname(__file__), 'config.json')
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump({"db_path": db_path}, f, indent=4)
            except Exception as e:
                print(f"Error saving config.json: {e}")

            app.config['DB_PATH'] = db_path
            return redirect(url_for('auth.login'))  # Ir al login
        else:
            return render_template('setup_db.html', error="Ruta inválida o archivo inexistente.")

    return render_template('setup_db.html')


# ──────────────────────────────────────────────
#  Endpoint: Avatar / foto del usuario
# ──────────────────────────────────────────────
@app.route('/avatar')
def user_avatar():
    """Sirve la foto del usuario. No requiere login (la usa el navbar antes de loguearse).
    Si no hay sesión activa, retorna 404."""
    from flask_login import current_user
    if not current_user.is_authenticated:
        return '', 404
    return _serve_avatar(current_user.id_personal)


def _serve_avatar(id_personal):
    """Lógica interna para servir la foto desde la BD."""
    if not id_personal:
        return '', 404
    from database.connection import get_connection
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Fotografia FROM Personal WHERE IdPersonal = ?", (id_personal,))
        row = cursor.fetchone()
        conn.close()

        if row and row[0] is not None:
            foto = row[0]

            # Si es bytes, servirlo directamente como imagen
            if isinstance(foto, bytes):
                # Detectar tipo de imagen por los primeros bytes (magic numbers)
                content_type = 'image/png'  # Por defecto
                if len(foto) > 3:
                    if foto[:3] == b'\xff\xd8\xff':
                        content_type = 'image/jpeg'
                    elif foto[:4] == b'\x89PNG':
                        content_type = 'image/png'
                    elif foto[:2] == b'BM':
                        content_type = 'image/bmp'
                return foto, 200, {'Content-Type': content_type}

            # Si es string, podría ser una ruta de archivo en disco
            elif isinstance(foto, str) and os.path.exists(foto):
                from flask import send_file
                return send_file(foto)
    except Exception as e:
        print(f"Error al servir avatar: {e}")

    return '', 404


# ──────────────────────────────────────────────
#  API: Estadísticas del Dashboard
# ──────────────────────────────────────────────
@app.route('/api/dashboard-stats')
@login_required_api
def dashboard_stats():
    """Devuelve estadísticas en JSON para el dashboard."""
    from database.connection import execute_query

    try:
        # Total personal
        total_personal = execute_query("SELECT COUNT(*) FROM Personal", fetchone=True)
        total_personal = total_personal[0] if total_personal else 0

        # Personal activo (basado en FK_IdEstatusActual)
        personal_activo = execute_query(
            "SELECT COUNT(*) FROM Personal WHERE FK_IdEstatusActual IN "
            "(SELECT IdEstatusA FROM EstatusActual WHERE EstatusA LIKE '%ACTIVO%')",
            fetchone=True
        )
        personal_activo = personal_activo[0] if personal_activo else 0

        # Personal inactivo
        personal_inactivo = total_personal - personal_activo

        # Total usuarios
        total_usuarios = execute_query("SELECT COUNT(*) FROM Usuarios", fetchone=True)
        total_usuarios = total_usuarios[0] if total_usuarios else 0

        # Usuarios activos (Fk_Status = 1)
        usuarios_activos = execute_query(
            "SELECT COUNT(*) FROM Usuarios WHERE Fk_Status = 1", fetchone=True
        )
        usuarios_activos = usuarios_activos[0] if usuarios_activos else 0

        # Usuarios inactivos
        usuarios_inactivos = total_usuarios - usuarios_activos

        # Total roles
        total_roles = execute_query("SELECT COUNT(*) FROM Roles", fetchone=True)
        total_roles = total_roles[0] if total_roles else 0

        # Personal sin usuario asignado
        personal_sin_usuario = execute_query(
            "SELECT COUNT(*) FROM Personal p LEFT JOIN Usuarios u "
            "ON p.IdPersonal = u.Fk_IdPersonal WHERE u.IdUsuario IS NULL",
            fetchone=True
        )
        personal_sin_usuario = personal_sin_usuario[0] if personal_sin_usuario else 0

        # Distribucion por estatus
        estatus_dist = execute_query(
            "SELECT IIF(ISNULL(ea.EstatusA), 'SIN ESTATUS', ea.EstatusA) AS estatus, COUNT(*) AS total "
            "FROM Personal p LEFT JOIN EstatusActual ea ON p.FK_IdEstatusActual = ea.IdEstatusA "
            "GROUP BY ea.EstatusA ORDER BY COUNT(*) DESC",
            fetchall=True
        )

        # Distribucion por rol
        roles_dist = execute_query(
            "SELECT IIF(ISNULL(r.Rol), 'SIN ROL', r.Rol) AS rol, COUNT(*) AS total "
            "FROM Usuarios u LEFT JOIN Roles r ON u.Fk_IdRol = r.IdRol "
            "GROUP BY r.Rol ORDER BY COUNT(*) DESC",
            fetchall=True
        )

        return {
            'success': True,
            'total_personal': total_personal,
            'personal_activo': personal_activo,
            'personal_inactivo': personal_inactivo,
            'total_usuarios': total_usuarios,
            'usuarios_activos': usuarios_activos,
            'usuarios_inactivos': usuarios_inactivos,
            'total_roles': total_roles,
            'personal_sin_usuario': personal_sin_usuario,
            'estatus_dist': [{'estatus': r[0], 'total': r[1]} for r in estatus_dist],
            'roles_dist': [{'rol': r[0], 'total': r[1]} for r in roles_dist],
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


# ──────────────────────────────────────────────
#  Página principal (Dashboard)
# ──────────────────────────────────────────────
@app.route('/')
@login_required
def index():
    """Página principal del sistema (dashboard/base)."""
    return render_template('index.html')


# ──────────────────────────────────────────────
#  Liberar puerto (forzar cierre de procesos)
# ──────────────────────────────────────────────
def liberar_puerto(port):
    """
    Fuerza el cierre de procesos Python que ocupen el puerto especificado (Windows).
    Útil cuando el servidor anterior no se cerró correctamente.
    """
    import subprocess
    try:
        # Buscar procesos escuchando en el puerto
        resultado = subprocess.run(
            f'netstat -ano | findstr :{port}',
            capture_output=True, text=True, shell=True, timeout=5
        )
        for linea in resultado.stdout.strip().split('\n'):
            if 'LISTENING' in linea:
                partes = linea.strip().split()
                if partes:
                    pid = partes[-1]  # El PID es el último campo
                    try:
                        # Matar el proceso forzosamente
                        subprocess.run(['taskkill', '/F', '/PID', pid],
                                     capture_output=True, timeout=3)
                        print(f"  ✓ Puerto {port} liberado (PID {pid})")
                    except Exception:
                        pass
    except Exception:
        pass


# ═══════════════════════════════════════════════
#  Punto de entrada principal
# ═══════════════════════════════════════════════
if __name__ == '__main__':
    from waitress import serve  # Servidor WSGI production-ready

    PORT = int(os.environ.get('PORCINO_PORT', '5000'))  # Puerto configurable

    # Intentar liberar el puerto antes de iniciar (por si quedó ocupado)
    liberar_puerto(PORT)

    print("============================================")
    print("|     SISTEMA DE GESTIÓN                     |")
    print("============================================")
    print(f"|  Servidor: http://localhost:{PORT:<13} |")
    print("|  Para APAGAR: Cierra esta ventana        |")
    print("|  o pulsa Ctrl+C                          |")
    print("============================================")
    print("")

    # Iniciar servidor con Waitress (bound a todas las interfaces)
    serve(app, host='0.0.0.0', port=PORT)
