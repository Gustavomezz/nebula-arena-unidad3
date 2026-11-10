#!/usr/bin/env bash
# Ejecutar desde la raíz del proyecto. Solo elimina recursos de este laboratorio.
set -euo pipefail
: "${PROYECTO:?Falta PROYECTO}"
registro=$(terraform -chdir=infra output -raw registro)
cluster=$(terraform -chdir=infra output -raw cluster)
case "$registro" in
  *"/$PROYECTO/nebula") ;;
  *) echo "El proyecto indicado no coincide con el estado de Terraform." >&2; exit 1 ;;
esac
contexto=$(kubectl config current-context)
case "$contexto" in
  "gke_${PROYECTO}_"*"_${cluster}") ;;
  *) echo "kubectl no apunta al clúster de este laboratorio." >&2; exit 1 ;;
esac
asignados=$(kubectl get gameservers -o 'jsonpath={range .items[?(@.status.state=="Allocated")]}{.metadata.name}{"\n"}{end}')
if [[ -n "$asignados" ]]; then
  echo "Todavía existen partidas Allocated. Espera su cierre antes de destruir." >&2
  exit 1
fi
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
