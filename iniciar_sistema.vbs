Option Explicit

Dim WshShell, fso, strBase, strCmd, strKillCmd, strPort, strPython, strSetupPy

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Obtiene la carpeta donde está guardado este archivo VBS
strBase = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strBase

' ──────────────────────────────────────────────
'  CONFIGURACIÓN
' ──────────────────────────────────────────────
strPort   = "5000"
strPython = strBase & "\venv\Scripts\python.exe"
strSetupPy = strBase & "\setup_portable.py"

' ──────────────────────────────────────────────
'  1) DETECTAR VENV OBSOLETO (de otra computadora)
'     El venv guarda rutas absolutas del Python original.
'     Si python.exe existe pero falla al ejecutarse, hay que recrearlo.
' ──────────────────────────────────────────────
If fso.FileExists(strPython) Then
    Dim exitCode
    exitCode = WshShell.Run("cmd /c """ & strPython & """ --version", 0, True)
    If exitCode <> 0 Then
        ' El venv es de otra máquina: eliminarlo para que se recree
        WshShell.Run "cmd /c rmdir /s /q """ & strBase & "\venv""", 0, True
    End If
End If

' ──────────────────────────────────────────────
'  2) VERIFICAR ENTORNO
'     Si el venv no existe (o fue eliminado arriba), ejecutar setup
' ──────────────────────────────────────────────
If Not fso.FileExists(strPython) Then
    If fso.FileExists(strSetupPy) Then
        WshShell.Run "cmd /c python """ & strSetupPy & """", 1, True
        ' Si después del setup aún no existe Python del venv
        If Not fso.FileExists(strPython) Then
            MsgBox "El setup no pudo crear el entorno virtual." & vbCrLf & _
                   "Asegúrate de que Python esté instalado correctamente." & vbCrLf & vbCrLf & _
                   "Descarga Python desde: https://www.python.org/downloads/" & vbCrLf & _
                   "(Marca 'Add Python to PATH' al instalar)", _
                   vbExclamation, "Sistema de Gestión - Error de entorno"
            WScript.Quit 1
        End If
    Else
        MsgBox "No se encuentra el entorno virtual ni el script de setup." & vbCrLf & _
               "Asegúrate de que la carpeta del proyecto esté completa.", _
               vbCritical, "Sistema de Gestión - Error"
        WScript.Quit 1
    End If
End If

' ──────────────────────────────────────────────
'  3) LIBERAR PUERTO: mata procesos zombies en :5000
' ──────────────────────────────────────────────
strKillCmd = "cmd /c netstat -ano | findstr :" & strPort & " > ""%TEMP%\porcino_port.txt"" & for /f ""tokens=5"" %a in ('findstr LISTENING ""%TEMP%\porcino_port.txt""') do taskkill /F /PID %a 2>nul"
WshShell.Run strKillCmd, 0, True
WScript.Sleep 1000

' ──────────────────────────────────────────────
'  4) INICIAR SERVIDOR (ventana oculta, windowStyle=0)
'     NOTA: Se ejecuta directamente SIN cmd /c porque WshShell.Run
'     no maneja correctamente las comillas anidadas con cmd /c.
' ──────────────────────────────────────────────
strCmd = """" & strPython & """ """ & strBase & "\app.py"""
WshShell.Run strCmd, 0, False

' ──────────────────────────────────────────────
'  5) ESPERAR Y ABRIR NAVEGADOR
' ──────────────────────────────────────────────
WScript.Sleep 4000
WshShell.Run "http://127.0.0.1:" & strPort & "/", 1, False

Set fso = Nothing
Set WshShell = Nothing
