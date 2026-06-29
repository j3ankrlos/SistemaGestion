from flask_login import UserMixin, AnonymousUserMixin
from database.connection import execute_query


# ═══════════════════════════════════════════════
#  Usuario autenticado (Flask-Login)
# ═══════════════════════════════════════════════
class User(UserMixin):
    """
    Modelo de usuario que usa Flask-Login.
    Reemplaza el acceso directo a session['...'] por atributos de objeto.
    
    Los objetos User se crean en:
    - auth.login() al iniciar sesión (login_user)
    - user_loader al cargar desde cookie en cada request
    """

    def __init__(self, id, usuario, nombre, rol_id, rol_nombre,
                 id_personal, fk_sitio, iniciales, permisos):
        self.id = id
        self.usuario = usuario
        self.nombre = nombre
        self.rol_id = rol_id
        self.rol_nombre = rol_nombre
        self.id_personal = id_personal
        self.fk_sitio = fk_sitio
        self.iniciales = iniciales
        self._permisos = permisos or []

    def tiene_permiso(self, slug):
        """Verifica si el usuario tiene un permiso específico (RBAC)."""
        return slug in (self._permisos or [])

    def get_id(self):
        """Flask-Login requiere que el ID sea string."""
        return str(self.id)


# ═══════════════════════════════════════════════
#  Usuario anónimo (no autenticado)
# ═══════════════════════════════════════════════
class AnonymousUser(AnonymousUserMixin):
    """
    Reemplaza el AnonymousUserMixin por defecto para que
    las templates puedan usar current_user.tiene_permiso()
    y current_user.rol_id incluso sin estar logueados,
    sin lanzar AttributeError.
    """

    def tiene_permiso(self, slug):
        return False

    @property
    def rol_id(self):
        return None

    @property
    def fk_sitio(self):
        return 0

    @property
    def iniciales(self):
        return 'U'

    @property
    def nombre(self):
        return 'Usuario'

    @property
    def rol_nombre(self):
        return ''

    @property
    def id_personal(self):
        return 0

    @property
    def _permisos(self):
        return []


# ═══════════════════════════════════════════════
#  Cargador de usuario (Flask-Login user_loader)
# ═══════════════════════════════════════════════
def get_user_by_id(user_id):
    """
    Construye un objeto User completo consultando la BD.
    Flask-Login llama a esta función en cada request
    para reconstruir el usuario desde la cookie de sesión.
    
    Esto garantiza que:
    - Los permisos siempre estén actualizados (no quedan obsoletos en sesión)
    - El usuario se invalida automáticamente si se elimina de la BD
    - No hay datos de sesión corruptos o inconsistentes
    """
    data = execute_query(
        """SELECT u.IdUsuario, u.Usuario, u.NombreCorto,
                  u.Fk_IdRol, r.Rol, u.Fk_IdPersonal, u.Fk_Sitio,
                  p.Nombres, p.Apellidos
           FROM (Usuarios u
           LEFT JOIN Roles r ON u.Fk_IdRol = r.IdRol)
           LEFT JOIN Personal p ON u.Fk_IdPersonal = p.IdPersonal
           WHERE u.IdUsuario = ?""",
        (user_id,), fetchone=True
    )
    if not data:
        return None

    (id, usuario, nombre, rol_id, rol_nombre,
     id_personal, fk_sitio, nombres, apellidos) = data

    # ── Calcular iniciales para el avatar ──
    iniciales = ''
    if nombres and apellidos:
        iniciales = (nombres[0] + apellidos[0]).upper()
    elif nombre:
        partes = nombre.split()
        if len(partes) >= 2:
            iniciales = (partes[0][0] + partes[1][0]).upper()
        else:
            iniciales = nombre[0].upper()

    # ── Cargar permisos del rol (RBAC) ──
    if rol_id:
        permisos_raw = execute_query(
            """SELECT p.Slug
               FROM Permisos p
               INNER JOIN Permiso_Rol pr ON p.IdPermiso = pr.Fk_IdPermiso
               WHERE pr.Fk_IdRol = ?""",
            (rol_id,), fetchall=True
        )
        slugs = [row[0] for row in permisos_raw] if permisos_raw else []
    else:
        slugs = []

    return User(
        id=id, usuario=usuario, nombre=nombre,
        rol_id=rol_id, rol_nombre=rol_nombre or '',
        id_personal=id_personal or 0, fk_sitio=fk_sitio or 0,
        iniciales=iniciales, permisos=slugs
    )
