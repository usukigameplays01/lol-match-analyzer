# lol-match-analyzer

Analizador de partidas de League of Legends que usa la API oficial de Riot Games. Consulta el historial de un jugador, guarda las partidas en una base de datos local y calcula estadísticas como el winrate y el KDA promedio por campeón.

## Qué hace

- Busca una cuenta por Riot ID (`Nombre#Tag`) y obtiene su `puuid`.
- Descarga las últimas partidas con la API MATCH-V5.
- Guarda cada partida en una base de datos SQLite, sin duplicar las que ya existen.
- Excluye de las estadísticas las partidas muy cortas (remakes, menos de 5 minutos).
- Muestra una tabla con partidas, victorias, winrate y KDA promedio por campeón.

## Requisitos

- Python 3.9 o superior
- Una cuenta de Riot Games
- Una clave de desarrollo de la API de Riot (gratuita) desde [developer.riotgames.com](https://developer.riotgames.com)

## Instalación

```bash
git clone https://github.com/usukigameplays01/lol-match-analyzer.git
cd lol-match-analyzer
pip install requests python-dotenv
```

En Windows, si el comando `python` no funciona, usa `py` en su lugar (por ejemplo `py -m pip install requests python-dotenv`).

## Configuración

Crea un archivo `.env` en la raíz del proyecto con tu clave de la API:

```
RIOT_API_KEY=RGAPI-tu-clave-aqui
```

Notas importantes:

- Sin comillas y sin espacios alrededor del `=`.
- Las claves de desarrollo **expiran cada 24 horas**: hay que regenerarla en el portal de desarrolladores y actualizar esa línea.
- El archivo `.env` está en el `.gitignore` y nunca debe subirse al repositorio.

## Uso

```bash
python main.py
```

El programa te pide tu Riot ID en dos partes. Si tu Riot ID es `Usuki#L01`:

```
Nombre (lo que va antes del #): Usuki
Tag (lo que va después del #): L01
```

Ejemplo de salida:

```
Partidas nuevas guardadas: 20 | Total en la base: 20

Campeón       Partidas  Victorias  Winrate  KDA promedio
Yunara        3         2          66.7     4.7/6.3/6.7
Zeri          3         2          66.7     10.7/5.3/12.0
...
```

Si lo ejecutas de nuevo, solo descarga las partidas nuevas, así que es mucho más rápido y gasta menos peticiones.

## Cómo funciona

1. `ACCOUNT-V1` convierte el Riot ID en un `puuid`.
2. `MATCH-V5` devuelve los IDs de las últimas partidas y el detalle de cada una.
3. Se extraen los datos del jugador (campeón, kills, muertes, asistencias, resultado, duración, modo y fecha).
4. Todo se guarda en `partidas.db` (SQLite) y las estadísticas se calculan con consultas SQL.

El programa hace una pausa entre peticiones para respetar los límites de la clave de desarrollo (20 solicitudes por segundo y 100 cada 2 minutos).

## Estructura

```
lol-match-analyzer/
├── main.py        # script principal
├── partidas.db    # base de datos local (se crea sola, no se sube a Git)
├── .env           # tu clave de la API (no se sube a Git)
├── .gitignore
└── README.md
```

## Próximos pasos

- [ ] Separar las estadísticas por modo de juego (ARAM, clasificatoria, normal).
- [ ] Más métricas: daño, oro, visión y farmeo por minuto.
- [ ] Exponer las estadísticas con una API propia (FastAPI).
- [ ] Migrar a PostgreSQL y desplegar con Docker.
- [ ] Pruebas automáticas.

## Aviso legal

Este proyecto no está respaldado por Riot Games ni refleja las opiniones de Riot Games ni de nadie oficialmente involucrado en producir o gestionar League of Legends. League of Legends y Riot Games son marcas registradas de Riot Games, Inc.
