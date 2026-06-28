# Sistema Porcino — Guía de Instalación Portable

> **Sin permisos de administrador · Sin internet en la PC destino**

---

## Qué necesitas en la PC destino

| Requisito | ¿Cómo obtenerlo? | ¿Necesita admin? |
|---|---|---|
| Python 3.8 o superior | https://www.python.org/downloads/ — marca "Add Python to PATH" | ❌ No (instalar solo para el usuario) |
| Microsoft Office | Ya instalado | — |
| La carpeta del proyecto | Copiar desde USB/red | ❌ No |

> **Si Office está instalado, el driver de Access ya funciona.** No hace falta instalar nada extra.

---

## Pasos (en la PC que SÍ tiene internet — la tuya)

### 1. Copiar la base de datos al proyecto

Tu base de datos está **fuera** del proyecto. Debes copiarla adentro:

```
Origen:   C:\Users\jean.gonzalez\Desktop\Recursos\DB\DBSistema.accdb
Destino:  SistemaPorcino\database\DBSistema.accdb
```

**Copia el archivo `.accdb` dentro de la carpeta `database\` del proyecto.**

### 2. Descargar paquetes para uso offline

Haz doble clic en:

```
descargar_paquetes.bat
```

Esto crea una carpeta `wheels\` con todos los paquetes Python necesarios.  
Tarda 1-3 minutos. Solo necesitas hacerlo una vez.

### 3. Copiar la carpeta completa a la otra PC

Copia **toda** la carpeta `SistemaPorcino\` a la otra computadora (USB, red, etc.).  
Debe incluir:
- `wheels\` ← paquetes pip offline
- `database\DBSistema.accdb` ← tu base de datos
- `requirements.txt`, `app.py`, `config.json`, etc.

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

*Sistema Porcino — Instalación portable sin admin*
