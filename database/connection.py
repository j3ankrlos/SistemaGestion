import pyodbc
from config import Config
import time

def _get_db_path():
    """
    Obtiene la ruta de la BD priorizando:
    1. current_app.config['DB_PATH'] (cuando Flask está corriendo y se actualizó dinámicamente)
    2. Config.DB_PATH (fallback)
    """
    try:
        from flask import current_app
        return current_app.config.get('DB_PATH', Config.DB_PATH)
    except (RuntimeError, ImportError):
        return Config.DB_PATH

def get_connection():
    """
    Establece y retorna una conexión a la base de datos Access.
    Implementa reintentos en caso de que la BD esté bloqueada.
    Siempre lee la ruta más actualizada desde current_app o Config.
    """
    db_path = _get_db_path()
    conn_str = (
        r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
        f'DBQ={db_path};'
    )
    
    max_retries = 3
    retry_delay = 0.5  # Segundos
    
    for attempt in range(max_retries):
        try:
            conn = pyodbc.connect(conn_str, timeout=10, autocommit=False)
            return conn
        except pyodbc.Error as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise Exception(f"Error al conectar a la base de datos tras {max_retries} intentos. Detalle: {str(e)}")

def execute_query(query, params=(), commit=False, fetchall=False, fetchone=False):
    """
    Ejecuta una consulta SQL abriendo y cerrando la conexión rápidamente.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        result = None
        if fetchall:
            result = cursor.fetchall()
        elif fetchone:
            result = cursor.fetchone()
            
        if commit:
            conn.commit()
            
        return result
    finally:
        conn.close()
