"""Acceso a la base de datos PostgreSQL: creación de la tabla, guardado y consultas de estadísticas."""
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

# En local apunta al PostgreSQL de docker-compose; en la nube se define con la variable DATABASE_URL.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://lol:lol@localhost:5432/lol")
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


def nombre_cola(queue_id):
    return COLAS.get(queue_id, f"Cola {queue_id}")


def _num(valor):
    """PostgreSQL devuelve Decimal en promedios y porcentajes; los pasamos a float."""
    return float(valor) if valor is not None else None


def init_db():
    conn = psycopg.connect(DATABASE_URL)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS partidas (
            match_id TEXT PRIMARY KEY,
            campeon TEXT,
            kills INTEGER,
            deaths INTEGER,
            assists INTEGER,
            win INTEGER,
            duracion_min DOUBLE PRECISION,
            modo TEXT,
            queue_id INTEGER,
            fecha TEXT
        )
        """
    )
    conn.commit()
    return conn


def match_exists(conn, match_id):
    row = conn.execute("SELECT 1 FROM partidas WHERE match_id = %s", (match_id,)).fetchone()
    return row is not None


def save_match(conn, match_id, r):
    conn.execute(
        """
        INSERT INTO partidas
            (match_id, campeon, kills, deaths, assists, win, duracion_min, modo, queue_id, fecha)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (match_id) DO NOTHING
        """,
        (match_id, r["campeon"], r["kills"], r["deaths"], r["assists"],
         r["win"], r["duracion_min"], r["modo"], r["queue_id"], r["fecha"]),
    )
    conn.commit()


def resumen_por_cola(conn):
    """Una fila por tipo de partida: total, victorias, winrate y KDA promedio."""
    rows = conn.execute(
        """
        SELECT queue_id,
               COUNT(*),
               SUM(win),
               ROUND(100.0 * SUM(win) / COUNT(*), 1),
               ROUND(AVG(kills), 1), ROUND(AVG(deaths), 1), ROUND(AVG(assists), 1)
        FROM partidas
        WHERE duracion_min >= %s
        GROUP BY queue_id
        ORDER BY COUNT(*) DESC
        """,
        (MIN_DURACION,),
    ).fetchall()
    return [
        {
            "queue_id": q,
            "cola": nombre_cola(q),
            "partidas": n,
            "victorias": int(v),
            "winrate": _num(wr),
            "kills_prom": _num(k),
            "muertes_prom": _num(d),
            "asistencias_prom": _num(a),
        }
        for q, n, v, wr, k, d, a in rows
    ]


def campeones_de_cola(conn, queue_id):
    rows = conn.execute(
        """
        SELECT campeon,
               COUNT(*),
               SUM(win),
               ROUND(100.0 * SUM(win) / COUNT(*), 1),
               ROUND(AVG(kills), 1), ROUND(AVG(deaths), 1), ROUND(AVG(assists), 1)
        FROM partidas
        WHERE queue_id = %s AND duracion_min >= %s
        GROUP BY campeon
        ORDER BY COUNT(*) DESC, 4 DESC
        """,
        (queue_id, MIN_DURACION),
    ).fetchall()
    return [
        {
            "campeon": c,
            "partidas": n,
            "victorias": int(v),
            "winrate": _num(wr),
            "kills_prom": _num(k),
            "muertes_prom": _num(d),
            "asistencias_prom": _num(a),
        }
        for c, n, v, wr, k, d, a in rows
    ]


def ultimas_partidas(conn, limit=10):
    rows = conn.execute(
        """
        SELECT match_id, campeon, kills, deaths, assists, win, duracion_min, queue_id, fecha
        FROM partidas
        ORDER BY fecha DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [
        {
            "match_id": m,
            "campeon": c,
            "kda": f"{k}/{d}/{a}",
            "resultado": "Victoria" if w else "Derrota",
            "duracion_min": dur,
            "cola": nombre_cola(q),
            "fecha": f,
        }
        for m, c, k, d, a, w, dur, q, f in rows
    ]
