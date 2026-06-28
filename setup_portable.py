"""
╔══════════════════════════════════════════════════════════╗
║   SISTEMA DE GESTIÓN - Setup Portable                 ║
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
import subprocess   # Para ejecutar comandos en terminal
import shutil       # Para eliminar directorios (venv corrupto)
import json         # Para leer/escribir config.json
import ctypes       # Para verificar si el usuario es admin

# ── Rutas fijas del proyecto ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Raíz del proyecto
VENV_DIR = os.path.join(BASE_DIR, 'venv')               # Entorno virtual
REQUIREMENTS_FILE = os.path.join(BASE_DIR, 'requirements.txt')  # Dependencias
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')     # Configuración de BD


# ──────────────────────────────────────────────
#  Colores para terminal (formato ANSI)
# ──────────────────────────────────────────────
class Color:
    """Códigos de color ANSI para mensajes en terminal."""
    VERDE = '\033[92m'
    AMARILLO = '\033[93m'
    ROJO = '\033[91m'
    AZUL = '\033[94m'
    NEGRITA = '\033[1m'
    RESET = '\033[0m'


# ── Funciones auxiliares de mensajes ──
def ok(msg):
    """Mensaje de éxito (✓ verde)."""
    print(f"{Color.VERDE}✓ {msg}{Color.RESET}")

def warn(msg):
    """Mensaje de advertencia (⚠ amarillo)."""
    print(f"{Color.AMARILLO}⚠ {msg}{Color.RESET}")

def error(msg):
    """Mensaje de error (✗ rojo)."""
    print(f"{Color.ROJO}✗ {msg}{Color.RESET}")

def info(msg):
    """Mensaje informativo (• azul)."""
    print(f"{Color.AZUL}• {msg}{Color.RESET}")

def titulo(msg):
    """Título de sección (negrita + línea)."""
    print(f"\n{Color.NEGRITA}{msg}{Color.RESET}")
    print("─" * 60)


# ──────────────────────────────────────────────
#  Verificar si el usuario es administrador
# ──────────────────────────────────────────────
def es_admin():
    """Verifica si el script se ejecuta con permisos de administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False


# ──────────────────────────────────────────────
#  Paso 1: Verificar Python
# ──────────────────────────────────────────────
def check_python():
    """Verifica que Python >= 3.8 esté disponible en el sistema."""
    titulo("1. Verificando Python")

    # Usar el Python que está ejecutando este script
    python_exe = sys.executable
    python_version = sys.version
    ok(f"Python encontrado: {python_exe}")
    info(f"Versión: {python_version.split()[0]}")

    major = sys.version_info.major
    minor = sys.version_info.minor

    # Python 3.8+ es requerido
    if major < 3 or (major == 3 and minor < 8):
        error("Se requiere Python 3.8 o superior")
        info("Descarga Python desde: https://www.python.org/downloads/")
        info("NO necesitas permisos de admin: elige 'Install for all users' = NO")
        return False

    ok(f"Python {major}.{minor}.{sys.version_info.micro} - compatible")

    # Guardar ruta del ejecutable para usos posteriores
    with open(os.path.join(BASE_DIR, '.python_exe'), 'w') as f:
        f.write(python_exe)

    return True


# ──────────────────────────────────────────────
#  Paso 2 y 3: Entorno virtual + dependencias
# ──────────────────────────────────────────────
def setup_venv():
    """Crea el entorno virtual (venv) si no existe e instala las dependencias."""
    titulo("2. Entorno virtual (venv)")

    # Si el venv ya existe, verificar que sea usable
    if os.path.exists(VENV_DIR):
        python_venv_check = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
        if os.path.exists(python_venv_check):
            # Verificar que realmente funciona (no sea de otra máquina)
            try:
                subprocess.run([python_venv_check, '--version'],
                               capture_output=True, timeout=5)
                ok("El venv ya existe y es funcional")
                return True
            except Exception:
                warn("El venv es de otra computadora, se recreará")
        else:
            warn("El venv está corrupto, se eliminará")

        # Eliminar venv existente (intentar varios métodos)
        try:
            shutil.rmtree(VENV_DIR)
        except Exception:
            pass
        # Forzar eliminación con cmd (más agresivo en Windows)
        os.system(f'rmdir /s /q "{VENV_DIR}" 2>nul')
        if os.path.exists(VENV_DIR):
            error("No se pudo eliminar la carpeta venv/ existente.")
            info("Cierra cualquier programa que pueda estar usándola e intenta de nuevo.")
            info("O ejecuta manualmente: rmdir /s /q venv")
            return False

    # Crear entorno virtual (con reintento)
    info("Creando entorno virtual...")
    for intento in range(3):
        result = subprocess.run(
            [sys.executable, '-m', 'venv', VENV_DIR],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            break
        if intento < 2:
            warn(f"Intento {intento + 1} falló, reintentando...")
            # Limpiar cualquier rastro antes de reintentar
            os.system(f'rmdir /s /q "{VENV_DIR}" 2>nul')
        else:
            error(f"No se pudo crear el entorno virtual tras 3 intentos.")
            error(f"Detalle: {result.stderr}")
            print()
            warn("╔══════════════════════════════════════════════════════════╗")
            warn("║  NO SE PUDO CREAR EL ENTORNO VIRTUAL (venv)           ║")
            warn("║  Se usará el modo SIN VENV (instalación global)        ║")
            warn("╚══════════════════════════════════════════════════════════╝")
            print()
            info("Instalando dependencias con pip install --user...")
            print()

            # ── Modo sin venv: instalar paquetes a nivel de usuario ──
            return install_deps_system()

    ok("Entorno virtual creado")

    # ── Instalar dependencias ──
    titulo("3. Instalando dependencias")

    python_venv = os.path.join(VENV_DIR, 'Scripts', 'python.exe')

    # Actualizar pip a la última versión
    info("Actualizando pip...")
    subprocess.run([python_venv, '-m', 'pip', 'install', '--upgrade', 'pip'],
                   capture_output=True, text=True)

    # Ruta de la carpeta wheels (paquetes precargados para offline)
    wheels_dir = os.path.join(BASE_DIR, 'wheels')

    # Instalar dependencias: primero intentar offline desde wheels/
    if os.path.exists(REQUIREMENTS_FILE):
        if os.path.exists(wheels_dir):
            info("Intentando instalar desde paquetes locales (wheels/)...")
            result = subprocess.run(
                [python_venv, '-m', 'pip', 'install', '--no-index', '--find-links', wheels_dir, '-r', REQUIREMENTS_FILE],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                ok("Dependencias instaladas desde paquetes locales")
            else:
                warn("Paquetes locales incompatibles (versión de Python diferente)")
                info("Intentando instalación desde internet...")
                result = subprocess.run(
                    [python_venv, '-m', 'pip', 'install', '-r', REQUIREMENTS_FILE],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    ok("Dependencias instaladas desde internet")
                else:
                    error(f"Error instalando dependencias: {result.stderr}")
                    info("Verifica tu conexión a internet e inténtalo de nuevo:")
                    info(f'  {python_venv} -m pip install -r "{REQUIREMENTS_FILE}"')
                    return False
        else:
            # No hay carpeta wheels, instalar directamente desde internet
            info("No se encontró carpeta wheels/, instalando desde internet...")
            result = subprocess.run(
                [python_venv, '-m', 'pip', 'install', '-r', REQUIREMENTS_FILE],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                ok("Dependencias instaladas desde internet")
            else:
                error(f"Error instalando dependencias: {result.stderr}")
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


# ──────────────────────────────────────────────
#  Instalar dependencias a nivel de sistema (sin venv)
# ──────────────────────────────────────────────
def install_deps_system():
    """Instala paquetes con pip install --user (no necesita admin).
    Usado cuando no se pudo crear el venv.
    Crea un archivo .no_venv para que los lanzadores lo detecten."""
    titulo("3. Instalando dependencias (modo sin venv)")

    info("Usando: pip install --user (NO necesita administrador)")
    print()

    # Determinar pip correcto
    pip_cmd = [sys.executable, '-m', 'pip']

    # Actualizar pip
    info("Actualizando pip...")
    subprocess.run(pip_cmd + ['install', '--upgrade', 'pip'],
                   capture_output=True, text=True)

    wheels_dir = os.path.join(BASE_DIR, 'wheels')

    # Instalar dependencias
    if os.path.exists(REQUIREMENTS_FILE):
        if os.path.exists(wheels_dir):
            info("Intentando desde paquetes locales (wheels/)...")
            result = subprocess.run(
                pip_cmd + ['install', '--no-index', '--find-links', wheels_dir, '-r', REQUIREMENTS_FILE],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                ok("Dependencias instaladas desde paquetes locales")
            else:
                warn("Paquetes locales incompatibles, intentando desde internet...")
                result = subprocess.run(
                    pip_cmd + ['install', '-r', REQUIREMENTS_FILE],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    ok("Dependencias instaladas desde internet")
                else:
                    error(f"Error: {result.stderr}")
                    return False
        else:
            info("Instalando desde internet...")
            result = subprocess.run(
                pip_cmd + ['install', '-r', REQUIREMENTS_FILE],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                ok("Dependencias instaladas desde internet")
            else:
                error(f"Error: {result.stderr}")
                return False
    else:
        info("Instalando dependencias mínimas...")
        result = subprocess.run(
            pip_cmd + ['install', 'Flask', 'pyodbc', 'bcrypt', 'waitress'],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            error(f"Error: {result.stderr}")
            return False

    # Crear marcador .no_venv para los lanzadores (VBS, BAT)
    no_venv_file = os.path.join(BASE_DIR, '.no_venv')
    try:
        with open(no_venv_file, 'w') as f:
            f.write('1')
        ok("Modo sin venv activado (archivo .no_venv creado)")
    except Exception:
        pass

    print()
    ok("Dependencias instaladas correctamente (modo sin venv)")
    return True


# ──────────────────────────────────────────────
#  Paso 4: Verificar driver ODBC de Access
# ──────────────────────────────────────────────
def check_odbc_driver():
    """Verifica que el driver 'Microsoft Access Driver' esté instalado en el sistema."""
    titulo("4. Driver ODBC de Microsoft Access")

    # Usar Python del sistema si no hay venv, o el del venv si existe
    no_venv_file = os.path.join(BASE_DIR, '.no_venv')
    if os.path.exists(no_venv_file):
        python_venv = sys.executable
    else:
        python_venv = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
        if not os.path.exists(python_venv):
            python_venv = sys.executable

    # Código Python que lista los drivers ODBC disponibles
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
            # Detectar arquitectura para elegir el instalador correcto
            if sys.maxsize > 2**32:
                info("  AccessDatabaseEngine_X64.exe /quiet")
            else:
                info("  AccessDatabaseEngine.exe /quiet")
        print()
        info("Alternativa: Si ya tienes Microsoft Office instalado, el driver ya está presente.")
        return False

    # Mostrar los drivers encontrados
    drivers = output.split('\n')
    for d in drivers:
        if d.strip():
            ok(f"Driver encontrado: {d.strip()}")
    return True


# ──────────────────────────────────────────────
#  Paso 5: Configurar ruta de base de datos
# ──────────────────────────────────────────────
def setup_config():
    """Busca un archivo .accdb en el proyecto y configura la conexión."""
    titulo("5. Configuración de base de datos")

    # Si ya existe config.json válido, lo usamos
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

    # Buscar archivos .accdb en el directorio del proyecto
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
        db_path = accdb_files[0]  # Tomar la primera encontrada
    else:
        warn("No se encontró ningún archivo .accdb")
        info("Deberás configurar la ruta manualmente desde la interfaz web")
        info("(Módulo Configuración > Base de Datos)")

        # Crear config.json con ruta vacía para que no vuele a preguntar
        config = {"db_path": ""}
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            warn(f"config.json creado con ruta vacía")
        except:
            pass
        return True

    # Probar conexión con el driver ODBC
    info("Probando conexión...")

    # Usar Python del sistema si no hay venv, o el del venv si existe
    no_venv_file = os.path.join(BASE_DIR, '.no_venv')
    if os.path.exists(no_venv_file):
        python_venv = sys.executable
    else:
        python_venv = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
        if not os.path.exists(python_venv):
            python_venv = sys.executable
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
        # Guardar ruta en config.json para que persista
        config = {"db_path": db_path}
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        ok("config.json actualizado")
        return True
    else:
        error(f"No se pudo conectar: {result.stdout.strip()}")
        info("Puedes configurar la ruta manualmente desde el módulo Configuración")
        return True  # No bloqueamos el setup por esto


# ──────────────────────────────────────────────
#  Paso 6: Crear lanzador PowerShell portable
# ──────────────────────────────────────────────
def create_portable_launcher():
    """Crea un archivo .ps1 para iniciar el sistema sin permisos de admin."""
    titulo("6. Creando lanzador portable")

    ps1_path = os.path.join(BASE_DIR, 'iniciar_sistema.ps1')

    # Contenido del script PowerShell
    ps1_content = r"""# ╔══════════════════════════════════════════╗
# ║   SISTEMA DE GESTIÓN - Launcher Portable   ║
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
Write-Host "║     SISTEMA DE GESTIÓN                    ║" -ForegroundColor Cyan
Write-Host "╠══════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "║  Iniciando servidor...                  ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Abrir navegador después de 4 segundos (tiempo para que el servidor arranque)
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


# ──────────────────────────────────────────────
#  Resumen final del setup
# ──────────────────────────────────────────────
def print_summary(success_venv, success_odbc, no_venv_mode):
    """Muestra un resumen con el resultado de cada paso del setup."""
    print()
    print("═" * 60)
    print(f"{Color.NEGRITA}       RESUMEN DEL SETUP{Color.RESET}")
    print("═" * 60)

    modo_venv = "SIN venv (instalación global)" if no_venv_mode else "Con venv"
    checks = [
        ("Python", True),
        ("Entorno virtual", success_venv),
        (f"  └ Modo: {modo_venv}", True),
        ("Dependencias instaladas", success_venv),
        ("Driver ODBC Access", success_odbc),
    ]

    for name, ok_flag in checks:
        status = f"{Color.VERDE}✓ OK{Color.RESET}" if ok_flag else f"{Color.ROJO}✗ FALLA{Color.RESET}"
        print(f"  {status}  {name}")

    print()

    if success_venv:
        ok("LISTO: Puedes iniciar el sistema dando doble clic en:")
        print()
        print(f"    {Color.AZUL}iniciar_sistema.vbs{Color.RESET}")
        print()
        if no_venv_mode:
            info("(Modo sin venv — los lanzadores usarán python directamente)")
        print()
    else:
        error("El setup tiene problemas. Revisa los mensajes anteriores.")

    if not success_odbc:
        warn("El driver ODBC de Access no está instalado.")
        info("El sistema NO podrá conectar a la base de datos Access.")
        info("Descarga: https://aka.ms/accessdatabasengine")


# ──────────────────────────────────────────────
#  Función principal
# ──────────────────────────────────────────────
def main():
    """Ejecuta todos los pasos del setup en orden."""
    print()
    print(f"{Color.NEGRITA}╔══════════════════════════════════════════════════════════╗{Color.RESET}")
    print(f"{Color.NEGRITA}║        SISTEMA DE GESTIÓN - SETUP PORTABLE              ║{Color.RESET}")
    print(f"{Color.NEGRITA}║  Prepara el entorno SIN permisos de administrador        ║{Color.RESET}")
    print(f"{Color.NEGRITA}╚══════════════════════════════════════════════════════════╝{Color.RESET}")
    print()

    info(f"Directorio: {BASE_DIR}")
    info(f"Admin: {'SÍ' if es_admin() else 'NO (bien, no lo necesitamos)'}")
    print()

    # Paso 1: Verificar Python
    if not check_python():
        return

    # Paso 2 y 3: Crear venv e instalar dependencias
    success_venv = setup_venv()

    # Paso 4: Verificar driver ODBC
    success_odbc = check_odbc_driver()

    # Paso 5: Configurar base de datos
    setup_config()

    # Paso 6: Crear lanzador .ps1
    create_portable_launcher()

    # Detectar si estamos en modo sin venv
    no_venv_mode = os.path.exists(os.path.join(BASE_DIR, '.no_venv'))

    # Resumen final
    print_summary(success_venv, success_odbc, no_venv_mode)


# ═══════════════════════════════════════════════
#  Punto de entrada
# ═══════════════════════════════════════════════
if __name__ == '__main__':
    main()
