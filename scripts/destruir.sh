#!/usr/bin/env bash
# Ejecutar desde la raíz del proyecto. Solo elimina recursos de este laboratorio.
set -euo pipefail
: "${PROYECTO:?Falta PROYECTO}"
mkdir -p evidencias
kubectl delete -f k8s/autoscaler.yaml --ignore-not-found
kubectl delete fleet nebula-fleet --ignore-not-found
kubectl delete -f k8s/matchmaker.yaml --ignore-not-found
terraform -chdir=infra/addons destroy -var "proyecto=$PROYECTO" -auto-approve | tee evidencias/destroy_addons.txt
terraform -chdir=infra destroy -var-file=terraform.tfvars -auto-approve | tee evidencias/destroy_infra.txt
# Conserva la salida del estado vacío antes de borrar el bucket que lo contiene.
terraform -chdir=infra state list | tee evidencias/estado_tras_destroy.txt
gcloud asset search-all-resources --scope="projects/$PROYECTO" \
  --format='table(assetType,name)' > evidencias/auditoria_recursos.txt
echo "Revisa la auditoría y conserva los logs antes de eliminar el bucket del estado remoto."
echo "Paso final: terraform -chdir=infra/bootstrap destroy -var proyecto=$PROYECTO"
