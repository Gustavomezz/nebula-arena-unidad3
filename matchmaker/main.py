"""Reparte 10 jugadores por partida y pide otra a Agones cuando se llena."""
import os
import threading
import time
from pathlib import Path

import requests
from flask import Flask


class Rooms:
    def __init__(self, allocate):
        self.allocate = allocate
        self.lock = threading.Lock()
        self.current = None
        self.slots = 0
        self.expires = 0

    def join(self):
        if not self.lock.acquire(blocking=False):
            raise RuntimeError("asignación en curso, reintentar")
        try:
            if not self.slots or time.monotonic() >= self.expires:
                self.current = self.allocate()
                self.slots = 10
                self.expires = time.monotonic() + 300
            self.slots -= 1
            return self.current
        finally:
            self.lock.release()


def allocate():
    root = Path("/var/run/secrets/kubernetes.io/serviceaccount")
    token = (root / "token").read_text().strip()
    namespace = os.getenv("NAMESPACE", "default")
    url = f"https://kubernetes.default.svc/apis/allocation.agones.dev/v1/namespaces/{namespace}/gameserverallocations"
    body = {"apiVersion": "allocation.agones.dev/v1", "kind": "GameServerAllocation",
            "spec": {"selectors": [{"matchLabels": {"agones.dev/fleet": "nebula-fleet"}}]}}
    response = requests.post(url, json=body, headers={"Authorization": f"Bearer {token}"},
                             verify=str(root / "ca.crt"), timeout=10)
    response.raise_for_status()
    return connection_info(response.json()["status"])


def connection_info(status):
    if status["state"] != "Allocated":
        raise RuntimeError("sin servidores listos")
    # La generadora está en la misma VPC y usa el firewall de la subred.
    address = next((item["address"] for item in status.get("addresses", [])
                    if item["type"] == "InternalIP"), status["address"])
    return {"url": f"ws://{address}:{status['ports'][0]['port']}",
            "partida": status["gameServerName"]}


def create_app(rooms=None):
    app = Flask(__name__)
    manager = rooms or Rooms(allocate)

    @app.get("/healthz")
    def health():
        return {"estado": "ok"}

    @app.post("/join")
    def join():
        try:
            return manager.join()
        except (requests.RequestException, RuntimeError) as exc:
            app.logger.warning("No se pudo asignar partida: %s", exc)
            return {"error": "esperando servidor disponible"}, 503

    return app


app = create_app()
