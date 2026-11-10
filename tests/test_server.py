import asyncio
import json

import pytest
import websockets

from server.server import Game


@pytest.fixture
async def room():
    game = Game(empty_grace=.1)
    async with websockets.serve(game.player, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        yield game, f"ws://127.0.0.1:{port}"


async def test_conexion_ping_y_limpieza(room):
    game, url = room
    async with websockets.connect(url) as ws:
        player_id = json.loads(await ws.recv())["bienvenido"]
        await ws.send('{"ping":123}')
        assert json.loads(await ws.recv()) == {"pong": 123}
        await ws.send('{"x":2,"y":3}')
        await ws.send('{"ping":124}')
        await ws.recv()
        assert game.state[player_id]["x"] == 2
        assert game.players._value.get() == 1
    await asyncio.sleep(.02)
    assert game.state == {}
    assert game.players._value.get() == 0


async def test_undecimo_jugador_es_rechazado(room):
    game, url = room
    sockets = []
    try:
        for _ in range(10):
            ws = await websockets.connect(url)
            await ws.recv()
            sockets.append(ws)
        async with websockets.connect(url) as extra:
            with pytest.raises(websockets.ConnectionClosed) as error:
                await extra.recv()
            assert error.value.code == 4000
        assert len(game.connections) == 10
    finally:
        await asyncio.gather(*(ws.close() for ws in sockets))


@pytest.mark.parametrize("message", ['no es JSON', '[]', '{"x":NaN,"y":0}', '{"x":true,"y":2}'])
async def test_mensajes_invalidos_no_tiran_el_servidor(room, message):
    game, url = room
    async with websockets.connect(url) as ws:
        await ws.recv()
        await ws.send(message)
        assert "error" in json.loads(await ws.recv())
        await ws.send('{"ping":1}')
        assert json.loads(await ws.recv()) == {"pong": 1}


async def test_cliente_no_puede_suplantar_identificador(room):
    game, url = room
    async with websockets.connect(url) as ws:
        assigned = json.loads(await ws.recv())["bienvenido"]
        await ws.send('{"id":"otro","x":1,"y":2}')
        await ws.send('{"ping":1}')
        await ws.recv()
        assert set(game.state) == {assigned}


async def test_fin_de_partida_llama_shutdown():
    calls = []

    class SDK:
        async def call(self, route):
            calls.append(route)

    game = Game(SDK(), empty_grace=0)
    game.started = True
    game.empty_since = 0
    await asyncio.wait_for(game.loop(), 1)
    assert calls == ["/shutdown"]
    assert game.finished.is_set()
