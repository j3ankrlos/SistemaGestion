"""Script único para actualizar los permisos en la BD:
- Elimina permisos huérfanos (módulos que ya no existen)
- Agrega permisos faltantes (módulos existentes sin permisos)
"""
import pyodbc

import json, os

# Leer ruta desde config.json
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, "..", "config.json")
with open(config_path) as f:
    config = json.load(f)
DB_PATH = config["db_path"]

DRIVER = "Microsoft Access Driver (*.mdb, *.accdb)"
conn_str = f"DRIVER={{{DRIVER}}};DBQ={DB_PATH};"
conn = pyodbc.connect(conn_str, timeout=10)
print(f"Conectado a: {DB_PATH}")
c = conn.cursor()

# ─── 1) MÓDULOS QUE EXISTEN EN EL CÓDIGO (blueprints registrados en app.py) ───
MODULOS_REALES = {'usuarios', 'roles', 'permisos', 'configuracion', 'personal'}

# ─── 2) ELIMINAR PERMISOS DE MÓDULOS QUE YA NO EXISTEN ───
c.execute("SELECT DISTINCT Modulo FROM Permisos")
modulos_en_bd = {r[0] for r in c.fetchall()}
modulos_huérfanos = modulos_en_bd - MODULOS_REALES

for mod in modulos_huérfanos:
    # Eliminar relaciones primero
    c.execute("DELETE FROM Permiso_Rol WHERE Fk_IdPermiso IN (SELECT IdPermiso FROM Permisos WHERE Modulo = ?)", (mod,))
    rel_elim = c.rowcount
    c.execute("DELETE FROM Permisos WHERE Modulo = ?", (mod,))
    perm_elim = c.rowcount
    print(f"  ✗ Eliminado módulo '{mod}': {perm_elim} permiso(s) y {rel_elim} relación(es)")

# ─── 3) AGREGAR PERMISOS FALTANTES PARA MÓDULOS EXISTENTES ───
permisos_requeridos = {
    'usuarios': [
        ('ver', 'usuarios.ver'),
        ('crear', 'usuarios.crear'),
        ('editar', 'usuarios.editar'),
        ('eliminar', 'usuarios.eliminar'),
        ('desactivar', 'usuarios.desactivar'),
    ],
    'roles': [
        ('ver', 'roles.ver'),
        ('crear', 'roles.crear'),
        ('editar', 'roles.editar'),
        ('eliminar', 'roles.eliminar'),
    ],
    'permisos': [
        ('ver', 'permisos.ver'),
        ('editar', 'permisos.editar'),
    ],
    'configuracion': [
        ('ver', 'configuracion.ver'),
        ('editar', 'configuracion.editar'),
    ],
    'personal': [
        ('ver', 'personal.ver'),
        ('crear', 'personal.crear'),
        ('editar', 'personal.editar'),
        ('eliminar', 'personal.eliminar'),
    ],
}

c.execute("SELECT Slug FROM Permisos")
slugs_existentes = {r[0] for r in c.fetchall()}

agregados = []
for modulo, acciones in permisos_requeridos.items():
    for accion, slug in acciones:
        if slug not in slugs_existentes:
            c.execute(
                "INSERT INTO Permisos (Modulo, Accion, Slug) VALUES (?, ?, ?)",
                (modulo, accion, slug)
            )
            agregados.append(slug)
            print(f"  + Agregado: {slug}")

if not agregados:
    print("  ✓ Todos los permisos ya existen")

conn.commit()

# ─── 4) MOSTRAL RESULTADO FINAL ───
print()
print("═══ PERMISOS ACTUALIZADOS ═══")
print(f"{'ID':>3}  {'Módulo':<20} {'Acción':<25} {'Slug'}")
print("─" * 70)
for r in c.execute("SELECT IdPermiso, Modulo, Accion, Slug FROM Permisos ORDER BY Modulo, Accion"):
    print(f"  {r[0]:>3}  {r[1]:<20} {r[2]:<25} {r[3]}")

print()
print("═══ ASIGNACIONES POR ROL ═══")
for r in c.execute("""
    SELECT rl.Rol, p.Modulo, p.Accion
    FROM (Permiso_Rol pr
    INNER JOIN Roles rl ON pr.Fk_IdRol = rl.IdRol)
    INNER JOIN Permisos p ON pr.Fk_IdPermiso = p.IdPermiso
    ORDER BY rl.IdRol, p.Modulo, p.Accion
"""):
    print(f"  {r[0]:<15} → {r[1]:<20} {r[2]}")

conn.close()
