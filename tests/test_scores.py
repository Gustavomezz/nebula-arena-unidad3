from concurrent.futures import ThreadPoolExecutor

import pytest

from serverless.main import SqliteScores, create_app


@pytest.fixture
def client(tmp_path):
    return create_app(SqliteScores(str(tmp_path / "scores.sqlite"))).test_client()


def test_suma_puntos_y_no_duplica_resultado(client):
    body = {"jugador": "ana", "puntos": 1250, "evento": "partida-1"}
    assert client.post("/score", json=body).status_code == 201
    assert client.post("/score", json=body).status_code == 200
    body.update(evento="partida-2", puntos=100)
    assert client.post("/score", json=body).status_code == 201
    assert client.get("/top").json == [{"jugador": "ana", "puntos": 1350, "partidas": 2}]


@pytest.mark.parametrize("body", [None, {}, {"jugador": "a/b", "puntos": 1, "evento": "a"},
    {"jugador": "a", "puntos": -1, "evento": "a"},
    {"jugador": "a", "puntos": True, "evento": "a"},
    {"jugador": "a", "puntos": 1.5, "evento": "a"}])
def test_rechaza_entradas_invalidas(client, body):
    assert client.post("/score", json=body).status_code == 400


def test_top_10_ordenado(client):
    for i in range(15):
        client.post("/score", json={"jugador": f"p{i}", "puntos": i, "evento": f"e{i}"})
    result = client.get("/top").json
    assert len(result) == 10
    assert [r["puntos"] for r in result] == list(range(14, 4, -1))


def test_actualizaciones_concurrentes_sin_perdidas(tmp_path):
    store = SqliteScores(str(tmp_path / "concurrente.sqlite"))
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda n: store.add("ana", 1, f"e{n}"), range(100)))
    assert store.top() == [{"jugador": "ana", "puntos": 100, "partidas": 100}]
