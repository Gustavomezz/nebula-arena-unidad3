from concurrent.futures import ThreadPoolExecutor

from matchmaker.main import Rooms, connection_info, create_app


def test_25_jugadores_ocupan_tres_partidas():
    calls = []

    def allocate():
        calls.append(len(calls))
        return {"url": "ws://localhost:7654", "partida": f"sala-{len(calls)}"}

    rooms = Rooms(allocate)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: rooms.join(), range(25)))
    assert len(calls) == 3
    assert sum(r["partida"] == "sala-1" for r in results) == 10
    assert sum(r["partida"] == "sala-2" for r in results) == 10


def test_falta_de_capacidad_se_reporta():
    def fail():
        raise RuntimeError("sin servidores")
    client = create_app(Rooms(fail)).test_client()
    assert client.post("/join").status_code == 503


def test_generador_en_vpc_recibe_la_direccion_interna():
    status = {"state": "Allocated", "address": "203.0.113.5", "gameServerName": "sala",
              "ports": [{"port": 7001}], "addresses": [
                  {"type": "ExternalIP", "address": "203.0.113.5"},
                  {"type": "InternalIP", "address": "10.40.0.6"}]}
    assert connection_info(status)["url"] == "ws://10.40.0.6:7001"
