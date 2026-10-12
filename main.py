import os
import sqlite3
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("RIOT_API_KEY")
BASE_URL = "https://americas.api.riotgames.com"
DB_PATH = "partidas.db"
MIN_DURACION = 5  # minutos; las partidas más cortas (remakes) no cuentan en las estadísticas

if not API_KEY:
    raise SystemExit("No se encontró RIOT_API_KEY. Revisa el archivo .env")


# ---------- API de Riot ----------
def riot_get(path, params=None):
    response = requests.get(
        f"{BASE_URL}{path}",
        headers={"X-Riot-Token": API_KEY},
        params=params,
        timeout=10,
    )
    if not response.ok:
        raise SystemExit(f"Error {response.status_code}: {response.text}")
    return response.json()


def get_puuid(game_name, tag_line):
    data = riot_get(f"/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}")
    return data["puuid"]


def get_match_ids(puuid, count=20):
    return riot_get(f"/lol/match/v5/matches/by-puuid/{puuid}/ids", {"start": 0, "count": count})


def get_match(match_id):
    return riot_get(f"/lol/match/v5/matches/{match_id}")


def summarize_match(match, puuid):
    info = match["info"]
    for p in info["participants"]:
        if p["puuid"] == puuid:
            return {
                "campeon": p["championName"],
                "kills": p["kills"],
                "deaths": p["deaths"],
                "assists": p["assists"],
                "win": int(p["win"]),
                "duracion_min": round(info["gameDuration"] / 60, 1),
                "modo": info["gameMode"],
                "fecha": datetime.fromtimestamp(info["gameCreation"] / 1000).isoformat(timespec="minutes"),
            }
    return None


# ---------- Base de datos ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS partidas (
            match_id TEXT PRIMARY KEY,
            campeon TEXT,
            kills INTEGER,
            deaths INTEGER,
            assists INTEGER,
            win INTEGER,
            duracion_min REAL,
            modo TEXT,
            fecha TEXT
        )
        """
    )
    return conn


def match_exists(conn, match_id):
    row = conn.execute("SELECT 1 FROM partidas WHERE match_id = ?", (match_id,)).fetchone()
    return row is not None


def save_match(conn, match_id, r):
    conn.execute(
        "INSERT OR IGNORE INTO partidas VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (match_id, r["campeon"], r["kills"], r["deaths"], r["assists"],
         r["win"], r["duracion_min"], r["modo"], r["fecha"]),
    )
    conn.commit()


def winrate_por_campeon(conn):
    return conn.execute(
        """
        SELECT campeon,
               COUNT(*) AS partidas,
               SUM(win) AS victorias,
               ROUND(100.0 * SUM(win) / COUNT(*), 1) AS winrate,
               ROUND(AVG(kills), 1), ROUND(AVG(deaths), 1), ROUND(AVG(assists), 1)
        FROM partidas
        WHERE duracion_min >= ?
        GROUP BY campeon
        ORDER BY partidas DESC, winrate DESC
        """,
        (MIN_DURACION,),
    ).fetchall()


# ---------- Programa principal ----------
if __name__ == "__main__":
    nombre = input("Nombre (lo que va antes del #): ").strip()
    tag = input("Tag (lo que va después del #): ").strip()

    conn = init_db()
    puuid = get_puuid(nombre, tag)
    match_ids = get_match_ids(puuid, count=20)

    nuevas = 0
    for match_id in match_ids:
        if match_exists(conn, match_id):
            continue  # ya la tenemos, no gastamos peticiones
        resumen = summarize_match(get_match(match_id), puuid)
        if resumen:
            save_match(conn, match_id, resumen)
            nuevas += 1
        time.sleep(0.5)  # pausa para respetar el límite de la clave

    total = conn.execute("SELECT COUNT(*) FROM partidas").fetchone()[0]
    print(f"\nPartidas nuevas guardadas: {nuevas} | Total en la base: {total}\n")

    print(f'{"Campeón":<14}{"Partidas":<10}{"Victorias":<11}{"Winrate":<9}KDA promedio')
    for camp, n, v, wr, k, d, a in winrate_por_campeon(conn):
        print(f"{camp:<14}{n:<10}{v:<11}{wr:<9}{k}/{d}/{a}")
    conn.close()