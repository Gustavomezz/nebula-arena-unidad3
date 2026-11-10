"""Descarga métricas oficiales de Cloud Run con credenciales locales, sin imprimirlas."""
import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import google.auth
from google.auth.transport.requests import AuthorizedSession

parser=argparse.ArgumentParser()
parser.add_argument('--proyecto',required=True)
parser.add_argument('--horas',type=float,default=2)
parser.add_argument('--output',type=Path,default=Path('evidencias/cloud_run_monitoring.json'))
args=parser.parse_args()
creds,_=google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'],quota_project_id=args.proyecto)
s=AuthorizedSession(creds)
base=f'https://monitoring.googleapis.com/v3/projects/{args.proyecto}'
end=datetime.now(timezone.utc);start=end-timedelta(hours=args.horas)
metrics=['container/instance_count','container/max_request_concurrencies','container/startup_latencies','request_latencies','request_count','container/billable_instance_time']
out={'consulta_utc':end.isoformat(),'desde_utc':start.isoformat(),'series':{}}
for metric in metrics:
    name='run.googleapis.com/'+metric
    params={'filter':f'metric.type="{name}" AND resource.type="cloud_run_revision" AND resource.labels.service_name="nebula-dev-leaderboard"','interval.startTime':start.isoformat(),'interval.endTime':end.isoformat(),'view':'FULL','pageSize':1000}
    series=[]
    while True:
        r=s.get(base+'/timeSeries',params=params,timeout=30);r.raise_for_status()
        data=r.json();series.extend(data.get('timeSeries',[]))
        if not data.get('nextPageToken'):break
        params['pageToken']=data['nextPageToken']
    d=s.get(base+'/metricDescriptors/'+name,timeout=30);d.raise_for_status()
    out['series'][name]={'datos':{'timeSeries':series},'descriptor':d.json()}
    print(name,len(series),'series descargadas')
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
