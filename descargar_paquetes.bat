@echo off
title Descargar Paquetes - Sistema de Gestión
cd /d "%~dp0"

:: ═══════════════════════════════════════════════════════
::  SISTEMA DE GESTIÓN - Descargar paquetes para uso offline
::  =====================================================
::  ¿Qué hace?
::   Descarga las ruedas (wheels) de Python necesarias
::   para Python 3.11, 3.12 y 3.13 (las 3 versiones).
::   Así la carpeta wheels/ sirve en CUALQUIER PC
::   SIN necesidad de internet ni permisos de admin.
::
;;  ¿Cómo se usa?
::   1. Ejecutar UNA SOLA VEZ en la PC con internet
::   2. Hacer git add + git commit + git push
;;   3. En la otra PC: git pull
;;   4. Ejecutar iniciar_sistema.vbs (instala offline)
;; ═══════════════════════════════════════════════════════

echo.
echo =============================================
echo   SISTEMA DE GESTIÓN - Descarga Offline
echo =============================================
echo.
echo Descargando paquetes para Python 3.11, 3.12 y 3.13
echo (todas las versiones共存 en wheels/)
echo.
echo Las ruedas .py3-none-any (Python puro) se descargan
echo una sola vez. Las version-specific (pyodbc, markupsafe)
echo se descargan para cada version de Python.
echo.

:: ── Verificar Python ──
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no encontrado. Instala Python primero.
    pause
    exit /b 1
)

:: ── Limpiar carpeta wheels (solo version-specific, no las py3) ──
if not exist "wheels" (
    mkdir wheels
) else (
    echo Limpiando ruedas version-specific antiguas...
    del /q "wheels\*cp3*-win_amd64.whl" 2>nul
    echo Listo.
)

echo.
echo =============================================
echo  IMPORTANTE: Conexion a internet requerida
echo =============================================
echo.
echo Se descargaran paquetes para las 3 versiones
echo de Python. Si solo te interesa una version
echo especifica, puedes cancelar (Ctrl+C) y editar
echo este script.
echo.

:: ── Elegir pip ──
if exist "venv\Scripts\pip.exe" (
    set PIP_CMD=venv\Scripts\pip.exe
    echo Usando pip del entorno virtual...
) else (
    set PIP_CMD=pip
    echo Usando pip del sistema...
)
echo.

:: ── Opciones comunes ──
:: Usamos --only-binary=:all: para evitar descargar source tarballs
:: SIN --no-deps para que pip descargue las dependencias (markupsafe, etc.)
set "OPTS=--only-binary=:all: -d wheels"

:: ── 1) Python actual (ruedas base + dependencias) ──
echo [1/4] Descargando ruedas para la version actual de Python...
%PIP_CMD% download -r requirements.txt %OPTS% 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Fallo la descarga inicial. Verifica internet.
    pause
    exit /b 1
)
echo     OK - Ruedas base descargadas
echo.

:: ── 2) Python 3.11 ──
echo [2/4] Descargando ruedas para Python 3.11 (win_amd64)...
%PIP_CMD% download -r requirements.txt %OPTS% --python-version 3.11 --platform win_amd64 2>nul
if %errorlevel% equ 0 (
    echo     OK - Ruedas para Python 3.11 descargadas
) else (
    echo     [AVISO] No se pudieron descargar algunas ruedas para 3.11
)
echo.

:: ── 3) Python 3.12 ──
echo [3/4] Descargando ruedas para Python 3.12 (win_amd64)...
%PIP_CMD% download -r requirements.txt %OPTS% --python-version 3.12 --platform win_amd64 2>nul
if %errorlevel% equ 0 (
    echo     OK - Ruedas para Python 3.12 descargadas
) else (
    echo     [AVISO] No se pudieron descargar algunas ruedas para 3.12
)
echo.

:: ── 4) Python 3.13 ──
echo [4/4] Descargando ruedas para Python 3.13 (win_amd64)...
%PIP_CMD% download -r requirements.txt %OPTS% --python-version 3.13 --platform win_amd64 2>nul
if %errorlevel% equ 0 (
    echo     OK - Ruedas para Python 3.13 descargadas
) else (
    echo     [AVISO] No se pudieron descargar algunas ruedas para 3.13
)
echo.

:: ── Contar resultados ──
set count311=0
set count312=0
set count313=0
set countgen=0
for %%f in (wheels\*cp311*.whl) do set /a count311+=1
for %%f in (wheels\*cp312*.whl) do set /a count312+=1
for %%f in (wheels\*cp313*.whl) do set /a count313+=1
for %%f in (wheels\*py3*.whl) do set /a countgen+=1
set /a total=count311+count312+count313+countgen

echo.
echo =============================================
echo   DESCARGA COMPLETADA
echo =============================================
echo.
echo   Total ruedas: %total% archivo(s) en wheels\
echo   ├─ Python puro (todas las versiones): %countgen%
echo   ├─ Python 3.11 especificas:          %count311%
echo   ├─ Python 3.12 especificas:          %count312%
echo   └─ Python 3.13 especificas:          %count313%
echo.
echo   SIGUIENTE PASO:
echo.
echo   Opcion A - Via GitHub (recomendado):
echo     1. git add -A
echo     2. git commit -m "Wheels multi-version"
echo     3. git push
echo     4. En la otra PC: git pull
echo     5. Ejecutar iniciar_sistema.vbs
echo.
echo   Opcion B - Via USB:
echo     1. Copia TODA la carpeta del proyecto
echo     2. En la otra PC ejecuta iniciar_sistema.vbs
echo.
pause
