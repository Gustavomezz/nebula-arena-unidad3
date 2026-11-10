"""Gráficas de instancias y concurrencia de Cloud Monitoring durante la carga."""
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

E=Path('evidencias')
j=json.loads((E/'cloud_run_monitoring.json').read_text())
phase=next(x for x in json.loads((E/'ejecucion_cargas.json').read_text())['fases'] if x['nombre']=='scores')
start=datetime.fromisoformat(phase['inicio_utc'])
end=datetime.fromisoformat(phase.get('fin_utc',datetime.now(timezone.utc).isoformat()))
rows=[];starts=[];billable=0;con=[]
for metric,entry in j['series'].items():
    for series in entry['datos'].get('timeSeries',[]):
        labels=series['metric'].get('labels',{})
        rev=series['resource']['labels']['revision_name']
        for p in series['points']:
            t=datetime.fromisoformat(p['interval']['endTime'].replace('Z','+00:00'))
            v=p['value']
            if metric.endswith('/instance_count') and start-timedelta(minutes=4)<=t<=end+timedelta(minutes=3):
                rows.append({'utc':t,'revision':rev,'estado':labels.get('state'),'instancias':int(v.get('int64Value',0))})
            if not start<=t<=end+timedelta(minutes=1):continue
            dist=v.get('distributionValue',{})
            count=int(dist.get('count',0))
            if metric.endswith('/max_request_concurrencies') and labels.get('state')=='active' and count:
                con.append({'utc':t,'revision':rev,'muestras':count,'media_maximos':dist['mean'],'distribucion':dist})
            if metric.endswith('/startup_latencies') and count:
                starts.append({'utc':t.isoformat(),'revision':rev,'arranques':count,'media_ms':dist['mean']})
            if metric.endswith('/billable_instance_time'):billable+=float(v.get('doubleValue',0))
if not rows or not con:
    raise SystemExit('Cloud Monitoring todavía no tiene muestras de concurrencia en el intervalo. Volver a consultar después del retraso de publicación.')
frame=pd.DataFrame(rows)
frame.to_csv(E/'cloud_run_instancias.csv',index=False)
conframe=pd.DataFrame([{k:v for k,v in x.items() if k!='distribucion'} for x in con])
conframe.to_csv(E/'cloud_run_concurrencia.csv',index=False)
inst=frame.groupby(['utc','estado']).instancias.sum().unstack(fill_value=0)
conc=conframe.assign(producto=conframe.media_maximos*conframe.muestras).groupby('utc').agg({'producto':'sum','muestras':'sum'})
conc['media_maximos']=conc.producto/conc.muestras
fig,ax=plt.subplots(2,1,figsize=(7,4.7),sharex=True)
for state,style in [('active','-'),('idle','--')]:
    if state in inst:ax[0].step(inst.index,inst[state],where='post',color='black',linestyle=style,marker='o',markersize=3,label={'active':'Activas','idle':'En espera'}[state])
ax[0].set_ylabel('Instancias');ax[0].legend(fontsize=8)
ax[1].plot(conc.index,conc.media_maximos,color='black',marker='o',markersize=3)
ax[1].set_ylabel('Media de máximos\nconcurrentes por instancia')
ax[1].set_xlabel('Hora UTC (intervalos de un minuto)')
ax[1].tick_params(axis='x',labelrotation=20)
fig.tight_layout();fig.savefig(E/'cloud_run_concurrencia.png',dpi=170);plt.close(fig)
active=inst.get('active',pd.Series(0,index=inst.index))
summary={'medicion_finalizada':phase['estado']=='medicion_finalizada','inicio_carga_utc':start.isoformat(),'fin_carga_utc':end.isoformat(),
'instancias_activas_max':int(active.max()),'instancias_totales_max':int(inst.sum(axis=1).max()),
'concurrencia_media_maxima_por_instancia':float(conc.media_maximos.max()),
'nota_concurrencia':'Métrica container/max_request_concurrencies: distribución del máximo por instancia en cada minuto. La curva presenta la media de esos máximos, no una medición instantánea ni la suma de clientes Locust.',
'cero_antes_carga':bool((inst.loc[inst.index<start].sum(axis=1)==0).any()),
'arranques':starts,'segundos_facturables_intervalo':billable,
'nota_arranque':'startup_latencies mide el inicio del contenedor. El p99 de Locust incluye la petición completa, red, cola e inicialización de Firestore. No equivalen a la misma métrica.'}
(E/'cloud_run_resumen.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
