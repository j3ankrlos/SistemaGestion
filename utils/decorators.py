from functools import wraps          # Preserva metadatos de la función decorada
from flask import session, redirect, url_for, flash, jsonify


# ──────────────────────────────────────────────
#  Decorador: Requiere inicio de sesión
# ──────────────────────────────────────────────
def login_required(f):
    """
    Decorador que protege rutas HTML: redirige al login si el usuario
    no tiene una sesión activa ('usuario_id' en session).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Si no hay usuario en sesión, lo envía al login
        if 'usuario_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


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
        if 'usuario_id' not in session:
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
    
    Parámetros:
        slug (str): Identificador del permiso requerido (ej: 'personal.crear')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Primero verifica que el usuario esté autenticado
            if 'usuario_id' not in session:
                return redirect(url_for('auth.login'))

            # Obtiene la lista de permisos del usuario desde la sesión
            # Usamos 'or []' porque session['permisos'] podría ser None
            user_permissions = session.get('permisos') or []

            # Si no tiene el permiso requerido, muestra error y redirige
            if slug not in user_permissions:
                flash('No tienes permisos para acceder a este módulo.', 'danger')
                return redirect(url_for('index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator
