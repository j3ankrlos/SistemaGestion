@echo off
title Sistema de Gestión - Portable
cd /d "%~dp0"

:: ══════════════════════════════════════════
::  SISTEMA DE GESTIÓN - Launcher Portable
::  NO requiere permisos de administrador
:: ══════════════════════════════════════════

:: ── 1) Verificar Python ──
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo.
    echo Descargalo SIN permisos de admin desde:
    echo   https://www.python.org/downloads/
    echo   ^(Marca "Add Python to PATH" al instalar^)
    echo.
    pause
    exit /b 1
)

:: ── 2) Verificar si estamos en modo SIN VENV ──
::    (creado por setup_portable.py cuando no se pudo crear venv)
set "PYTHON_CMD=venv\Scripts\python.exe"
if exist ".no_venv" (
    echo.
    echo [INFO] Modo sin venv activado (instalacion global).
    echo        Usando python del sistema directamente.
    echo.
    set "PYTHON_CMD=python"
    goto :run_server
)

:: ── 3) Detectar venv obsoleto (de otra computadora) ──
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo [AVISO] El entorno virtual es de otra computadora.
        echo         Eliminando y recreando automaticamente...
        echo.
        rmdir /s /q venv
    )
)

:: ── 4) Crear entorno virtual si no existe ──
if not exist "venv" (
    echo [1/3] Creando entorno virtual...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo.
        echo [AVISO] No se pudo crear el entorno virtual.
        echo         Instalando dependencias a nivel de usuario...
        echo.

        :: Instalar con --user (no necesita admin) y crear marcador
        pip install --user -r requirements.txt --quiet
        if %errorlevel% neq 0 (
            echo.
            echo [ERROR] No se pudieron instalar las dependencias.
            echo Intenta: pip install -r requirements.txt
            echo.
            pause
            exit /b 1
        )
        type nul > .no_venv
        set "PYTHON_CMD=python"
        echo        Dependencias instaladas (modo sin venv).
        goto :run_server
    )

    call venv\Scripts\activate.bat

    echo [2/3] Instalando dependencias...

    :: Intentar primero con paquetes locales (sin internet)
    if exist "wheels\" (
        echo        Usando paquetes locales ^(carpeta wheels\^)...
        pip install --no-index --find-links=wheels -r requirements.txt --quiet
        if %errorlevel% equ 0 (
            echo        Dependencias instaladas correctamente ^(modo offline^).
            goto :dependencias_ok
        )
        echo        Paquetes locales incompatibles, intentando online...
    )

    :: Intentar con internet como fallback
    pip install -r requirements.txt --quiet
    if %errorlevel% neq 0 (
        echo.
        echo [AVISO] Error instalando algunas dependencias.
        echo Si no tienes internet, ejecuta primero descargar_paquetes.bat
        echo en la computadora que SI tiene internet.
        echo.
        pause
        exit /b 1
    )

    :dependencias_ok
    echo        Listo.
) else (
    call venv\Scripts\activate.bat
)

:run_server

:: ── 5) Liberar puertos (matar procesos zombies) ──
echo [3/3] Verificando puertos disponibles...
for %%p in (5000 5001 5002) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%p" ^| findstr LISTENING') do (
        echo         Liberando puerto %%p ^(PID %%a^)...
        taskkill /F /PID %%a >nul 2>&1
    )
)
timeout /t 1 /nobreak >nul

:: ── 5) Verificar driver ODBC Access ──
%PYTHON_CMD% -c "import pyodbc; [d for d in pyodbc.drivers() if 'access' in d.lower()][0]" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [AVISO] No se detecta el driver de Microsoft Access.
    echo Si tienes Microsoft Office instalado, deberia estar disponible automaticamente.
    echo De lo contrario, descargalo desde: https://aka.ms/accessdatabasengine
    echo.
)

:: ── 6) Iniciar servidor ──
echo.
echo ========================================
echo   SISTEMA DE GESTIÓN
echo ========================================
echo.
echo Puertos: 5000, 5001, 5002 (elige el primero libre)
echo Para salir: Cierra esta ventana o pulsa Ctrl+C
echo.
%PYTHON_CMD% app.py

:: Si el servidor se cierra, mantener ventana visible
echo.
echo Servidor detenido.
pause
