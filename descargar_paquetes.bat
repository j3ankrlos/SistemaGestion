@echo off
title Descargar Paquetes - Sistema de Gestión
cd /d "%~dp0"

:: ═══════════════════════════════════════════════════════
::  SISTEMA DE GESTIÓN - Descargar paquetes para uso offline
::  Ejecutar este script UNA SOLA VEZ en la PC con internet
::  Luego copiar toda la carpeta del proyecto a la otra PC
:: ═══════════════════════════════════════════════════════

echo.
echo =============================================
echo   SISTEMA DE GESTIÓN - Descarga Offline
echo =============================================
echo.
echo Este script descarga todos los paquetes Python
echo necesarios para instalarlos SIN internet.
echo.

:: Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no encontrado. Instala Python primero.
    pause
    exit /b 1
)

:: Crear carpeta wheels si no existe
if not exist "wheels" (
    mkdir wheels
    echo Carpeta wheels\ creada.
)

echo Descargando paquetes de requirements.txt...
echo (Puede tardar unos minutos segun tu velocidad de internet)
echo.

:: Intentar primero con el venv activo si existe (version exacta de Python)
if exist "venv\Scripts\pip.exe" (
    echo Usando pip del entorno virtual...
    venv\Scripts\pip.exe download -r requirements.txt -d wheels --quiet
) else (
    echo Usando pip del sistema...
    pip download -r requirements.txt -d wheels --quiet
)

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Hubo un error descargando algunos paquetes.
    echo Verifica tu conexion a internet e intentalo de nuevo.
    pause
    exit /b 1
)

:: Contar cuantos archivos se descargaron
set count=0
for %%f in (wheels\*.whl wheels\*.tar.gz wheels\*.zip) do set /a count+=1

echo.
echo =============================================
echo   DESCARGA COMPLETADA
echo =============================================
echo.
echo   Paquetes descargados: %count% archivo(s) en wheels\
echo.
echo   SIGUIENTE PASO:
echo   Copia la carpeta completa del proyecto a la otra
echo   computadora. El sistema instalara estos paquetes
echo   automaticamente sin necesitar internet.
echo.
pause
