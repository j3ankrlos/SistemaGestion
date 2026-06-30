Option Explicit

Dim WshShell, fso, strBase, strCmd, strKillCmd, strPort, strPython, strSetupPy, strSep, strNoVenv

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Obtiene la carpeta donde está guardado este archivo VBS
strBase = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strBase

' Separador de rutas
strSep = "\"

' ──────────────────────────────────────────────
'  CONFIGURACIÓN
' ──────────────────────────────────────────────
strPort    = "5001"
strPython  = strBase & "\venv\Scripts\python.exe"
strSetupPy = strBase & "\setup_portable.py"
strNoVenv  = strBase & "\.no_venv"       ' Marcador: modo sin venv activo

' ═══════════════════════════════════════════════
'  FUNCIÓN: Verificar si Python está en el PATH
' ═══════════════════════════════════════════════
Function SystemPythonExists()
    Dim exitCode
    exitCode = WshShell.Run("cmd /c python --version >nul 2>&1", 0, True)
    SystemPythonExists = (exitCode = 0)
End Function

' ═══════════════════════════════════════════════
'  FUNCIÓN: Verificar si el venv es usable
' ═══════════════════════════════════════════════
Function VenvIsUsable()
    If Not fso.FileExists(strPython) Then
        VenvIsUsable = False
        Exit Function
    End If
    Dim exitCode
    exitCode = WshShell.Run("cmd /c """ & strPython & """ --version >nul 2>&1", 0, True)
    VenvIsUsable = (exitCode = 0)
End Function

' ═══════════════════════════════════════════════
'  FUNCIÓN: Forzar una ventana de consola visible
'  para que el usuario vea el progreso del setup
' ═══════════════════════════════════════════════
Sub RunVisible(cmd)
    ' 1 = ventana normal (visible), True = esperar a que termine
    WshShell.Run "cmd /c " & cmd, 1, True
End Sub

' ═══════════════════════════════════════════════
'  1) VERIFICAR QUE EXISTA PYTHON EN EL SISTEMA
' ═══════════════════════════════════════════════
If Not SystemPythonExists() Then
    MsgBox "Python no está instalado o no está en el PATH." & vbCrLf & vbCrLf & _
           "Para usar este sistema necesitas instalar Python." & vbCrLf & vbCrLf & _
           "Descárgalo GRATIS desde:" & vbCrLf & _
           "  https://www.python.org/downloads/" & vbCrLf & vbCrLf & _
           "IMPORTANTE: Al instalar, MARCA la opción:" & vbCrLf & _
           "  'Add Python to PATH'" & vbCrLf & vbCrLf & _
           "NO necesitas permisos de administrador." & vbCrLf & _
           "Elige 'Install for all users' = NO (solo para ti).", _
           vbExclamation, "Sistema de Gestión - Falta Python"
    WScript.Quit 1
End If

' ═══════════════════════════════════════════════
'  2) DETECTAR VENV OBSOLETO (de otra computadora)
' ═══════════════════════════════════════════════
If fso.FileExists(strPython) Then
    If Not VenvIsUsable() Then
        ' El venv es de otra máquina: eliminarlo para que se recree
        WshShell.Run "cmd /c rmdir /s /q """ & strBase & "\venv""", 0, True
    End If
End If

' ═══════════════════════════════════════════════
'  3) VERIFICAR ENTORNO: si no hay venv, ejecutar setup
' ═══════════════════════════════════════════════
If Not fso.FileExists(strPython) And Not fso.FileExists(strNoVenv) Then
    If fso.FileExists(strSetupPy) Then
        ' Mostrar ventana de consola para que el usuario vea el progreso
        RunVisible "python """ & strSetupPy & """"
        ' Verificar si el setup activó modo sin venv
        If Not VenvIsUsable() And Not fso.FileExists(strNoVenv) Then
            MsgBox "El setup no pudo preparar el entorno." & vbCrLf & vbCrLf & _
                   "Posibles causas:" & vbCrLf & _
                   "  - Antivirus bloqueando" & vbCrLf & _
                   "  - Permisos de Python insuficientes" & vbCrLf & vbCrLf & _
                   "Abre una terminal en la carpeta del proyecto y ejecuta:" & vbCrLf & _
                   "  python setup_portable.py" & vbCrLf & _
                   "(así verás el error detallado)", _
                   vbExclamation, "Sistema de Gestión - Error de entorno"
            WScript.Quit 1
        End If
    Else
        MsgBox "No se encuentra el script de setup (setup_portable.py)." & vbCrLf & _
               "Asegúrate de que la carpeta del proyecto esté completa.", _
               vbCritical, "Sistema de Gestión - Error"
        WScript.Quit 1
    End If
End If

' ═══════════════════════════════════════════════
'  4) ELEGIR PYTHON: venv o sistema
' ═══════════════════════════════════════════════
If fso.FileExists(strNoVenv) Then
    ' Modo sin venv — usar python del sistema
    strPython = "python"
End If
' Si no, strPython ya apunta a venv\Scripts\python.exe

' ═══════════════════════════════════════════════
'  5) LIBERAR PUERTO: mata procesos zombies en el puerto
' ═══════════════════════════════════════════════
strKillCmd = "cmd /c netstat -ano | findstr :" & strPort & " > ""%TEMP%\gestion_port.txt"" & for /f ""tokens=5"" %a in ('findstr LISTENING ""%TEMP%\gestion_port.txt""') do taskkill /F /PID %a 2>nul"
WshShell.Run strKillCmd, 0, True
WScript.Sleep 1000

' ═══════════════════════════════════════════════
'  6) INICIAR SERVIDOR (ventana oculta)
' ═══════════════════════════════════════════════
strCmd = """" & strPython & """ """ & strBase & "\app.py"""
WshShell.Run strCmd, 0, False

' ═══════════════════════════════════════════════
'  7) ESPERAR Y ABRIR NAVEGADOR EN EL PUERTO REAL
' ═══════════════════════════════════════════════
WScript.Sleep 5000

' Leer el puerto real desde el archivo que escribe app.py
Dim strPortFile, strActualPort
strPortFile = strBase & "\.actual_port"
If fso.FileExists(strPortFile) Then
    Dim ts
    Set ts = fso.OpenTextFile(strPortFile, 1)
    strActualPort = ts.ReadLine
    ts.Close
Else
    strActualPort = strPort ' fallback al configurado
End If

WshShell.Run "http://127.0.0.1:" & strActualPort & "/", 1, False

Set fso = Nothing
Set WshShell = Nothing
