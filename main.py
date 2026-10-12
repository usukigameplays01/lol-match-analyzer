"""Descarga las partidas de un jugador desde la API de Riot y las guarda en la base de datos."""
import os
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

from database import (
    campeones_de_cola,
    init_db,
    match_exists,
    resumen_por_cola,
    save_match,
)

load_dotenv()
API_KEY = os.getenv("RIOT_API_KEY")
BASE_URL = "https://americas.api.riotgames.com"

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
                "queue_id": info["queueId"],
                "fecha": datetime.fromtimestamp(info["gameCreation"] / 1000).isoformat(timespec="minutes"),
            }
    return None


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

    for cola in resumen_por_cola(conn):
        print(f"\n=== {cola['cola']} ===")
        print(
            f"{cola['partidas']} partidas | {cola['victorias']} victorias | "
            f"winrate {cola['winrate']}% | KDA promedio "
            f"{cola['kills_prom']}/{cola['muertes_prom']}/{cola['asistencias_prom']}\n"
        )
        print(f'{"Campeón":<14}{"Partidas":<10}{"Victorias":<11}{"Winrate":<9}KDA promedio')
        for c in campeones_de_cola(conn, cola["queue_id"]):
            kda = f"{c['kills_prom']}/{c['muertes_prom']}/{c['asistencias_prom']}"
            print(f"{c['campeon']:<14}{c['partidas']:<10}{c['victorias']:<11}{c['winrate']:<9}{kda}")
    conn.close()
