"""Clientes de carga. El RTT se mide por ping y se separa de la asignación."""
import json
import os
import random
import time
import uuid

import gevent
from gevent.event import AsyncResult
from locust import HttpUser, User, constant_pacing, task
from locust.exception import StopUser
from websocket import create_connection


class Jugador(User):
    wait_time = constant_pacing(.05)

    def measurement(self, name, started, error=None, length=0, request_type="WS"):
        self.environment.events.request.fire(
            request_type=request_type, name=name, response_time=(time.perf_counter() - started) * 1000,
            response_length=length, exception=error)

    def on_start(self):
        self.ws = None
        self.reader = None
        self.pending = {}
        self.alive = True
        started = time.perf_counter()
        try:
            direct = os.getenv("DIRECT_WS")
            if direct:
                url = direct
            else:
                import requests
                url = None
                deadline = time.monotonic() + 180
                while time.monotonic() < deadline:
                    attempt = time.perf_counter()
                    try:
                        response = requests.post(os.environ["MATCHMAKER_URL"] + "/join", timeout=15)
                        error = None if response.ok else requests.HTTPError(f"HTTP {response.status_code}")
                        self.measurement("asignacion", attempt, error, len(response.content), "HTTP")
                        if response.status_code == 200:
                            url = response.json()["url"]
                            break
                    except requests.RequestException as exc:
                        self.measurement("asignacion", attempt, exc, request_type="HTTP")
                    gevent.sleep(random.uniform(.5, 1.5))
                if url is None:
                    raise TimeoutError("Agones no tuvo servidores listos en 180 s")
            self.ws = create_connection(url, timeout=10, enable_multithread=False,
                                        skip_utf8_validation=True)
            greeting = json.loads(self.ws.recv())
            if "bienvenido" not in greeting:
                raise ValueError("falta bienvenida")
            self.measurement("conexion", started)
            self.ws.settimeout(None)
            self.reader = gevent.spawn(self.receive)
            self.count = 0
        except Exception as exc:
            self.measurement("conexion", started, exc)
            if self.ws:
                self.ws.close()
            raise StopUser() from exc

    def receive(self):
        try:
            while self.alive:
                data = json.loads(self.ws.recv())
                if "pong" in data and data["pong"] in self.pending:
                    self.pending[data["pong"]].set(True)
        except Exception as exc:
            self.alive = False
            for future in list(self.pending.values()):
                if not future.ready():
                    future.set_exception(exc)

    @task
    def play(self):
        if not self.alive:
            raise StopUser()
        try:
            self.ws.send(json.dumps({"x": random.uniform(0, 100), "y": random.uniform(0, 100),
                                     "dispara": random.random() < .1}))
            self.count += 1
            if self.count % 20 == 0:
                token = uuid.uuid4().hex
                future = AsyncResult()
                self.pending[token] = future
                started = time.perf_counter()
                try:
                    self.ws.send(json.dumps({"ping": token}))
                    future.get(timeout=5)
                    self.measurement("rtt", started)
                except Exception as exc:
                    self.measurement("rtt", started, exc)
                    raise StopUser() from exc
                finally:
                    self.pending.pop(token, None)
        except StopUser:
            raise
        except Exception as exc:
            self.measurement("envio", time.perf_counter(), exc)
            raise StopUser() from exc

    def on_stop(self):
        self.alive = False
        if self.ws:
            self.ws.close()
        if self.reader:
            self.reader.kill(block=False)


class Espectador(HttpUser):
    wait_time = constant_pacing(2)

    def on_start(self):
        response = self.client.get("/live/nebula/360p.m3u8", name="manifiesto", timeout=15)
        if response.status_code != 200:
            raise StopUser()
        self.segments = [line.strip() for line in response.text.splitlines() if line.endswith(".ts")]
        if not self.segments:
            raise StopUser()
        self.index = random.randrange(len(self.segments))

    @task
    def watch(self):
        segment = self.segments[self.index % len(self.segments)]
        self.index += 1
        with self.client.get("/live/nebula/" + segment, name="segmento", timeout=15,
                             catch_response=True) as response:
            if response.status_code == 200 and response.elapsed.total_seconds() > 2:
                response.failure("segmento tardó más de 2 s, posible rebuffering")


class Matchmaking(HttpUser):
    """Carga breve del servicio sin reservar partidas vacías, para observar HPA."""
    wait_time = constant_pacing(.05)

    @task
    def status(self):
        self.client.get("/healthz", name="salud_matchmaking", timeout=15)


class TablaLideres(HttpUser):
    wait_time = constant_pacing(.5)

    @task(4)
    def read_top(self):
        self.client.get("/top", name="top", timeout=15)

    @task(1)
    def save_score(self):
        self.client.post("/score", name="score", json={"jugador": f"sim-{random.randrange(10000)}",
                         "puntos": random.randrange(1000), "evento": uuid.uuid4().hex}, timeout=15)
