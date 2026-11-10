"""Guarda métricas verdaderas de Prometheus cada cinco segundos."""
import argparse
import csv
import time

import requests

QUERIES = {
    "ccu": "sum(nebula_players_connected)",
    "tick_p99_ms": "histogram_quantile(0.99,sum by(le)(rate(nebula_tick_seconds_bucket[1m])))*1000",
    "tick_hz_por_servidor": "avg(rate(nebula_ticks_total[1m]))",
    "ready": 'sum(agones_gameservers_count{type="Ready",fleet_name="nebula-fleet"})',
    "allocated": 'sum(agones_gameservers_count{type="Allocated",fleet_name="nebula-fleet"})',
    "nodos": "count(kube_node_info)",
    "pods_matchmaker": 'count(kube_pod_info{pod=~"matchmaker-.*"})'
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:9090")
    parser.add_argument("--seconds", type=int, default=1800)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with open(args.output, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["timestamp", *QUERIES, "error"])
        writer.writeheader()
        end = time.monotonic() + args.seconds
        while time.monotonic() < end:
            row = {"timestamp": time.time()}
            try:
                for key, query in QUERIES.items():
                    response = requests.get(args.url + "/api/v1/query", params={"query": query}, timeout=10)
                    response.raise_for_status()
                    data = response.json()["data"]["result"]
                    row[key] = data[0]["value"][1] if data else ""
            except (requests.RequestException, ValueError, KeyError) as exc:
                # Conserva el hueco de medición y continúa; no inventa valores.
                row["error"] = str(exc)
            writer.writerow(row)
            file.flush()
            time.sleep(5)
