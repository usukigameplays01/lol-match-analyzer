# lol-match-analyzer

Analizador de partidas de League of Legends que usa la API oficial de Riot Games. Descarga el historial de un jugador, lo guarda en una base de datos local y expone estadísticas (winrate y KDA por tipo de partida y por campeón) mediante una API propia hecha con FastAPI.

## Qué hace

- Busca una cuenta por Riot ID (`Nombre#Tag`) y obtiene su `puuid` (ACCOUNT-V1).
- Descarga las últimas partidas (MATCH-V5) y las guarda en SQLite, sin duplicar las que ya existen.
- Separa las estadísticas por tipo de partida (clasificatoria, ARAM, normales...) para que no se mezclen.
- Excluye de las estadísticas las partidas de menos de 5 minutos (remakes).
- Expone los resultados en JSON mediante una API REST con documentación automática.

## Requisitos

- Python 3.9 o superior
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

Crea un archivo `.env` en la raíz del proyecto con tu clave de la API:

```
RIOT_API_KEY=RGAPI-tu-clave-aqui
```

- Sin comillas y sin espacios alrededor del `=`.
- Las claves de desarrollo **expiran cada 24 horas**: hay que regenerarla en el portal de desarrolladores y actualizar esa línea.
- `.env` está en el `.gitignore` y nunca debe subirse al repositorio.

## Uso

### 1. Descargar y guardar partidas

```bash
python main.py
```

Pide tu Riot ID en dos partes (si es `Usuki#L01`, el nombre es `Usuki` y el tag `L01`), guarda las partidas nuevas en `partidas.db` e imprime las estadísticas:

```
Partidas nuevas guardadas: 20 | Total en la base: 20

=== Clasificatoria solo/duo ===
17 partidas | 7 victorias | winrate 41.2% | KDA promedio 6.2/6.2/8.6

Campeón       Partidas  Victorias  Winrate  KDA promedio
Yunara        3         2          66.7     4.7/6.3/6.7
...
```

Si lo ejecutas de nuevo, solo descarga las partidas nuevas.

### 2. Levantar la API

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

## Estructura

```
lol-match-analyzer/
├── main.py            # descarga partidas desde Riot y las guarda
├── database.py        # base de datos SQLite y consultas de estadísticas
├── api.py             # API REST con FastAPI
├── requirements.txt   # dependencias
├── partidas.db        # base de datos local (se crea sola, no se sube a Git)
├── .env               # tu clave de la API (no se sube a Git)
├── .gitignore
└── README.md
```

## Decisiones de diseño

- **Sin duplicados:** el `match_id` es la clave primaria y antes de pedir una partida se comprueba si ya está guardada, lo que ahorra peticiones.
- **Límites de la API:** la clave de desarrollo permite 20 solicitudes por segundo y 100 cada 2 minutos, por eso hay una pausa entre peticiones.
- **Separación de responsabilidades:** la lógica de datos vive en `database.py` y la comparten el script de descarga y la API.
- **Una conexión por petición** en la API, porque SQLite no comparte conexiones entre hilos.

## Próximos pasos

- [ ] Pruebas automáticas con pytest.
- [ ] Más métricas: daño, oro, visión y farmeo por minuto.
- [ ] Empaquetar con Docker y desplegar en la nube.
- [ ] Migrar de SQLite a PostgreSQL.

## Aviso legal

Este proyecto no está respaldado por Riot Games ni refleja las opiniones de Riot Games ni de nadie oficialmente involucrado en producir o gestionar League of Legends. League of Legends y Riot Games son marcas registradas de Riot Games, Inc.
