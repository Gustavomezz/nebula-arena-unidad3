#!/usr/bin/env bash
# Ejecutar en la VM generadora, con el clúster y Grafana preparados previamente.
set -euo pipefail
: "${MATCHMAKER_URL:?Indica la URL interna de matchmaking}"
mkdir -p evidencias
locust -f loadtest/locustfile.py Jugador -u 800 -r 50 -t 3m \
  --headless --processes -1 --csv evidencias/demo --csv-full-history
