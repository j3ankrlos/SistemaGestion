"""Verificar drivers ODBC disponibles"""
import pyodbc

todos = pyodbc.drivers()
print("Todos los drivers ODBC instalados:")
for d in todos:
    print(f"  - {d}")

access = [d for d in todos if 'access' in d.lower() or 'ace' in d.lower() or 'excel' in d.lower()]
print(f"\nDrivers Access/ACE/Excel ({len(access)}):")
for d in access:
    print(f"  ✓ {d}")

if not access:
    print("\n⚠ NO HAY driver de Microsoft Access instalado.")
    print("  Descarga e instala: https://aka.ms/accessdatabasengine")
    print("  (AccessDatabaseEngine.exe /quiet si no tienes admin)")
