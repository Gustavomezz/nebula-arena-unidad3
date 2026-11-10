"""Consulta los recursos del proyecto después de destroy. Falla si una consulta falla."""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--proyecto',required=True)
args=parser.parse_args()
out=Path('evidencias/auditoria_cierre');out.mkdir(exist_ok=True)
commands={
 'vm':['compute','instances','list'],
 'discos':['compute','disks','list'],
 'direcciones':['compute','addresses','list'],
 'reglas_balanceo':['compute','forwarding-rules','list'],
 'backend_services':['compute','backend-services','list'],
 'backend_buckets':['compute','backend-buckets','list'],
 'url_maps':['compute','url-maps','list'],
 'proxy_http':['compute','target-http-proxies','list'],
 'clusters':['container','clusters','list'],
 'cloud_run':['run','services','list','--platform=managed','--region=us-central1'],
 'registros':['artifacts','repositories','list','--location=us-central1'],
 'firestore':['firestore','databases','list'],
 'buckets':['storage','buckets','list'],
}
counts={}
for name,cmd in commands.items():
    result=subprocess.run(['gcloud',*cmd,'--project='+args.proyecto,'--format=json','--quiet'],capture_output=True,text=True,check=True)
    data=json.loads(result.stdout)
    if not isinstance(data,list):
        raise ValueError(f'{name}: respuesta inesperada, no se interpreta como vacía')
    (out/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    counts[name]=len(data)
    print(name,counts[name],flush=True)
clean=all(x==0 for x in counts.values())
summary={'proyecto':args.proyecto,'consulta_utc':datetime.now(timezone.utc).isoformat(),
 'sin_recursos_facturables':clean,'conteos':counts,
 'alcance':'Todos los recursos de cómputo y balanceo del proyecto; Cloud Run, registro y Firestore en la región del laboratorio. Los servicios se desplegaron solo en us-central1.',
 'descripcion':('Terraform eliminó los complementos, la infraestructura y el bucket del estado. La auditoría posterior encontró cero VM, discos, IP reservadas, balanceadores, clústeres, servicios Cloud Run, repositorios de imágenes, bases Firestore y buckets. El proyecto y su configuración administrativa permanecen, sin esos recursos facturables.' if clean else 'La auditoría encontró recursos pendientes. No se considera terminado el cierre.')}
Path('evidencias/cierre_verificado.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
if not clean:raise SystemExit('Existen recursos pendientes; revisar antes de dar por terminado.')
