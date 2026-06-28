<#
╔══════════════════════════════════════════════════════════╗
║   SISTEMA DE GESTIÓN - Descargar Python Portable      ║
║   Úsalo si la computadora NO tiene Python instalado     ║
╚══════════════════════════════════════════════════════════╝
#>

$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonDir = Join-Path $BaseDir "python-portable"
$PythonExe = Join-Path $PythonDir "python.exe"

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        Descargar Python Portable         ║" -ForegroundColor Cyan
Write-Host "║     (NO necesita permisos de admin)      ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $PythonExe) {
    Write-Host "✓ Python portable ya existe en: $PythonDir" -ForegroundColor Green
    
    # Verificar versión
    $version = & $PythonExe --version
    Write-Host "  Versión: $version" -ForegroundColor Gray
    
    # Preguntar si quiere ejecutar el setup
    $resp = Read-Host "¿Ejecutar setup del sistema? (S/n)"
    if ($resp -ne 'n') {
        & $PythonExe setup_portable.py
    }
    exit 0
}

Write-Host "Descargando Python 3.13.7 (embedded)..." -ForegroundColor Yellow
Write-Host ""

# URL del Python embedded (no necesita instalación)
$Url = "https://www.python.org/ftp/python/3.13.7/python-3.13.7-embed-amd64.zip"
$ZipFile = Join-Path $env:TEMP "python-portable.zip"

try {
    Write-Host "  Descargando de: $Url" -ForegroundColor Gray
    Import-Module -Name BitsTransfer -ErrorAction SilentlyContinue
    
    if (Get-Command Start-BitsTransfer -ErrorAction SilentlyContinue) {
        Start-BitsTransfer -Source $Url -Destination $ZipFile -DisplayName "Python Portable" -Priority High
    } else {
        # Fallback a WebClient
        $wc = New-Object System.Net.WebClient
        $wc.DownloadFile($Url, $ZipFile)
    }
    
    Write-Host "✓ Descarga completada" -ForegroundColor Green
    
    # Extraer
    New-Item -ItemType Directory -Path $PythonDir -Force | Out-Null
    Expand-Archive -Path $ZipFile -DestinationPath $PythonDir -Force
    
    # Eliminar zip
    Remove-Item $ZipFile -Force
    
    Write-Host "✓ Python portable extraído en: $PythonDir" -ForegroundColor Green
    
    # Habilitar pip (viene deshabilitado en embedded Python)
    $PthFile = Get-ChildItem $PythonDir -Filter "python*._pth" | Select-Object -First 1
    if ($PthFile) {
        $content = Get-Content $PthFile.FullName
        # Comentar la línea '#import site' para habilitar pip
        $content = $content -replace '^#import site', 'import site'
        Set-Content -Path $PthFile.FullName -Value $content
        Write-Host "✓ pip habilitado" -ForegroundColor Green
    }
    
    # Descargar get-pip.py e instalar pip
    $GetPip = Join-Path $env:TEMP "get-pip.py"
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile("https://bootstrap.pypa.io/get-pip.py", $GetPip)
    & $PythonExe $GetPip --no-warn-script-location
    Remove-Item $GetPip -Force
    
    Write-Host "✓ pip instalado" -ForegroundColor Green
    Write-Host ""
    Write-Host "Python portable listo!" -ForegroundColor Green
    Write-Host ""
    
    # Ejecutar setup
    $resp = Read-Host "¿Ejecutar setup del sistema? (S/n)"
    if ($resp -ne 'n') {
        & $PythonExe setup_portable.py
    }
    
} catch {
    Write-Host "ERROR: No se pudo descargar Python." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Alternativa manual:" -ForegroundColor Yellow
    Write-Host "  1. Ve a: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "  2. Descarga el instalador" -ForegroundColor Yellow
    Write-Host "  3. Al instalar, MARCA 'Add Python to PATH'" -ForegroundColor Yellow
    Write-Host "  4. Desmarca 'Install for all users'" -ForegroundColor Yellow
    Write-Host "  5. Ejecuta: python setup_portable.py" -ForegroundColor Yellow
    pause
}
