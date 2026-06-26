import subprocess
import sys

def main():
    """
    Usa PowerShell con System.Windows.Forms para mostrar el diálogo de selección.
    Funciona incluso cuando Python se ejecuta en modo oculto (sin ventana de consola).
    No requiere Tkinter ni ninguna librería externa.
    """
    # Usar $f.FileName directamente (sin Write-Host) para que vaya a stdout capturable
    ps_script = """
    Add-Type -AssemblyName System.Windows.Forms
    $f = New-Object System.Windows.Forms.OpenFileDialog
    $f.Title = "Seleccionar Base de Datos de Access (.accdb)"
    $f.Filter = "Bases de Datos de Access (*.accdb;*.mdb)|*.accdb;*.mdb|Todos los archivos|*.*"
    $f.Multiselect = $false
    $result = $f.ShowDialog()
    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
        $f.FileName
    }
    """

    try:
        resultado = subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=120
        )
        ruta = resultado.stdout.strip()
        print(ruta or "", end="")
    except Exception:
        print("", end="")

if __name__ == "__main__":
    main()
