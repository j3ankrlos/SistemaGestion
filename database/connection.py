import pyodbc      # Driver para conectar con bases de datos Access (.accdb)
from config import Config  # Configuración global del sistema
import time         # Para pausas entre reintentos de conexión


def _get_db_path():
    """
    Obtiene la ruta de la base de datos Access priorizando:
    1. current_app.config['DB_PATH'] → Ruta actualizada dinámicamente desde la interfaz de configuración.
    2. Config.DB_PATH → Ruta por defecto definida en config.py (fallback).
    
    Esto permite que el usuario cambie la BD en tiempo de ejecución sin reiniciar el sistema.
    """
    try:
        # Intenta obtener la ruta desde la configuración activa de Flask
        from flask import current_app
        return current_app.config.get('DB_PATH', Config.DB_PATH)
    except (RuntimeError, ImportError):
        # Si Flask no está disponible (ej: scripts), usa la ruta estática de config.py
        return Config.DB_PATH


def get_connection():
    """
    Establece y retorna una conexión a la base de datos Access.
    Implementa reintentos automáticos por si la BD está bloqueada por otro usuario.
    Siempre lee la ruta más actualizada llamando a _get_db_path().
    """
    # Obtiene la ruta de la BD (prioriza la config dinámica de Flask)
    db_path = _get_db_path()
    
    # Cadena de conexión ODBC para Microsoft Access
    conn_str = (
        r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
        f'DBQ={db_path};'
    )
    
    # Configuración de reintentos en caso de que la BD esté bloqueada
    max_retries = 3      # Número máximo de intentos
    retry_delay = 0.5    # Segundos de espera entre cada intento
    
    for attempt in range(max_retries):
        try:
            # Intenta conectar con timeout de 10s y sin autocommit
            conn = pyodbc.connect(conn_str, timeout=10, autocommit=False)
            return conn  # Conexión exitosa
        except pyodbc.Error as e:
            # Si falla y aún quedan reintentos, espera y vuelve a intentar
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                # Agotó los intentos → lanza excepción con mensaje claro
                raise Exception(
                    f"Error al conectar a la base de datos tras {max_retries} intentos. "
                    f"Detalle: {str(e)}"
                )


def execute_query(query, params=(), commit=False, fetchall=False, fetchone=False):
    """
    Ejecuta una consulta SQL abriendo y cerrando la conexión rápidamente.
    Útil para operaciones puntuales sin mantener la conexión abierta.
    
    Parámetros:
        query (str): Sentencia SQL a ejecutar.
        params (tuple): Parámetros para consultas parametrizadas (evita inyección SQL).
        commit (bool): Si True, hace COMMIT de la transacción (INSERT/UPDATE/DELETE).
        fetchall (bool): Si True, retorna todas las filas del resultado.
        fetchone (bool): Si True, retorna solo la primera fila del resultado.
    """
    conn = get_connection()  # Abre una conexión nueva
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)  # Ejecuta la consulta con parámetros seguros
        
        # Procesa el resultado según lo solicitado
        result = None
        if fetchall:
            result = cursor.fetchall()   # Todas las filas (usado en SELECT múltiples)
        elif fetchone:
            result = cursor.fetchone()   # Solo la primera fila (usado en SELECT único)
        
        # Confirma los cambios si es una operación de escritura
        if commit:
            conn.commit()
        
        return result  # None si no se pidió fetchall/fetchone
    finally:
        conn.close()  # Cierra la conexión para liberar recursos
