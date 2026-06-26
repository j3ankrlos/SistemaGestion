from database.connection import get_connection

def create_tables():
    """
    Crea las tablas del sistema RBAC si no existen en la base de datos Access.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla Roles
    try:
        cursor.execute('''
            CREATE TABLE Roles (
                IdRol AUTOINCREMENT PRIMARY KEY,
                Rol VARCHAR(255)
            )
        ''')
        print("Tabla Roles creada.")
    except Exception as e:
        print("La tabla Roles ya existe o hubo un error:", e)

    # Tabla Permisos
    try:
        cursor.execute('''
            CREATE TABLE Permisos (
                IdPermiso AUTOINCREMENT PRIMARY KEY,
                Modulo VARCHAR(255),
                Accion VARCHAR(255),
                Slug VARCHAR(255) UNIQUE
            )
        ''')
        print("Tabla Permisos creada.")
    except Exception as e:
        print("La tabla Permisos ya existe o hubo un error:", e)

    # Tabla Usuarios
    try:
        cursor.execute('''
            CREATE TABLE Usuarios (
                IdUsuario AUTOINCREMENT PRIMARY KEY,
                Usuario VARCHAR(255) UNIQUE,
                Clave VARCHAR(255),
                NombreCorto VARCHAR(255),
                Fk_IdPersonal INT,
                Fk_IdRol INT,
                Fk_Sitio INT,
                Fk_Status INT
            )
        ''')
        print("Tabla Usuarios creada.")
    except Exception as e:
        print("La tabla Usuarios ya existe o hubo un error:", e)

    # Tabla Permiso_Rol
    try:
        cursor.execute('''
            CREATE TABLE Permiso_Rol (
                Fk_IdRol INT,
                Fk_IdPermiso INT,
                PRIMARY KEY (Fk_IdRol, Fk_IdPermiso)
            )
        ''')
        print("Tabla Permiso_Rol creada.")
    except Exception as e:
        print("La tabla Permiso_Rol ya existe o hubo un error:", e)

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

if __name__ == '__main__':
    create_tables()
    init_default_data()
    print("Inicialización de BD completada.")
