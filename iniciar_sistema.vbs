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
strPort = "5000"            ' Puerto del servidor
strPython = strBase & "\venv\Scripts\python.exe"
strSetupPy = strBase & "\setup_portable.py"

' ──────────────────────────────────────────────
'  1) VERIFICAR ENTORNO
'     Si no existe el venv o setup_portable.py, ejecutar setup
' ──────────────────────────────────────────────
If Not fso.FileExists(strPython) Then
    If fso.FileExists(strSetupPy) Then
        WshShell.Run "cmd /c python """ & strSetupPy & """", 1, True
        ' Si el Python del sistema no existe, ofrecer ayuda
        If Not fso.FileExists(strPython) Then
            MsgBox "No se encontró Python. Puedes descargarlo SIN admin desde:" & vbCrLf & _
                   "https://www.python.org/downloads/" & vbCrLf & vbCrLf & _
                   "O ejecuta: descargar_python.ps1 (PowerShell)", _
                   vbExclamation, "Sistema Porcino - Falta Python"
            WScript.Quit 1
        End If
    Else
        MsgBox "No se encuentra el entorno virtual ni el script de setup." & vbCrLf & _
               "Asegúrate de que la carpeta está completa.", _
               vbCritical, "Sistema Porcino - Error"
        WScript.Quit 1
    End If
End If

' ──────────────────────────────────────────────
'  2) LIBERAR PUERTO: mata procesos zombies
' ──────────────────────────────────────────────
strKillCmd = "cmd /c netstat -ano | findstr :" & strPort & " > ""%TEMP%\porcino_port.txt"" & for /f ""tokens=5"" %a in ('findstr LISTENING ""%TEMP%\porcino_port.txt""') do taskkill /F /PID %a 2>nul"
WshShell.Run strKillCmd, 0, True
WScript.Sleep 1000

' ──────────────────────────────────────────────
'  3) INICIAR SERVIDOR (ventana oculta, windowStyle=0)
' ──────────────────────────────────────────────
strCmd = "cmd /c """ & strPython & """ app.py"
WshShell.Run strCmd, 0, False

' ──────────────────────────────────────────────
'  4) ESPERAR Y ABRIR NAVEGADOR
' ──────────────────────────────────────────────
WScript.Sleep 4000
WshShell.Run "http://127.0.0.1:" & strPort & "/", 1, False

Set fso = Nothing
Set WshShell = Nothing
