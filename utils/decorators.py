from functools import wraps               # Preserva metadatos de la función decorada
from flask import session, redirect, url_for, flash, jsonify
from flask_login import login_required as flask_login_required, current_user


# ──────────────────────────────────────────────
#  Decorador: Requiere inicio de sesión
#  (Re-export de Flask-Login para mantener compatibilidad
#   con todos los 'from utils.decorators import login_required')
# ──────────────────────────────────────────────
login_required = flask_login_required


# ──────────────────────────────────────────────
#  Decorador: Requiere inicio de sesión (API JSON)
# ──────────────────────────────────────────────
def login_required_api(f):
    """
    Decorador para ENDPOINTS JSON (API). En lugar de redirigir
    al login cuando no hay sesión, responde con JSON 401.
    Así el JavaScript puede detectar el error sin romperse.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Sesión no válida. Inicia sesión nuevamente.'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ──────────────────────────────────────────────
#  Decorador: Requiere permiso específico (RBAC)
# ──────────────────────────────────────────────
def permission_required(slug):
    """
    Decorador que protege rutas según el permiso (slug).
    Ejemplo de uso: @permission_required('usuarios.ver')
    Usa current_user (Flask-Login) en lugar de session directamente.
    
    Parámetros:
        slug (str): Identificador del permiso requerido (ej: 'personal.crear')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Primero verifica que el usuario esté autenticado
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))

            # Verifica el permiso usando el método del modelo User
            if not current_user.tiene_permiso(slug):
                flash('No tienes permisos para acceder a este módulo.', 'danger')
                return redirect(url_for('index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator
