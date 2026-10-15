"""Copia las partidas de partidas.db (SQLite) a PostgreSQL. Se ejecuta una sola vez."""
import os
import sqlite3

from database import init_db, match_exists, save_match

SQLITE_PATH = "partidas.db"

if not os.path.exists(SQLITE_PATH):
    raise SystemExit(f"No se encontró {SQLITE_PATH}. Ejecuta este script desde la carpeta del proyecto.")

origen = sqlite3.connect(SQLITE_PATH)
origen.row_factory = sqlite3.Row
filas = origen.execute("SELECT * FROM partidas").fetchall()
origen.close()

destino = init_db()
migradas = 0
for fila in filas:
    datos = dict(fila)
    if match_exists(destino, datos["match_id"]):
        continue
    save_match(destino, datos["match_id"], datos)
    migradas += 1

total = destino.execute("SELECT COUNT(*) FROM partidas").fetchone()[0]
destino.close()
print(f"Partidas migradas: {migradas} | Total en PostgreSQL: {total}")
