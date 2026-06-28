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

:: ── 2) Detectar venv obsoleto (de otra computadora) ──
::    Si python.exe existe pero falla al ejecutarse, el venv es invalido.
::    Esto pasa cuando el venv fue creado en otra maquina con diferente ruta de Python.
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

:: ── 3) Crear entorno virtual si no existe ──
if not exist "venv" (
    echo [1/3] Creando entorno virtual...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] No se pudo crear el entorno virtual.
        echo Asegurate de que Python este instalado correctamente.
        pause
        exit /b 1
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
        echo        Paquetes locales incompletos, intentando online...
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

:: ── 4) Liberar puerto 5000 (matar procesos zombies) ──
echo [3/3] Verificando puerto 5000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    echo         Liberando puerto 5000 ^(PID %%a^)...
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: ── 5) Verificar driver ODBC Access ──
venv\Scripts\python.exe -c "import pyodbc; [d for d in pyodbc.drivers() if 'access' in d.lower()][0]" >nul 2>&1
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
echo   SISTEMA PORCINO
echo ========================================
echo.
echo Servidor: http://localhost:5000
echo Para salir: Cierra esta ventana o pulsa Ctrl+C
echo.
venv\Scripts\python.exe app.py

:: Si el servidor se cierra, mantener ventana visible
echo.
echo Servidor detenido.
pause
