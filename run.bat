@echo off
title Sistema Porcino - Portable
cd /d "%~dp0"

:: ══════════════════════════════════════════
::  SISTEMA PORCINO - Launcher Portable
::  NO requiere permisos de administrador
:: ══════════════════════════════════════════

:: ── 1) Verificar Python ──
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado.
    echo.
    echo Puedes descargarlo SIN permisos de admin desde:
    echo   https://www.python.org/downloads/
    echo.
    echo O ejecuta: descargar_python.ps1 (PowerShell)
    echo.
    pause
    exit /b 1
)

:: ── 2) Crear entorno virtual si no existe ──
if not exist "venv" (
    echo [1/3] Creando entorno virtual...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
    echo [2/3] Instalando dependencias...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo [AVISO] Algunas dependencias fallaron.
        echo Puedes ignorarlo si ya estaban instaladas.
    )
) else (
    call venv\Scripts\activate.bat
)

:: ── 3) Liberar puerto 5000 (matar procesos zombies) ──
echo [3/3] Verificando puerto...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    echo    Liberando puerto 5000 (PID %%a)...
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: ── 4) Verificar driver ODBC Access (solo advertencia) ──
python -c "import pyodbc; [d for d in pyodbc.drivers() if 'access' in d.lower()][0]" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [AVISO] No se detecta el driver de Microsoft Access.
    echo El sistema requiere el Microsoft Access Database Engine.
    echo Descargalo desde: https://aka.ms/accessdatabasengine
    echo.
)

:: ── 5) Iniciar servidor ──
echo.
echo ========================================
echo   SISTEMA PORCINO
echo ========================================
echo.
echo Servidor: http://localhost:5000
echo Para salir: Cierra esta ventana o pulsa Ctrl+C
echo.
python app.py

:: Si el servidor se cierra, mantener ventana visible
echo.
echo Servidor detenido.
pause
