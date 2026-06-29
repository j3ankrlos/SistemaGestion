import pyodbc           # Driver ODBC para Access
from config import Config
import time
import threading         # Para caché de conexión thread-local


# ──────────────────────────────────────────────────────
#  Caché de conexión thread-local
# ──────────────────────────────────────────────────────
# Cada hilo (cada request en Waitress) mantiene su propia
# conexión reutilizable, evitando abrir/cerrar constantemente
# y saturar el driver ODBC de Microsoft Access.
_local = threading.local()
_conn_lock = threading.Lock()     # Serializa creación de conexiones nuevas


def _get_db_path():
    """
    Obtiene la ruta de la base de datos Access priorizando:
    1. current_app.config['DB_PATH'] → Ruta actualizada dinámicamente.
    2. Config.DB_PATH → Ruta por defecto (fallback).
    """
    try:
        from flask import current_app
        return current_app.config.get('DB_PATH', Config.DB_PATH)
    except (RuntimeError, ImportError):
        return Config.DB_PATH


def _crear_conexion():
    """Crea una conexión nueva con reintentos."""
    db_path = _get_db_path()
    conn_str = (
        r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
        f'DBQ={db_path};'
    )
    max_retries = 3
    retry_delay = 0.5
    for attempt in range(max_retries):
        try:
            conn = pyodbc.connect(conn_str, timeout=10, autocommit=False)
            return conn
        except pyodbc.Error as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise Exception(
                    f"Error al conectar a la BD tras {max_retries} intentos. "
                    f"Detalle: {str(e)}"
                )


def get_connection():
    """
    Retorna una conexión en caché para el hilo actual.
    Si es la primera llamada del hilo, crea una conexión nueva.
    Antes de reutilizar la conexión, verifica que siga viva con un
    health-check (SELECT 1). Si falla, la reemplaza por una nueva.
    """
    conn = getattr(_local, 'conn', None)
    if conn is not None:
        # Health-check: verificar que la conexión sigue viva
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return conn
        except pyodbc.Error:
            # Conexión muerta → cerrarla y crear una nueva
            try:
                conn.close()
            except Exception:
                pass
            _local.conn = None

    # Crear conexión nueva (con lock para no saturar el driver)
    with _conn_lock:
        # Doble-check: otro hilo pudo haberla creado mientras esperábamos el lock
        if getattr(_local, 'conn', None) is not None:
            return _local.conn
        _local.conn = _crear_conexion()
    return _local.conn


def close_connection():
    """
    Cierra la conexión del hilo actual (si existe).
    Útil para limpiar recursos en apagado o tests.
    """
    conn = getattr(_local, 'conn', None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
        _local.conn = None


def execute_query(query, params=(), commit=False, fetchall=False, fetchone=False):
    """
    Ejecuta una consulta SQL reutilizando la conexión del hilo actual.
    
    La conexión NO se cierra al final — se guarda en caché thread-local
    para ser reutilizada en la siguiente llamada del mismo hilo.
    Esto evita saturar el driver ODBC de Access con aperturas/cierres
    constantes en entornos multi-hilo como Waitress.
    
    Parámetros:
        query (str): Sentencia SQL a ejecutar.
        params (tuple): Parámetros para consultas parametrizadas.
        commit (bool): Si True, hace COMMIT (INSERT/UPDATE/DELETE).
        fetchall (bool): Si True, retorna todas las filas.
        fetchone (bool): Si True, retorna solo la primera fila.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
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
        try:
            cursor.close()
        except Exception:
            pass
