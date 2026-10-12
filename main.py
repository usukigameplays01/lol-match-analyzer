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

# Nombres legibles para las colas (queueId) más comunes. Las demás salen como "Cola <id>".
COLAS = {
    400: "Normal (draft)",
    420: "Clasificatoria solo/duo",
    430: "Normal (ciega)",
    440: "Clasificatoria flex",
    450: "ARAM",
    480: "Swiftplay",
    490: "Normal (quickplay)",
    700: "Clash",
    1700: "Arena",
    1900: "URF",
}

if not API_KEY:
    raise SystemExit("No se encontró RIOT_API_KEY. Revisa el archivo .env")


def nombre_cola(queue_id):
    return COLAS.get(queue_id, f"Cola {queue_id}")


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
                "queue_id": info["queueId"],
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
            queue_id INTEGER,
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
        """
        INSERT OR IGNORE INTO partidas
            (match_id, campeon, kills, deaths, assists, win, duracion_min, modo, queue_id, fecha)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (match_id, r["campeon"], r["kills"], r["deaths"], r["assists"],
         r["win"], r["duracion_min"], r["modo"], r["queue_id"], r["fecha"]),
    )
    conn.commit()


def resumen_por_cola(conn):
    """Una fila por tipo de partida: total, victorias, winrate y KDA promedio."""
    return conn.execute(
        """
        SELECT queue_id,
               COUNT(*),
               SUM(win),
               ROUND(100.0 * SUM(win) / COUNT(*), 1),
               ROUND(AVG(kills), 1), ROUND(AVG(deaths), 1), ROUND(AVG(assists), 1)
        FROM partidas
        WHERE duracion_min >= ?
        GROUP BY queue_id
        ORDER BY COUNT(*) DESC
        """,
        (MIN_DURACION,),
    ).fetchall()


def campeones_de_cola(conn, queue_id):
    return conn.execute(
        """
        SELECT campeon,
               COUNT(*),
               SUM(win),
               ROUND(100.0 * SUM(win) / COUNT(*), 1),
               ROUND(AVG(kills), 1), ROUND(AVG(deaths), 1), ROUND(AVG(assists), 1)
        FROM partidas
        WHERE queue_id = ? AND duracion_min >= ?
        GROUP BY campeon
        ORDER BY COUNT(*) DESC, 4 DESC
        """,
        (queue_id, MIN_DURACION),
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
    print(f"\nPartidas nuevas guardadas: {nuevas} | Total en la base: {total}")

    for queue_id, n, v, wr, k, d, a in resumen_por_cola(conn):
        print(f"\n=== {nombre_cola(queue_id)} ===")
        print(f"{n} partidas | {v} victorias | winrate {wr}% | KDA promedio {k}/{d}/{a}\n")
        print(f'{"Campeón":<14}{"Partidas":<10}{"Victorias":<11}{"Winrate":<9}KDA promedio')
        for camp, cn, cv, cwr, ck, cd, ca in campeones_de_cola(conn, queue_id):
            print(f"{camp:<14}{cn:<10}{cv:<11}{cwr:<9}{ck}/{cd}/{ca}")
    conn.close()
