#!/usr/bin/env bash
# Restablece el laboratorio vacío antes de medir el crecimiento de los nodos.
set -euo pipefail
: "${PROYECTO:?Falta PROYECTO}"
kubectl get gameservers -l agones.dev/fleet=nebula-fleet -o json | python3 -c '
import json,sys
items=json.load(sys.stdin)["items"]
if any(g["status"]["state"] == "Allocated" for g in items):
    sys.exit("Todavía hay partidas asignadas. Espera a que terminen.")
'
kubectl delete fleetautoscaler nebula-autoscaler --ignore-not-found
kubectl scale fleet nebula-fleet --replicas=0
kubectl wait --for=delete gameservers -l agones.dev/fleet=nebula-fleet --timeout=90s
gcloud container clusters resize nebula-dev --node-pool=game-pool --num-nodes=1 \
  --zone="${ZONA:-us-central1-a}" --project="$PROYECTO" --quiet
kubectl scale fleet nebula-fleet --replicas=3
kubectl apply -f k8s/autoscaler.yaml
kubectl rollout restart deployment/matchmaker
kubectl rollout status deployment/matchmaker --timeout=180s
kubectl wait gameservers -l agones.dev/fleet=nebula-fleet \
  --for=jsonpath='{.status.state}'=Ready --timeout=180s
kubectl get fleet,gameservers,nodes
