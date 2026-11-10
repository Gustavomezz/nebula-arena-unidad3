"""Comprobación real del servidor y de la tabla de líderes encendidos."""
import asyncio
import json
import os
import uuid

import requests
import websockets


async def main():
    ws_url = os.getenv("WS_URL", "ws://localhost:7654")
    score_url = os.getenv("SCORE_URL", "http://localhost:8080")
    async with websockets.connect(ws_url) as ws:
        greeting = json.loads(await ws.recv())
        assert "bienvenido" in greeting
        await ws.send('{"ping":"smoke"}')
        while True:
            data = json.loads(await ws.recv())
            if "pong" in data:
                assert data["pong"] == "smoke"
                break
    body = {"jugador": "prueba", "puntos": 1250, "evento": uuid.uuid4().hex}
    response = requests.post(score_url + "/score", json=body, timeout=10)
    assert response.status_code == 201, response.text
    response = requests.get(score_url + "/top", timeout=10)
    response.raise_for_status()
    assert any(row["jugador"] == "prueba" for row in response.json())
    metrics = requests.get(os.getenv("METRICS_URL", "http://localhost:9100/metrics"), timeout=5)
    assert "nebula_players_connected" in metrics.text
    print("WebSocket, ping, métricas y tabla de líderes: correcto")


if __name__ == "__main__":
    asyncio.run(main())
