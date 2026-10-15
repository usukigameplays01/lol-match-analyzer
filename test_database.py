"""Pruebas de database.py.

Necesitan PostgreSQL corriendo (docker compose up -d db). Cada prueba usa un esquema temporal
que se borra al terminar, así que nunca tocan tus datos reales ni la API de Riot.
"""
import uuid

import psycopg
import pytest

import database


@pytest.fixture
def conn(monkeypatch):
    schema = f"test_{uuid.uuid4().hex[:8]}"
    base_url = database.DATABASE_URL
    with psycopg.connect(base_url, autocommit=True) as admin:
        admin.execute(f"CREATE SCHEMA {schema}")
        # Todas las tablas de esta prueba se crean dentro del esquema temporal
        monkeypatch.setattr(
            database, "DATABASE_URL", f"{base_url}?options=-c%20search_path%3D{schema}"
        )
        c = database.init_db()
        try:
            yield c
        finally:
            c.close()
            admin.execute(f"DROP SCHEMA {schema} CASCADE")


def partida(**cambios):
    """Partida de ejemplo; cada prueba cambia solo lo que le interesa."""
    datos = {
        "campeon": "Zeri",
        "kills": 5,
        "deaths": 3,
        "assists": 7,
        "win": 1,
        "duracion_min": 30.0,
        "modo": "CLASSIC",
        "queue_id": 420,
        "fecha": "2026-10-12T10:00",
    }
    datos.update(cambios)
    return datos


def test_match_exists_antes_y_despues_de_guardar(conn):
    assert not database.match_exists(conn, "LA1_1")
    database.save_match(conn, "LA1_1", partida())
    assert database.match_exists(conn, "LA1_1")


def test_guardar_dos_veces_la_misma_partida_no_duplica(conn):
    database.save_match(conn, "LA1_1", partida())
    database.save_match(conn, "LA1_1", partida())
    total = conn.execute("SELECT COUNT(*) FROM partidas").fetchone()[0]
    assert total == 1


def test_winrate_se_calcula_bien(conn):
    database.save_match(conn, "LA1_1", partida(win=1))
    database.save_match(conn, "LA1_2", partida(win=1))
    database.save_match(conn, "LA1_3", partida(win=0))

    resumen = database.resumen_por_cola(conn)

    assert len(resumen) == 1
    assert resumen[0]["partidas"] == 3
    assert resumen[0]["victorias"] == 2
    assert resumen[0]["winrate"] == 66.7


def test_kda_promedio(conn):
    database.save_match(conn, "LA1_1", partida(kills=10, deaths=2, assists=3))
    database.save_match(conn, "LA1_2", partida(kills=4, deaths=4, assists=6))
    database.save_match(conn, "LA1_3", partida(kills=1, deaths=6, assists=9))

    resumen = database.resumen_por_cola(conn)[0]

    assert resumen["kills_prom"] == 5.0
    assert resumen["muertes_prom"] == 4.0
    assert resumen["asistencias_prom"] == 6.0


def test_los_remakes_no_cuentan_en_las_estadisticas(conn):
    database.save_match(conn, "LA1_1", partida(win=1, duracion_min=30.0))
    database.save_match(conn, "LA1_2", partida(win=0, duracion_min=2.7))  # remake

    resumen = database.resumen_por_cola(conn)[0]

    assert resumen["partidas"] == 1
    assert resumen["winrate"] == 100.0
    # ...pero la partida sí queda guardada
    assert database.match_exists(conn, "LA1_2")


def test_separa_las_estadisticas_por_cola(conn):
    database.save_match(conn, "LA1_1", partida(queue_id=420, win=0))
    database.save_match(conn, "LA1_2", partida(queue_id=450, win=1))

    resumen = {fila["queue_id"]: fila for fila in database.resumen_por_cola(conn)}

    assert set(resumen) == {420, 450}
    assert resumen[420]["winrate"] == 0.0
    assert resumen[450]["winrate"] == 100.0


def test_campeones_de_cola_solo_incluye_esa_cola(conn):
    database.save_match(conn, "LA1_1", partida(campeon="Zeri", queue_id=420))
    database.save_match(conn, "LA1_2", partida(campeon="Jinx", queue_id=450))

    campeones = database.campeones_de_cola(conn, 420)

    assert [c["campeon"] for c in campeones] == ["Zeri"]


def test_campeones_de_cola_ordena_por_mas_partidas(conn):
    database.save_match(conn, "LA1_1", partida(campeon="Ezreal"))
    database.save_match(conn, "LA1_2", partida(campeon="Yunara"))
    database.save_match(conn, "LA1_3", partida(campeon="Yunara"))

    campeones = database.campeones_de_cola(conn, 420)

    assert campeones[0]["campeon"] == "Yunara"
    assert campeones[0]["partidas"] == 2


def test_campeones_de_cola_sin_datos_devuelve_lista_vacia(conn):
    assert database.campeones_de_cola(conn, 999) == []


def test_ultimas_partidas_orden_y_limite(conn):
    database.save_match(conn, "LA1_1", partida(fecha="2026-10-12T10:00"))
    database.save_match(conn, "LA1_2", partida(fecha="2026-10-12T12:00"))
    database.save_match(conn, "LA1_3", partida(fecha="2026-10-12T11:00"))

    ultimas = database.ultimas_partidas(conn, limit=2)

    assert [p["match_id"] for p in ultimas] == ["LA1_2", "LA1_3"]


def test_ultimas_partidas_formatea_resultado_y_kda(conn):
    database.save_match(conn, "LA1_1", partida(kills=8, deaths=4, assists=5, win=0))

    p = database.ultimas_partidas(conn)[0]

    assert p["kda"] == "8/4/5"
    assert p["resultado"] == "Derrota"


def test_nombre_cola_conocida_y_desconocida():
    assert database.nombre_cola(450) == "ARAM"
    assert database.nombre_cola(9999) == "Cola 9999"
