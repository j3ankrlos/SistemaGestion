from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def permission_required(slug):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario_id' not in session:
                return redirect(url_for('auth.login'))
            
            user_permissions = session.get('permisos', [])
            if slug not in user_permissions:
                flash('No tienes permisos para acceder a este módulo.', 'danger')
                return redirect(url_for('index'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
