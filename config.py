import os      # Rutas de archivos y variables de entorno
import json    # Lectura de config.json
import secrets # Generación de clave secreta aleatoria


# ──────────────────────────────────────────────
#  Obtener ruta de BD desde config.json
# ──────────────────────────────────────────────
def get_db_path():
    """
    Lee la ruta de la base de datos desde config.json.
    Soporta rutas absolutas y relativas (resueltas desde la raíz del proyecto).
    Si el archivo no existe o está vacío, busca un .accdb dentro de database\.
    """
    project_root = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(project_root, 'config.json')

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                db_path = data.get('db_path', '')
                if db_path:
                    # Si la ruta es relativa, resolverla desde la raíz del proyecto
                    if not os.path.isabs(db_path):
                        db_path = os.path.normpath(os.path.join(project_root, db_path))
                    return db_path
        except:
            pass  # Si el JSON está corrupto, usar fallback

    # Fallback: intentar con config.example.json (plantilla que viene en git)
    example_file = os.path.join(project_root, 'config.example.json')
    if os.path.exists(example_file):
        try:
            with open(example_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                db_path = data.get('db_path', '')
                if db_path:
                    if not os.path.isabs(db_path):
                        db_path = os.path.normpath(os.path.join(project_root, db_path))
                    return db_path
        except:
            pass

    # Fallback: buscar cualquier .accdb dentro de la carpeta database/
    db_folder = os.path.join(project_root, 'database')
    if os.path.exists(db_folder):
        for f in os.listdir(db_folder):
            if f.lower().endswith('.accdb'):
                return os.path.join(db_folder, f)

    # Último recurso: archivo en la raíz del proyecto
    return os.path.join(project_root, 'database.accdb')


# ──────────────────────────────────────────────
#  Configuración global de la aplicación
# ──────────────────────────────────────────────
class Config:
    """
    Configuración general de Flask y la base de datos.
    Los valores pueden sobreescribirse con variables de entorno.
    """
    # SECRET_KEY aleatoria en cada inicio: invalida sesiones anteriores.
    # Al cerrar el navegador → servidor se apaga → al reiniciar, nueva key → login requerido.
    # Se puede fijar vía variable de entorno para depuración.
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    # Ruta de la base de datos Access (puede sobreescribirse desde la interfaz web)
    DB_PATH = os.environ.get('DB_PATH') or get_db_path()
