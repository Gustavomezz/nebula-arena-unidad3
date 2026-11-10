"""Servidor didáctico de una partida de Nebula Arena, con hasta 10 jugadores."""
import asyncio
import json
import logging
import math
import os
import signal
import time
import urllib.request
import uuid

import websockets
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, start_http_server

MAX_JUGADORES = 10
TICK_S = 0.05
log = logging.getLogger("nebula")


class Agones:
    def __init__(self, enabled=False):
        self.enabled = enabled
        self.url = "http://localhost:" + os.getenv("AGONES_SDK_HTTP_PORT", "9358")

    async def call(self, route):
        if not self.enabled:
            return

        def request():
            req = urllib.request.Request(
                self.url + route, data=b"{}", method="POST",
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=2) as response:
                response.read()

        # Un fallo del SDK se registra y llega al llamador; no se oculta.
        await asyncio.to_thread(request)


class Game:
    def __init__(self, sdk=None, empty_grace=5):
        self.sdk = sdk or Agones()
        self.empty_grace = empty_grace
        self.connections = {}
        self.state = {}
        self.started = False
        self.empty_since = None
        self.finished = asyncio.Event()
        self.registry = CollectorRegistry()
        self.players = Gauge("nebula_players_connected", "Jugadores conectados", registry=self.registry)
        self.tick_time = Histogram(
            "nebula_tick_seconds", "Duración de una actualización",
            buckets=(.001, .0025, .005, .01, .025, .05, .1, .25, .5), registry=self.registry)
        self.ticks = Counter("nebula_ticks", "Actualizaciones terminadas", registry=self.registry)
        self.invalid = Counter("nebula_invalid_messages", "Mensajes rechazados", registry=self.registry)

    def snapshot(self):
        return json.dumps({"t": time.time(), "e": self.state}, separators=(",", ":"), allow_nan=False)

    @staticmethod
    def movement(data):
        values = (data.get("x"), data.get("y"))
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or not math.isfinite(v) or abs(v) > 100000 for v in values):
            raise ValueError("posición inválida")
        return {"x": values[0], "y": values[1], "dispara": bool(data.get("dispara", False))}

    async def player(self, ws):
        if len(self.connections) >= MAX_JUGADORES:
            await ws.close(code=4000, reason="partida llena")
            return
        player_id = uuid.uuid4().hex[:12]
        self.connections[ws] = player_id
        self.players.set(len(self.connections))
        self.started = True
        self.empty_since = None
        try:
            await ws.send(json.dumps({"bienvenido": player_id}))
            async for message in ws:
                try:
                    data = json.loads(message)
                    if not isinstance(data, dict):
                        raise ValueError("se requiere un objeto JSON")
                    if "ping" in data:
                        await ws.send(json.dumps({"pong": data["ping"]}, allow_nan=False))
                    else:
                        # El servidor asigna el identificador; un cliente no modifica a otro.
                        self.state[player_id] = {"id": player_id, **self.movement(data)}
                except (ValueError, TypeError):
                    self.invalid.inc()
                    await ws.send('{"error":"mensaje inválido"}')
        except websockets.ConnectionClosed:
            pass
        finally:
            self.connections.pop(ws, None)
            self.state.pop(player_id, None)
            self.players.set(len(self.connections))
            if not self.connections:
                self.empty_since = time.monotonic()

    async def send_snapshot(self, ws, message):
        try:
            await asyncio.wait_for(ws.send(message), timeout=TICK_S / 2)
        except (asyncio.TimeoutError, websockets.ConnectionClosed):
            await ws.close(code=4001, reason="conexión lenta o cerrada")

    async def loop(self):
        next_tick = time.monotonic()
        while not self.finished.is_set():
            started = time.perf_counter()
            if self.connections:
                message = self.snapshot()
                await asyncio.gather(*(self.send_snapshot(ws, message) for ws in list(self.connections)))
            self.tick_time.observe(time.perf_counter() - started)
            self.ticks.inc()
            if (self.started and not self.connections and self.empty_since is not None
                    and time.monotonic() - self.empty_since >= self.empty_grace):
                await self.sdk.call("/shutdown")
                self.finished.set()
                return
            next_tick += TICK_S
            if next_tick < time.monotonic() - TICK_S:
                next_tick = time.monotonic()
            await asyncio.sleep(max(0, next_tick - time.monotonic()))

    async def heartbeat(self):
        while not self.finished.is_set():
            await self.sdk.call("/health")
            await asyncio.sleep(2)

    async def run(self, host="0.0.0.0", port=7654, metrics_port=9100):
        start_http_server(metrics_port, addr=host, registry=self.registry)
        async with websockets.serve(self.player, host, port, max_size=4096, max_queue=32):
            await self.sdk.call("/ready")
            log.info("Servidor listo en %s:%s, máximo %s jugadores", host, port, MAX_JUGADORES)
            tasks = [asyncio.create_task(self.loop()), asyncio.create_task(self.heartbeat())]
            stop = asyncio.create_task(self.finished.wait())
            done, _ = await asyncio.wait([*tasks, stop], return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                if not task.cancelled() and task.exception():
                    raise task.exception()
            for task in [*tasks, stop]:
                task.cancel()
            await asyncio.gather(*tasks, stop, return_exceptions=True)


async def main():
    game = Game(Agones(os.getenv("AGONES_ENABLED", "false").lower() == "true"),
                empty_grace=float(os.getenv("EMPTY_GRACE", "5")))
    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_running_loop().add_signal_handler(sig, game.finished.set)
    await game.run(port=int(os.getenv("PORT", "7654")), metrics_port=int(os.getenv("METRICS_PORT", "9100")))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main())
