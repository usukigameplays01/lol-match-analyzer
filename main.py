import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("RIOT_API_KEY")
BASE_URL = "https://americas.api.riotgames.com"

if not API_KEY:
    raise SystemExit("No se encontró RIOT_API_KEY. Revisa el archivo .env")


def get_puuid(game_name, tag_line):
    url = f"{BASE_URL}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    response = requests.get(url, headers={"X-Riot-Token": API_KEY}, timeout=10)
    if not response.ok:
        raise SystemExit(f"Error {response.status_code}: {response.text}")
    return response.json()["puuid"]


if __name__ == "__main__":
    nombre = input("Nombre (lo que va antes del #): ").strip()
    tag = input("Tag (lo que va después del #): ").strip()
    puuid = get_puuid(nombre, tag)
    print("Tu puuid es:", puuid)