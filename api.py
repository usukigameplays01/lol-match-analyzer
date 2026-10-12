"""API propia que expone en JSON las estadísticas guardadas en la base de datos."""
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Query

from database import (
    campeones_de_cola,
    init_db,
    nombre_cola,
    resumen_por_cola,
    ultimas_partidas,
)

app = FastAPI(
    title="LoL Match Analyzer",
    description="Estadísticas de partidas de League of Legends guardadas desde la API de Riot.",
    version="0.1.0",
)


@contextmanager
def db():
    """Abre una conexión por petición (SQLite no comparte conexiones entre hilos)."""
    conn = init_db()
    try:
        yield conn
    finally:
        conn.close()


@app.get("/")
def raiz():
    return {
        "proyecto": "lol-match-analyzer",
        "documentacion": "/docs",
        "endpoints": ["/estadisticas", "/campeones/{queue_id}", "/partidas"],
    }


@app.get("/estadisticas")
def estadisticas():
    """Resumen por tipo de partida: total, victorias, winrate y KDA promedio."""
    with db() as conn:
        return resumen_por_cola(conn)


@app.get("/campeones/{queue_id}")
def campeones(queue_id: int):
    """Detalle por campeón dentro de un tipo de partida (por ejemplo 420 = clasificatoria solo/duo)."""
    with db() as conn:
        filas = campeones_de_cola(conn, queue_id)
    if not filas:
        raise HTTPException(status_code=404, detail=f"No hay partidas guardadas para la cola {queue_id}")
    return {"queue_id": queue_id, "cola": nombre_cola(queue_id), "campeones": filas}


@app.get("/partidas")
def partidas(limit: int = Query(10, ge=1, le=100)):
    """Últimas partidas guardadas, de la más reciente a la más antigua."""
    with db() as conn:
        return ultimas_partidas(conn, limit)
