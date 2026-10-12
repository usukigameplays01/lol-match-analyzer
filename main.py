import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("RIOT_API_KEY")
BASE_URL = "https://americas.api.riotgames.com"

if not API_KEY:
    raise SystemExit("No se encontró RIOT_API_KEY. Revisa el archivo .env")


def riot_get(path, params=None):
    """Hace una petición a la API de Riot y devuelve el JSON."""
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


def get_match_ids(puuid, count=10):
    return riot_get(f"/lol/match/v5/matches/by-puuid/{puuid}/ids", {"start": 0, "count": count})


def get_match(match_id):
    return riot_get(f"/lol/match/v5/matches/{match_id}")


def summarize_match(match, puuid):
    """Busca al jugador dentro de la partida y devuelve sus datos clave."""
    info = match["info"]
    for player in info["participants"]:
        if player["puuid"] == puuid:
            return {
                "campeon": player["championName"],
                "kda": f'{player["kills"]}/{player["deaths"]}/{player["assists"]}',
                "resultado": "Victoria" if player["win"] else "Derrota",
                "duracion_min": round(info["gameDuration"] / 60, 1),
                "modo": info["gameMode"],
            }
    return None


if __name__ == "__main__":
    nombre = input("Nombre (lo que va antes del #): ").strip()
    tag = input("Tag (lo que va después del #): ").strip()

    puuid = get_puuid(nombre, tag)
    match_ids = get_match_ids(puuid, count=10)
    print(f"\nSe encontraron {len(match_ids)} partidas:\n")

    for match_id in match_ids:
        resumen = summarize_match(get_match(match_id), puuid)
        if resumen:
            print(
                f'{match_id} | {resumen["campeon"]:<12} | {resumen["kda"]:<8} | '
                f'{resumen["resultado"]:<8} | {resumen["duracion_min"]} min | {resumen["modo"]}'
            )
        time.sleep(0.5)  # pausa para no pasar el límite de la clave