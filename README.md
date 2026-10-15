# lol-match-analyzer

Analizador de partidas de League of Legends que usa la API oficial de Riot Games. Descarga el historial de un jugador, lo guarda en PostgreSQL y expone estadísticas (winrate y KDA por tipo de partida y por campeón) mediante una API propia hecha con FastAPI. Todo se levanta con Docker Compose.

## Qué hace

- Busca una cuenta por Riot ID (`Nombre#Tag`) y obtiene su `puuid` (ACCOUNT-V1).
- Descarga las últimas partidas (MATCH-V5) y las guarda en PostgreSQL, sin duplicar las que ya existen.
- Separa las estadísticas por tipo de partida (clasificatoria, ARAM, normales...) para que no se mezclen.
- Excluye de las estadísticas las partidas de menos de 5 minutos (remakes).
- Expone los resultados en JSON mediante una API REST con documentación automática.

## Requisitos

- Python 3.9 o superior
- Docker Desktop (para PostgreSQL y la API)
- Una cuenta de Riot Games
- Una clave de desarrollo de la API de Riot (gratuita) desde [developer.riotgames.com](https://developer.riotgames.com)

## Instalación

```bash
git clone https://github.com/usukigameplays01/lol-match-analyzer.git
cd lol-match-analyzer
pip install -r requirements.txt
```

En Windows, si el comando `python` no funciona, usa `py` (por ejemplo `py -m pip install -r requirements.txt`).

## Configuración

Crea un archivo `.env` en la raíz del proyecto con tu clave de la API de Riot:

```
RIOT_API_KEY=RGAPI-tu-clave-aqui
```

- Sin comillas y sin espacios alrededor del `=`.
- Las claves de desarrollo **expiran cada 24 horas**: hay que regenerarla en el portal de desarrolladores y actualizar esa línea.
- `.env` está en el `.gitignore` y nunca debe subirse al repositorio.

Opcional: `DATABASE_URL` define la conexión a PostgreSQL. Por defecto apunta al contenedor local de `docker-compose.yml` (`postgresql://lol:lol@localhost:5432/lol`). Esas credenciales son solo para desarrollo local.

## Uso

### 1. Levantar PostgreSQL

```bash
docker compose up -d db
```

### 2. Descargar y guardar partidas

```bash
python main.py
```

Pide tu Riot ID en dos partes (si es `Usuki#L01`, el nombre es `Usuki` y el tag `L01`), guarda las partidas nuevas e imprime las estadísticas:

```
Partidas nuevas guardadas: 20 | Total en la base: 20

=== Clasificatoria solo/duo ===
17 partidas | 7 victorias | winrate 41.2% | KDA promedio 6.2/6.2/8.6

Campeón       Partidas  Victorias  Winrate  KDA promedio
Yunara        3         2          66.7     4.7/6.3/6.7
...
```

Si lo ejecutas de nuevo, solo descarga las partidas nuevas.

### 3. Levantar la API

Todo junto (API + base de datos) con Docker Compose:

```bash
docker compose up --build
```

O solo la API en local, con la base ya encendida:

```bash
python -m uvicorn api:app --reload
```

La API queda en `http://127.0.0.1:8000`. Solo lee la base de datos, así que no necesita la clave de Riot. La documentación interactiva está en `http://127.0.0.1:8000/docs`.

| Endpoint | Descripción |
|---|---|
| `GET /` | Información general y lista de endpoints |
| `GET /estadisticas` | Resumen por tipo de partida: total, victorias, winrate y KDA promedio |
| `GET /campeones/{queue_id}` | Detalle por campeón dentro de un tipo de partida (por ejemplo `420` = clasificatoria solo/duo) |
| `GET /partidas?limit=10` | Últimas partidas guardadas (entre 1 y 100) |

Ejemplo de respuesta de `/estadisticas`:

```json
[
  {
    "queue_id": 420,
    "cola": "Clasificatoria solo/duo",
    "partidas": 17,
    "victorias": 7,
    "winrate": 41.2,
    "kills_prom": 6.2,
    "muertes_prom": 6.2,
    "asistencias_prom": 8.6
  }
]
```

Para apagar todo conservando los datos: `docker compose down`. (`docker compose down -v` también borra la base de datos.)

## Pruebas

Las pruebas necesitan PostgreSQL encendido (`docker compose up -d db`):

```bash
python -m pytest -v
```

Cada prueba crea un esquema temporal que se elimina al terminar, así que nunca tocan los datos reales ni la API de Riot.

## Estructura

```
lol-match-analyzer/
├── main.py              # descarga partidas desde Riot y las guarda
├── database.py          # acceso a PostgreSQL y consultas de estadísticas
├── api.py               # API REST con FastAPI
├── test_database.py     # pruebas con pytest
├── migrar_sqlite.py     # migración única desde la versión antigua con SQLite
├── Dockerfile           # imagen de la API
├── docker-compose.yml   # API + PostgreSQL
├── requirements.txt     # dependencias
├── .env                 # tu clave de Riot (no se sube a Git)
├── .gitignore
└── README.md
```

## Decisiones de diseño

- **Sin duplicados:** el `match_id` es la clave primaria, se usa `ON CONFLICT DO NOTHING` y antes de pedir una partida se comprueba si ya está guardada, lo que ahorra peticiones.
- **Límites de la API:** la clave de desarrollo permite 20 solicitudes por segundo y 100 cada 2 minutos, por eso hay una pausa entre peticiones.
- **Separación de responsabilidades:** la lógica de datos vive en `database.py` y la comparten el script de descarga y la API. Cambiar de SQLite a PostgreSQL no requirió tocar `main.py` ni `api.py`.
- **Una conexión por petición** en la API, abierta y cerrada dentro de cada endpoint.
- **Pruebas aisladas:** esquemas temporales de PostgreSQL por prueba, para no depender del estado de la base.

## Próximos pasos

- [ ] Más métricas: daño, oro, visión y farmeo por minuto.
- [ ] Separar estadísticas por rol y por versión del juego.
- [ ] Desplegar en la nube con una base de datos PostgreSQL gestionada.
- [ ] Integración continua (GitHub Actions) para correr las pruebas en cada push.

## Aviso legal

Este proyecto no está respaldado por Riot Games ni refleja las opiniones de Riot Games ni de nadie oficialmente involucrado en producir o gestionar League of Legends. League of Legends y Riot Games son marcas registradas de Riot Games, Inc.
