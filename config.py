import os
import json
import secrets

def get_db_path():
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('db_path'):
                    return data['db_path']
        except:
            pass
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.accdb')

class Config:
    # SECRET_KEY aleatoria en cada inicio: invalida sesiones anteriores
    # (navegador cerrado → servidor se apaga → al reiniciar, nueva key → login requerido)
    # Se puede fijar via variable de entorno para depuración.
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    DB_PATH = os.environ.get('DB_PATH') or get_db_path()
