import subprocess  # Para ejecutar PowerShell y capturar su salida
import sys


# ──────────────────────────────────────────────
#  Selector de archivos (diálogo nativo de Windows)
# ──────────────────────────────────────────────
def main():
    """
    Abre un diálogo de selección de archivos usando PowerShell.
    Funciona incluso cuando Python está en modo oculto (sin ventana de consola).
    No requiere Tkinter ni librerías externas.
    
    Retorna la ruta seleccionada por stdout, o cadena vacía si el usuario canceló.
    """
    # Script PowerShell que muestra el diálogo OpenFileDialog
    ps_script = """
    Add-Type -AssemblyName System.Windows.Forms
    $f = New-Object System.Windows.Forms.OpenFileDialog
    $f.Title = "Seleccionar Base de Datos de Access (.accdb)"
    $f.Filter = "Bases de Datos de Access (*.accdb;*.mdb)|*.accdb;*.mdb|Todos los archivos|*.*"
    $f.Multiselect = $false  # Solo permitir un archivo
    $result = $f.ShowDialog()
    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
        $f.FileName  # Imprime la ruta a stdout para capturarla desde Python
    }
    """

    try:
        # Ejecuta PowerShell oculto, captura la salida
        resultado = subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=120  # Timeout por si el usuario se toma mucho tiempo
        )
        ruta = resultado.stdout.strip()
        print(ruta or "", end="")  # Imprime sin newline para no contaminar stdout
    except Exception:
        # Si hay cualquier error, retorna vacío
        print("", end="")


if __name__ == "__main__":
    """Punto de entrada: se ejecuta como script independiente desde app.py"""
    main()
