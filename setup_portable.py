"""
╔══════════════════════════════════════════════════════════╗
║   SISTEMA PORCINO - Setup Portable                      ║
║   Prepara el entorno sin permisos de administrador      ║
╚══════════════════════════════════════════════════════════╝

Este script verifica e instala todo lo necesario para ejecutar
el sistema en cualquier computadora SIN permisos de admin.

¿Qué hace?
  1. Verifica que Python esté instalado
  2. Crea un entorno virtual (venv) si no existe
  3. Instala las dependencias (Flask, pyodbc, bcrypt, waitress)
  4. Verifica el driver ODBC de Microsoft Access
  5. Crea config.json con la ruta de la base de datos
  6. Prueba la conexión a la base de datos
"""

import sys
import os
import subprocess
import shutil
import json
import ctypes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(BASE_DIR, 'venv')
REQUIREMENTS_FILE = os.path.join(BASE_DIR, 'requirements.txt')
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')

# Colores para terminal
class Color:
    VERDE = '\033[92m'
    AMARILLO = '\033[93m'
    ROJO = '\033[91m'
    AZUL = '\033[94m'
    NEGRITA = '\033[1m'
    RESET = '\033[0m'

def ok(msg):
    print(f"{Color.VERDE}✓ {msg}{Color.RESET}")

def warn(msg):
    print(f"{Color.AMARILLO}⚠ {msg}{Color.RESET}")

def error(msg):
    print(f"{Color.ROJO}✗ {msg}{Color.RESET}")

def info(msg):
    print(f"{Color.AZUL}• {msg}{Color.RESET}")

def titulo(msg):
    print(f"\n{Color.NEGRITA}{msg}{Color.RESET}")
    print("─" * 60)


def es_admin():
    """Verifica si el script se ejecuta como administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False


def check_python():
    """Verifica que Python esté disponible."""
    titulo("1. Verificando Python")
    
    # Posibles nombres del ejecutable de Python
    python_cmds = [
        ('python', sys.executable),
    ]
    
    # Intentar encontrar python en PATH
    python_exe = None
    python_version = None
    
    # Primero usamos el Python actual (el que ejecuta este script)
    python_exe = sys.executable
    python_version = sys.version
    ok(f"Python encontrado: {python_exe}")
    info(f"Versión: {python_version.split()[0]}")
    
    major = sys.version_info.major
    minor = sys.version_info.minor
    
    if major < 3 or (major == 3 and minor < 8):
        error("Se requiere Python 3.8 o superior")
        info("Descarga Python desde: https://www.python.org/downloads/")
        info("NO necesitas permisos de admin: elige 'Install for all users' = NO")
        return False
    
    ok(f"Python {major}.{minor}.{sys.version_info.micro} - compatible")
    
    # Guardar la ruta del exe
    with open(os.path.join(BASE_DIR, '.python_exe'), 'w') as f:
        f.write(python_exe)
    
    return True


def setup_venv():
    """Crea el entorno virtual si no existe e instala dependecias."""
    titulo("2. Entorno virtual (venv)")
    
    if os.path.exists(VENV_DIR):
        ok("El venv ya existe")
        # Verificar que el Python del venv sea usable
        python_venv = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
        if os.path.exists(python_venv):
            info(f"Python del venv: {python_venv}")
            return True
        else:
            warn("El venv está corrupto, se recreará")
            shutil.rmtree(VENV_DIR)
    
    info("Creando entorno virtual...")
    result = subprocess.run(
        [sys.executable, '-m', 'venv', VENV_DIR],
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        error(f"No se pudo crear el venv: {result.stderr}")
        return False
    
    ok("Entorno virtual creado")
    
    # Instalar dependencias
    titulo("3. Instalando dependencias")
    
    python_venv = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
    
    # Actualizar pip
    info("Actualizando pip...")
    subprocess.run([python_venv, '-m', 'pip', 'install', '--upgrade', 'pip'],
                   capture_output=True, text=True)
    
    if os.path.exists(REQUIREMENTS_FILE):
        info(f"Instalando desde {REQUIREMENTS_FILE}...")
        result = subprocess.run(
            [python_venv, '-m', 'pip', 'install', '-r', REQUIREMENTS_FILE],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            ok("Dependencias instaladas correctamente")
        else:
            error(f"Error instalando dependencias: {result.stderr}")
            info("Puedes intentarlo manualmente con:")
            info(f'  {python_venv} -m pip install -r "{REQUIREMENTS_FILE}"')
            return False
    else:
        warn(f"No se encontró {REQUIREMENTS_FILE}")
        info("Instalando dependencias mínimas...")
        result = subprocess.run(
            [python_venv, '-m', 'pip', 'install', 'Flask', 'pyodbc', 'bcrypt', 'waitress'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            ok("Dependencias instaladas")
        else:
            error(f"Error: {result.stderr}")
            return False
    
    return True


def check_odbc_driver():
    """Verifica que el driver ODBC de Access esté instalado."""
    titulo("4. Driver ODBC de Microsoft Access")
    
    # Probar con el Python del venv
    python_venv = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
    
    check_code = """
import pyodbc
drivers = pyodbc.drivers()
access_drivers = [d for d in drivers if 'access' in d.lower()]
print('\\n'.join(access_drivers) if access_drivers else 'NINGUNO')
"""
    
    result = subprocess.run(
        [python_venv, '-c', check_code],
        capture_output=True, text=True
    )
    
    output = result.stdout.strip()
    
    if 'NINGUNO' in output:
        error("No hay driver de Microsoft Access instalado.")
        print()
        info("Para que el sistema funcione, necesitas el 'Microsoft Access Database Engine'.")
        info("Descárgalo GRATIS desde Microsoft (NO necesitas Office):")
        info("  https://aka.ms/accessdatabasengine")
        print()
        warn("IMPORTANTE: El driver ODBC SÍ requiere permisos de administrador para instalarse.")
        info("Si no tienes admin, pídele a TI que ejecute:")
        if not es_admin():
            if sys.maxsize > 2**32:
                info("  AccessDatabaseEngine_X64.exe /quiet")
            else:
                info("  AccessDatabaseEngine.exe /quiet")
        print()
        info("Alternativa: Si ya tienes Microsoft Office instalado, el driver ya está presente.")
        
        return False
    
    drivers = output.split('\n')
    for d in drivers:
        if d.strip():
            ok(f"Driver encontrado: {d.strip()}")
    return True


def setup_config():
    """Configura la ruta de la base de datos."""
    titulo("5. Configuración de base de datos")
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            db_path = cfg.get('db_path', '')
            if db_path and os.path.exists(db_path):
                ok(f"Configurado: {db_path}")
                return True
            elif db_path:
                warn(f"La ruta guardada no existe: {db_path}")
            else:
                warn("config.json vacío")
        except:
            warn("config.json inválido")
    else:
        info("No hay config.json todavía")
    
    # Buscar archivos .accdb en el mismo directorio o subdirectorios
    info("Buscando bases de datos .accdb...")
    accdb_files = []
    for root, dirs, files in os.walk(BASE_DIR):
        for f in files:
            if f.lower().endswith('.accdb'):
                accdb_files.append(os.path.join(root, f))
    
    if accdb_files:
        info(f"Se encontraron {len(accdb_files)} base(s) de datos:")
        for f in accdb_files:
            info(f"  • {f}")
        
        # Usar la primera
        db_path = accdb_files[0]
    else:
        warn("No se encontró ningún archivo .accdb")
        info("Deberás configurar la ruta manualmente desde la interfaz web")
        info("(Módulo Configuración > Base de Datos)")
        
        # Crear config.json con ruta vacía
        config = {"db_path": ""}
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            warn(f"config.json creado con ruta vacía")
        except:
            pass
        return True
    
    # Probar conexión
    info("Probando conexión...")
    
    python_venv = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
    test_code = f"""
import pyodbc
try:
    conn_str = (
        r'DRIVER=Microsoft Access Driver (*.mdb, *.accdb);'
        f'DBQ={db_path};'
    )
    conn = pyodbc.connect(conn_str, timeout=10)
    conn.close()
    print('CONEXION_OK')
except Exception as e:
    print(f'ERROR: {{e}}')
"""
    
    result = subprocess.run(
        [python_venv, '-c', test_code],
        capture_output=True, text=True, timeout=30
    )
    
    if 'CONEXION_OK' in result.stdout:
        ok(f"Conexión exitosa a: {db_path}")
        # Guardar en config.json
        config = {"db_path": db_path}
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        ok("config.json actualizado")
        return True
    else:
        error(f"No se pudo conectar: {result.stdout.strip()}")
        info("Puedes configurar la ruta manualmente desde el módulo Configuración")
        return True  # No bloqueamos el setup por esto


def create_portable_launcher():
    """Crea un lanzador PowerShell portable como alternativa al VBS."""
    titulo("6. Creando lanzador portable")
    
    ps1_path = os.path.join(BASE_DIR, 'iniciar_sistema.ps1')
    
    ps1_content = r"""# ╔══════════════════════════════════════════╗
# ║   SISTEMA PORCINO - Launcher Portable   ║
# ║   NO requiere permisos de administrador ║
# ╚══════════════════════════════════════════╝

$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BaseDir

# 1. Usar el Python del venv si existe
$PythonExe = Join-Path $BaseDir "venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "ERROR: No se encontró el entorno virtual." -ForegroundColor Red
    Write-Host "Ejecuta primero: python setup_portable.py" -ForegroundColor Yellow
    pause
    exit 1
}

# 2. Verificar que app.py existe
$AppPy = Join-Path $BaseDir "app.py"
if (-not (Test-Path $AppPy)) {
    Write-Host "ERROR: No se encontró app.py" -ForegroundColor Red
    pause
    exit 1
}

# 3. Iniciar servidor
Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     SISTEMA PORCINO - Gestión           ║" -ForegroundColor Cyan
Write-Host "╠══════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "║  Iniciando servidor...                  ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Abrir navegador después de 4 segundos
$timer = [System.Timers.Timer]::new(4000)
Register-ObjectEvent -InputObject $timer -EventName Elapsed -Action {
    Start-Process "http://localhost:5000/"
    $timer.Dispose()
} | Out-Null
$timer.Start()

# Ejecutar servidor
& $PythonExe app.py
"""
    
    with open(ps1_path, 'w', encoding='utf-8') as f:
        f.write(ps1_content)
    
    ok(f"Creado: iniciar_sistema.ps1")
    info("También puedes usar:  python app.py  desde cualquier terminal")
    return True


def print_summary(success_venv, success_odbc):
    """Muestra resumen final."""
    print()
    print("═" * 60)
    print(f"{Color.NEGRITA}       RESUMEN DEL SETUP{Color.RESET}")
    print("═" * 60)
    
    checks = [
        ("Python", True),
        ("Entorno virtual (venv)", success_venv),
        ("Dependencias instaladas", success_venv),
        ("Driver ODBC Access", success_odbc),
    ]
    
    for name, ok_flag in checks:
        status = f"{Color.VERDE}✓ OK{Color.RESET}" if ok_flag else f"{Color.ROJO}✗ FALLA{Color.RESET}"
        print(f"  {status}  {name}")
    
    print()
    
    if success_venv:
        ok("LISTO: Puedes iniciar el sistema con:")
        print()
        print(f"    {Color.AZUL}iniciar_sistema.vbs{Color.RESET}")
        print(f"    {Color.AZUL}python app.py{Color.RESET}")
        print()
    else:
        error("El setup tiene problemas. Revisa los mensajes anteriores.")
    
    if not success_odbc:
        warn("El driver ODBC de Access no está instalado.")
        info("El sistema NO podrá conectar a la base de datos Access.")
        info("Descarga: https://aka.ms/accessdatabasengine")


def main():
    print()
    print(f"{Color.NEGRITA}╔══════════════════════════════════════════════════════════╗{Color.RESET}")
    print(f"{Color.NEGRITA}║        SISTEMA PORCINO - SETUP PORTABLE                  ║{Color.RESET}")
    print(f"{Color.NEGRITA}║  Prepara el entorno SIN permisos de administrador        ║{Color.RESET}")
    print(f"{Color.NEGRITA}╚══════════════════════════════════════════════════════════╝{Color.RESET}")
    print()
    
    info(f"Directorio: {BASE_DIR}")
    info(f"Admin: {'SÍ' if es_admin() else 'NO (bien, no lo necesitamos)'}")
    print()
    
    # Paso 1: Python
    if not check_python():
        return
    
    # Paso 2 y 3: venv + dependencias
    success_venv = setup_venv()
    
    # Paso 4: Driver ODBC
    success_odbc = check_odbc_driver()
    
    # Paso 5: Config
    setup_config()
    
    # Paso 6: Launcher
    create_portable_launcher()
    
    # Resumen
    print_summary(success_venv, success_odbc)


if __name__ == '__main__':
    main()
