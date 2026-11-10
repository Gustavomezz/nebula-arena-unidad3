"""Prueba de 10 clientes reales sobre un servidor local. No mide GKE."""
import asyncio
import json
import platform
import statistics
import time
from pathlib import Path

import websockets


async def player(url, seconds):
    samples = []
    async with websockets.connect(url) as ws:
        await ws.recv()
        end = time.monotonic() + seconds
        i = 0
        while time.monotonic() < end:
            await ws.send(json.dumps({"x": i % 100, "y": i % 70}))
            if i % 20 == 0:
                started = time.perf_counter()
                await ws.send(json.dumps({"ping": i}))
                while json.loads(await ws.recv()).get("pong") != i:
                    pass
                samples.append((time.perf_counter() - started) * 1000)
            else:
                # Leer continuamente evita acumular snapshots en la conexión.
                try:
                    await asyncio.wait_for(ws.recv(), .05)
                except asyncio.TimeoutError:
                    pass
            i += 1
            await asyncio.sleep(.05)
    return samples


async def main():
    results = await asyncio.gather(*(player("ws://127.0.0.1:7654", 30) for _ in range(10)))
    samples = sorted(x for row in results for x in row)
    data = {"entorno": "localhost macOS, servidor y clientes en el mismo equipo",
            "equipo": platform.platform(), "jugadores": 10, "duracion_s": 30,
            "muestras_rtt": len(samples), "rtt_media_ms": statistics.mean(samples),
            "rtt_p95_ms": samples[min(len(samples)-1, int(.95 * len(samples)))],
            "rtt_p99_ms": samples[min(len(samples)-1, int(.99 * len(samples)))],
            "limitacion": "No demuestra capacidad de Google Cloud ni autoescalado.",
            "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    Path("evidencias/carga_local_10.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
