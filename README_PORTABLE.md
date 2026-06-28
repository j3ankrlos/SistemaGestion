# Sistema de Gestión — Guía de Instalación Portable

> **Sin permisos de administrador · Sin internet en la PC destino**

---

## Requisitos en la PC destino

| Requisito | ¿Cómo obtenerlo? | ¿Necesita admin? |
|---|---|---|
| Python 3.8 o superior | https://www.python.org/downloads/ — marca "Add Python to PATH" | ❌ No |
| Microsoft Access Driver | Viene con Microsoft Office | ❌ No |
| La carpeta del proyecto | Git clone o copiar desde USB | ❌ No |

---

## Modo RÁPIDO (recomendado)

### 1. Clonar o copiar el proyecto

```bash
git clone https://github.com/j3ankrlos/SistemaGestion.git
cd SistemaGestion
```

### 2. Ejecutar el sistema

Haz **doble clic** en:

```
iniciar_sistema.vbs
```

> **¿Qué hace automáticamente?**
> 1. ✅ Verifica que Python esté instalado
> 2. ✅ Crea el entorno virtual (venv) si no existe
> 3. ✅ Instala dependencias desde `wheels\` (sin internet) o desde internet
> 4. ✅ Verifica el driver ODBC de Microsoft Access
> 5. ✅ Inicia el servidor y abre el navegador

### 3. Configurar la base de datos (solo la primera vez)

Al abrir el sistema por primera vez, verás una pantalla de **configuración**.
Presiona **"Buscar"** y selecciona tu archivo `.accdb` desde cualquier carpeta.

---

## Modo manual (alternativa)

```bash
cd SistemaGestion
python setup_portable.py
python app.py
```

Luego abre http://localhost:5000

---

## Si no tienes Python instalado

Descárgalo gratis desde: https://www.python.org/downloads/

**Importante al instalar:** marca la opción **"Add Python to PATH"**.
NO necesitas permisos de administrador (elige "Install for all users" = NO).

> ⚠️ **NO copies la carpeta `venv\`** — si la copias, el sistema la detectará como inválida
> y la recreará automáticamente. Mejor no copiarla para ahorrar espacio.

---

## Pasos (en la PC destino — sin internet)

### 4. Primera vez: doble clic en `iniciar_sistema.vbs`

Al iniciar por primera vez:
1. El sistema detecta que no hay entorno virtual
2. Crea el entorno virtual automáticamente (`venv\`)
3. Instala los paquetes desde la carpeta `wheels\` (sin internet)
4. Abre el navegador en `http://localhost:5000`

**El proceso puede tardar 1-2 minutos la primera vez.**  
Las siguientes veces inicia en segundos.

### 5. Configurar la ruta de la base de datos (si es necesario)

Si el sistema dice que no encuentra la base de datos:
1. Abre el navegador en `http://localhost:5000`
2. Ve a **Configuración → Base de Datos**
3. Escribe la ruta donde está el archivo `.accdb`

---

## Estructura final del proyecto

```
SistemaPorcino\
├── database\
│   └── DBSistema.accdb        ← tu base de datos (copiada aquí)
├── wheels\                     ← paquetes pip offline
│   ├── Flask-3.x.whl
│   ├── pyodbc-5.x.whl
│   └── ...
├── venv\                       ← se crea automáticamente (no copiar)
├── app.py
├── config.json                 ← apunta a ./database/DBSistema.accdb
├── iniciar_sistema.vbs         ← doble clic para iniciar
├── run.bat                     ← alternativa por terminal
└── descargar_paquetes.bat      ← ejecutar en PC con internet
```

---

## Solución de problemas

### "Python no encontrado"
- Instala Python desde https://www.python.org/downloads/
- **Marca la casilla "Add Python to PATH"** durante la instalación
- Reinicia el sistema después de instalar

### "No se detecta driver Microsoft Access"
- Si tienes Microsoft Office instalado: el driver ya debería funcionar. Reinicia el PC.
- Si no tienes Office: necesitarás que un administrador instale el "Microsoft Access Database Engine" desde https://aka.ms/accessdatabasengine

### "Error al conectar a la base de datos"
- Verifica que el archivo `database\DBSistema.accdb` existe dentro de la carpeta del proyecto
- O ve a Configuración → Base de Datos en la interfaz web y corrige la ruta

### El sistema tarda en iniciar la primera vez
- Normal: está creando el entorno virtual e instalando paquetes desde `wheels\`
- Las siguientes veces será instantáneo

---

*Sistema de Gestión — Instalación portable sin admin*
