from database.connection import get_connection  # Conexión a BD Access

# ──────────────────────────────────────────────
#  Creación de tablas del sistema RBAC
# ──────────────────────────────────────────────
def create_tables():
    """
    Crea las tablas del sistema RBAC (Roles, Permisos, Usuarios, Permiso_Rol)
    si no existen en la base de datos Access.
    Cada CREATE TABLE está envuelto en try/except para que si la tabla ya existe
    no detenga la creación de las siguientes.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # ── Tabla Roles: almacena los nombres de los roles del sistema ──
    try:
        cursor.execute('''
            CREATE TABLE Roles (
                IdRol AUTOINCREMENT PRIMARY KEY,  -- ID autonumérico
                Rol VARCHAR(255)                   -- Nombre del rol (ej: Administrador)
            )
        ''')
        print("Tabla Roles creada.")
    except Exception as e:
        print("La tabla Roles ya existe o hubo un error:", e)

    # ── Tabla Permisos: catálogo de permisos (módulo + acción + slug único) ──
    try:
        cursor.execute('''
            CREATE TABLE Permisos (
                IdPermiso AUTOINCREMENT PRIMARY KEY,  -- ID autonumérico
                Modulo VARCHAR(255),                   -- Módulo (ej: usuarios, roles)
                Accion VARCHAR(255),                   -- Acción (ej: ver, crear)
                Slug VARCHAR(255) UNIQUE               -- Identificador único (ej: usuarios.ver)
            )
        ''')
        print("Tabla Permisos creada.")
    except Exception as e:
        print("La tabla Permisos ya existe o hubo un error:", e)

    # ── Tabla Usuarios: credenciales y vinculación con Personal ──
    try:
        cursor.execute('''
            CREATE TABLE Usuarios (
                IdUsuario AUTOINCREMENT PRIMARY KEY,  -- ID autonumérico
                Usuario VARCHAR(255) UNIQUE,           -- Nombre de usuario (login)
                Clave VARCHAR(255),                    -- Contraseña hasheada con bcrypt
                NombreCorto VARCHAR(255),              -- Nombre para mostrar en la interfaz
                Fk_IdPersonal INT,                     -- Relación con tabla Personal (opcional)
                Fk_IdRol INT,                          -- Relación con tabla Roles
                Fk_Sitio INT,                          -- Sitio al que pertenece
                Fk_Status INT                          -- 1=Activo, 2=Inactivo
            )
        ''')
        print("Tabla Usuarios creada.")
    except Exception as e:
        print("La tabla Usuarios ya existe o hubo un error:", e)

    # ── Tabla Permiso_Rol: matriz muchos-a-muchos entre roles y permisos ──
    try:
        cursor.execute('''
            CREATE TABLE Permiso_Rol (
                Fk_IdRol INT,      -- ID del rol
                Fk_IdPermiso INT,  -- ID del permiso
                PRIMARY KEY (Fk_IdRol, Fk_IdPermiso)  -- Clave compuesta (no duplicados)
            )
        ''')
        print("Tabla Permiso_Rol creada.")
    except Exception as e:
        print("La tabla Permiso_Rol ya existe o hubo un error:", e)

    conn.commit()  # Confirma todos los cambios

    # ── Tabla HistorialIncidencias: registro de incidencias del personal ──
    try:
        cursor.execute('''
            CREATE TABLE HistorialIncidencias (
                IdHistorial AUTOINCREMENT PRIMARY KEY,
                Fk_IdIncidencia INT,
                Fk_IdPersonal INT,
                Fk_IdUsuario INT,
                FechaInicio DATETIME,
                FechaFin DATETIME,
                Observacion VARCHAR(255),
                Fk_Status INT,
                FechaRegistro DATETIME
            )
        ''')
        print("Tabla HistorialIncidencias creada.")
    except Exception as e:
        print("La tabla HistorialIncidencias ya existe o hubo un error:", e)

    conn.commit()
    conn.close()

def init_default_data():
    """
    Inserta datos por defecto si la base de datos está recién creada.
    """
    from database.connection import execute_query
    import bcrypt
    
    # Revisar si hay roles
    roles = execute_query("SELECT COUNT(*) FROM Roles", fetchone=True)
    if roles and roles[0] == 0:
        execute_query("INSERT INTO Roles (Rol) VALUES (?)", ('Administrador',), commit=True)
        execute_query("INSERT INTO Roles (Rol) VALUES (?)", ('Operador',), commit=True)
        print("Roles por defecto insertados.")

    # Revisar si hay usuarios
    usuarios = execute_query("SELECT COUNT(*) FROM Usuarios", fetchone=True)
    if usuarios and usuarios[0] == 0:
        hashed_pw = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        execute_query(
            "INSERT INTO Usuarios (Usuario, Clave, NombreCorto, Fk_IdRol, Fk_Sitio, Fk_Status) VALUES (?, ?, ?, ?, ?, ?)",
            ('admin', hashed_pw, 'Administrador', 1, 1, 1),
            commit=True
        )
        print("Usuario admin creado (admin / admin123).")

    # Revisar si hay incidencias en el catálogo
    incidencias = execute_query("SELECT COUNT(*) FROM Incidencias", fetchone=True)
    if incidencias and incidencias[0] == 0:
        tipos = [
            ('Reposo', 'REP'),
            ('Vacaciones', 'VAC'),
            ('Permiso Paternidad', 'PAT'),
            ('Permiso Matrimonio', 'MAT'),
            ('Permiso Funeral', 'FUN'),
            ('Permiso Diligencias Personales', 'DIL'),
        ]
        for nombre, sigla in tipos:
            execute_query(
                "INSERT INTO Incidencias (Incidencia, SiglaIncidencia) VALUES (?, ?)",
                (nombre, sigla), commit=True
            )
        print(f"{len(tipos)} tipos de incidencias insertados.")

if __name__ == '__main__':
    create_tables()
    init_default_data()
    print("Inicialización de BD completada.")
