# Nebula Arena

Unidad 3 de Cómputo en la Nube 1. Gustavo Adolfo Martínez Enríquez.

Servidor de partidas 5 contra 5 con WebSocket, Docker, GKE, Agones, Terraform,
GitHub Actions, Prometheus, Grafana y una tabla de líderes en Cloud Run con Firestore.
Los clientes de Locust simulan jugadores y espectadores. El video de prueba es un
patrón HLS de 360p, como indica la práctica.

## Estado de ejecución

El laboratorio se desplegó, se midió y se eliminó al terminar. Las seis prácticas,
la autoevaluación y el reporte técnico están terminados en `Documentos/`.
La presentación de diez minutos incluye notas y una demostración preparada.
El reporte técnico tiene seis páginas, incluida su portada.

Las 23 pruebas automáticas y las tres etapas del pipeline terminaron correctamente:
[ejecución completa](https://github.com/Gustavomezz/nebula-arena-unidad3/actions/runs/42763006149). Las imágenes publicadas llevan la etiqueta
`c589c72567365f1a558c920c6fe539cb6c7e89ce`. La identidad de GitHub usa federación y no una llave JSON.

| Prueba real en Google Cloud | Resultado |
| --- | --- |
| Rampa de 20 min, 1,000 jugadores, 2 entradas/s | 932,465 RTT, p95 8 ms, p99 16 ms, cero fallos RTT. |
| Pico de 10 min, 1,000 jugadores, 50 entradas/s | 533,386 RTT, p95 3 ms, p99 12 ms, cero fallos RTT. |
| Estrés de 5 min, 1,800 solicitados | Máximo observado de 1,610 conectados y 190 que no consiguieron servidor. |
| Streaming de 5 min, 500 espectadores | 74,500 solicitudes, cero fallos y p95 de segmento de 46 ms. |
| Cloud Run, 500 usuarios, pesos 80/20 | 169,199 solicitudes, 0 fallos, p99 de 3700 ms. |

Los 1,610 jugadores se observaron cerca del máximo durante unos 139 s. En los últimos
65 s del estrés, el p95 por ventana fue de 10 a 12 ms y la generadora no superó 81.6%
de CPU. Los eventos indican CPU insuficiente y el tope de tres nodos. Esta cifra es
el límite de admisión observado de esta configuración, no un máximo universal.
El p95 acumulado del estrés fue de 86 ms e incluye el transitorio de entrada.

La entrada es una limitación importante. La rampa tuvo 4,509 rechazos/reintentos HTTP
y el pico 44,243. Todos los 1,000 de ambos escenarios lograron conectar, con p95 hasta
entrar de 43 s y 92 s. En la entrada del pico, el p95 por ventana alcanzó 200 ms y la
generadora llegó a 99.7% de CPU. Esos segundos no se atribuyen solo al clúster. Las
mediciones de asignación, conexión y RTT se conservan separadas. Los dos primeros
ensayos abortados están identificados como diagnósticos y no cuentan como las pruebas finales.

El clúster creció de uno a tres nodos n2-standard-8. Cada nodo nuevo tardó 64 s entre
TriggeredScaleUp y Node Ready. HPA pasó de dos a nueve réplicas en la rampa y llegó a
diez en el pico. La generadora fue una e2-standard-8. La cuota global de 32 vCPU
incluyó los nodos y esa VM. Los contenedores de juego solicitaron 100m de CPU y
conservaron el límite de 500m, después de medir unos 28m por partida en el piloto.

Cloud Run registró hasta 10 instancias activas. Los datos de
concurrencia y arranque provienen de Cloud Monitoring. El p99 del cliente también
incluye red, cola e inicialización de Firestore. La práctica 3.1 se ejecutó en Colab
con CPU y T4, con sus resultados originales y el CSV de la calculadora.

Las URL de Cloud Run y CDN funcionaron durante las pruebas y se conservaron como
evidencia. Se retiraron junto con el laboratorio para cumplir `terraform destroy`.
`evidencias/cierre_verificado.json` y las consultas de `evidencias/auditoria_cierre/`
confirman el cierre. La cuenta de facturación sigue abierta.

## Archivos

- `server/`: servidor para 10 jugadores, con actualización a 20 Hz y métricas.
- `tests/`: pruebas de conexiones, límite de jugadores, validación, puntos y asignación.
- `infra/`: red, GKE, registro, generador, IAM, Firestore, Cloud Run y CDN.
- `infra/bootstrap/`: bucket del estado remoto de Terraform.
- `infra/addons/`: instalación de Agones, Prometheus y Grafana con Helm.
- `k8s/`: flota, autoescalado, matchmaking, monitores y tablero de Grafana.
- `serverless/`: API de puntos y top 10. Los reintentos no duplican un resultado.
- `loadtest/`: jugadores, espectadores, tabla de líderes, captura y análisis de métricas.
- `ia/`: notebook y script PPO de CartPole para comparar CPU con GPU.
- `evidencias/`: resultados originales de las ejecuciones. El nombre indica su entorno.
- `scripts/`: comprobación, costos, despliegue y eliminación del laboratorio.

## Comprobación local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
python server/server.py
```

En otra terminal:

```bash
source .venv/bin/activate
SCORES_BACKEND=sqlite SQLITE_PATH=/tmp/nebula-scores.sqlite \
  gunicorn --bind 127.0.0.1:8080 --workers 1 --threads 8 serverless.main:app
```

La tabla local usa SQLite para poder verificarla sin credenciales. En Cloud Run usa
Firestore. Las mediciones locales no prueban la capacidad de un clúster de Google Cloud.

## Práctica 3.1

```bash
pip install -r ia/requirements.txt
python ia/entrenar_bot.py --device cpu
python ia/entrenar_bot.py --device cuda
```

La segunda orden requiere NVIDIA CUDA. En Colab se puede usar el notebook de `ia/`
con el entorno T4. El script se detiene si CUDA no está disponible, para evitar presentar
una ejecución de CPU como una de GPU. PPO completa lotes de 2,048 pasos, así que
100,000 pasos solicitados producen 100,352 pasos reales.

## Preparación de Google Cloud

Se requiere una cuenta con verificación en dos pasos, facturación activa y cuota para
el laboratorio. El generador debe correr en `us-central1`, junto al clúster. Antes de
ejecutar, revisar la calculadora y crear una alerta de presupuesto. En esta ejecución se configuraron MXN 150, por debajo del ejemplo de USD 10 del material.
La alerta avisa del gasto; no funciona como límite automático.

Herramientas: Docker, Google Cloud CLI, GitHub CLI, kubectl, Terraform 1.6 o superior, Helm y FFmpeg. Para carga y gráficas instalar `pip install -r loadtest/requirements.txt`; las consultas de Monitoring también usan las dependencias de `requirements-dev.txt`.
Instalar el complemento `gke-gcloud-auth-plugin`. Agones 1.62 admite Kubernetes
1.34, 1.35 y 1.36; comprobar la versión que ofrece GKE antes de crear el clúster.

```bash
export PROYECTO=ID_DEL_PROYECTO
gcloud auth login
gcloud auth application-default login
gcloud config set project "$PROYECTO"
gcloud services enable storage.googleapis.com cloudresourcemanager.googleapis.com \
  serviceusage.googleapis.com
terraform -chdir=infra/bootstrap init
terraform -chdir=infra/bootstrap plan -var "proyecto=$PROYECTO" -out bootstrap.tfplan
terraform -chdir=infra/bootstrap apply bootstrap.tfplan
terraform -chdir=infra init -reconfigure \
  -backend-config="bucket=$PROYECTO-nebula-tfstate" -backend-config="prefix=dev/base"
cp infra/terraform.tfvars.example infra/terraform.tfvars
```

Editar `infra/terraform.tfvars` con el ID real. Crear y revisar un plan antes de aplicar.
Para recrear después de `destroy`, cambiar `pool_ci` a un ID nuevo, por ejemplo
`nebula-github-demo-01`, porque IAM retiene el ID de un pool eliminado durante 30 días.
Actualizar también la variable `WIF_PROVIDER` de GitHub con la nueva salida.
[Documentación de eliminación y recuperación de pools](https://docs.cloud.google.com/iam/docs/manage-workload-identity-pools-providers).

```bash
terraform -chdir=infra plan -out laboratorio.tfplan
terraform -chdir=infra show -no-color laboratorio.tfplan > evidencias/terraform_plan.txt
terraform -chdir=infra apply laboratorio.tfplan
gcloud container clusters get-credentials nebula-dev --zone us-central1-a
terraform -chdir=infra/addons init -reconfigure \
  -backend-config="bucket=$PROYECTO-nebula-tfstate" -backend-config="prefix=dev/addons"
terraform -chdir=infra/addons plan -var "proyecto=$PROYECTO" -out addons.tfplan
terraform -chdir=infra/addons apply addons.tfplan
```

El estado se separa en base y complementos para que Helm se conecte a un clúster
que ya existe y para desinstalar los complementos antes de destruirlo.

## Imágenes y CI/CD

La primera etapa de GitHub Actions prueba el código y valida Terraform. La segunda
construye los tres contenedores, los ejecuta para comprobarlos y conserva las imágenes
como artefactos con la etiqueta exacta del commit. La etapa `nube` publica en Artifact
Registry y se habilita después de preparar GCP.
Una etapa omitida no demuestra un despliegue exitoso en GKE.

Publicación inicial para poder crear Cloud Run:

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
export TAG=$(git rev-parse HEAD)
for component in server serverless matchmaker; do
  docker buildx build --platform linux/amd64 \
    -t "us-central1-docker.pkg.dev/$PROYECTO/nebula/nebula-$component:$TAG" \
    --push "$component"
done
```

Habilitar `crear_serverless = true`, indicar `imagen_serverless` con la imagen publicada,
y aplicar un nuevo plan revisado. Para la prueba del video, habilitar `crear_cdn = true`.

Variables de GitHub Actions: `GCP_PROJECT`, `WIF_PROVIDER`, `DEPLOY_SERVICE_ACCOUNT`
y `CLOUD_ENABLED=true`. Las dos identidades se obtienen de `terraform output`.
Se usa federación de identidad y no se guarda una llave JSON.

```bash
export SERVER_IMAGE="us-central1-docker.pkg.dev/$PROYECTO/nebula/nebula-server:$TAG"
export MATCHMAKER_IMAGE="us-central1-docker.pkg.dev/$PROYECTO/nebula/nebula-matchmaker:$TAG"
python scripts/aplicar_k8s.py
kubectl get gameservers
```

El rollback consiste en volver a las imágenes del commit anterior, aplicar el mismo
despliegue y comprobar métricas. Agones conserva las partidas asignadas hasta que
terminan. Borrar a la fuerza un pod asignado corta la partida que guarda en memoria.

## Carga y métricas

Abrir Prometheus y Grafana en la máquina de control:

```bash
kubectl -n monitoring port-forward svc/monitoreo-kube-prometheus-prometheus 9090:9090
kubectl -n monitoring port-forward svc/monitoreo-grafana 3000:80
```

El tablero se importa automáticamente desde `k8s/dashboard.yaml`. Obtener la contraseña
local de Grafana desde su Secret y no incluirla en capturas ni en el repositorio.
Durante cada escenario, en otra terminal:

```bash
python loadtest/recoger_metricas.py --seconds 1500 --output evidencias/metricas_rampa.csv
```

Copiar `loadtest/` a la VM `nebula-dev-locust`, crear un entorno virtual e instalar sus
dependencias. Obtener la IP interna con `kubectl get svc matchmaker`. En la VM:

```bash
export MATCHMAKER_URL=http://IP_INTERNA_MATCHMAKER
locust -f loadtest/locustfile.py Jugador -u 1000 -r 2 -t 20m \
  --headless --processes -1 --csv rampa --csv-full-history
locust -f loadtest/locustfile.py Jugador -u 1000 -r 50 -t 10m \
  --headless --processes -1 --csv pico --csv-full-history
locust -f loadtest/locustfile.py TablaLideres --host URL_CLOUD_RUN \
  -u 500 -r 50 -t 5m --headless --processes -1 --csv scores --csv-full-history
```

Ejecutar cada escenario con la captura de métricas correspondiente. Dejar terminar las
partidas entre escenarios. El número de usuarios pedidos a Locust puede incluir clientes
que todavía esperan servidor. Por eso la capacidad se calcula con CCU de Prometheus.
La latencia se toma de `rtt`, sin mezclarla con el tiempo de asignación.

```bash
bash stream/generar.sh
gcloud storage rsync --recursive stream/video/ "gs://$PROYECTO-nebula-stream/"
# En la VM, contra la URL de la CDN obtenida de Terraform:
locust -f loadtest/locustfile.py Espectador --host URL_CDN -u 500 -r 50 -t 5m \
  --headless --processes -1 --csv stream --csv-full-history
```

Guardar los CSV originales en `evidencias/` y analizar:

```bash
python loadtest/analizar.py --prefix evidencias/rampa \
  --metricas evidencias/metricas_rampa.csv --output evidencias/graficas_rampa
python scripts/costos.py
```

Para encontrar una capacidad máxima, subir la carga hasta observar el umbral de 80 ms,
errores o una degradación sostenida. Si la prueba llega a 1,000 y sigue bien, el resultado
es “al menos 1,000”, no una capacidad máxima demostrada de 1,000.

## Demostración de 10 minutos

Recrear la infraestructura antes de la clase. Cambiar `pool_ci` a un ID nuevo si el
anterior sigue retenido por IAM, actualizar las variables de GitHub y habilitar
`CLOUD_ENABLED=true` después de preparar el entorno. Las mediciones y las imágenes
de la entrega permiten revisar lo realizado mientras los recursos están eliminados.

Antes de comenzar la exposición, dejar un nodo y tres servidores listos. Ejecutar
`scripts/preparar_carga.sh` desde el equipo de control solo cuando ya no existan
partidas Allocated. Abrir los port-forward y el tablero de Grafana. Preparar la VM
generadora con su entorno y la variable `MATCHMAKER_URL`.

Las notas de las diapositivas distribuyen siete minutos de explicación y tres de
demostración. Al comenzar la última diapositiva, en la VM:

```bash
bash scripts/demostracion.sh
```

El script solicita 800 usuarios a 50 por segundo durante tres minutos. Mostrar CCU,
Ready/Allocated, réplicas de matchmaking y la llegada de un nodo. Comparar la reacción
con los 64 s medidos. Consultar `/top` de Cloud Run y conservar los resultados antes
de volver a destruir los recursos. Para un evento real de 1,000 jugadores se propone preparar tres nodos y 130 partidas
listas antes del pico, tomando como referencia los 104 asignados más 26 Ready de la
rampa. La demostración parte de tres partidas para que se pueda observar el escalado.

## Cierre

```bash
bash scripts/destruir.sh
```

Guardar las salidas de destrucción y revisar que no quedan VM, discos, balanceadores,
registros ni servicios cobrando. Tras conservar las evidencias, destruir el bucket del
estado con `infra/bootstrap`. Después ejecutar `python scripts/auditar_cierre.py --proyecto "$PROYECTO"` y comprobar que todos los conteos estén en cero. Las cuentas y proyectos de otros trabajos no se modifican.

## Fuentes de consulta

Material de estudio de la Unidad 3 proporcionado por el profesor y documentación
oficial de Agones, Kubernetes, Terraform y Google Cloud. Las direcciones de los precios
utilizados están registradas en `evidencias/costos_referencia.json`.
