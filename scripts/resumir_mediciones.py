"""Resume CSV y eventos originales, sin rellenar las mediciones ausentes."""
import json
from pathlib import Path
import pandas as pd

E=Path('evidencias')

def requests_summary(name):
    path=E/f'{name}_stats.csv'
    if not path.exists(): return None
    frame=pd.read_csv(path).fillna('')
    keys=['Type','Name','Request Count','Failure Count','Average Response Time','95%','99%','Max Response Time','Average Content Size']
    return frame[[k for k in keys if k in frame]].to_dict(orient='records')


def scenario(name):
    stats=requests_summary(name)
    if stats is None:return None
    out={'solicitudes':stats}
    path=E/f'metricas_{name}.csv'
    if path.exists():
        raw=pd.read_csv(path);m=raw.drop(columns=['error'],errors='ignore').apply(pd.to_numeric,errors='coerce')
        out['observacion']={'duracion_csv_s':float(m.timestamp.max()-m.timestamp.min()),
            'filas':len(m),'filas_con_error':int(raw.get('error',pd.Series(dtype=str)).notna().sum()),
            'intervalo_mediano_s':float(m.timestamp.diff().median())}
        for key in ['ccu','nodos','ready','allocated','pods_matchmaker','tick_p99_ms','tick_hz_por_servidor']:
            s=m[key].dropna()
            out['observacion'][key]={'min':float(s.min()),'max':float(s.max()),'mediana':float(s.median())} if len(s) else None
        if len(m):
            target=m[m.ccu>=990]
            out['observacion']['primer_ccu_990_timestamp']=float(target.timestamp.min()) if len(target) else None
            out['observacion']['segundos_observados_ccu_990_o_mas']=float(m.timestamp.diff().shift(-1).where(m.ccu>=990).sum())
    gp=E/f'generador_{name}.csv'
    if gp.exists():
        gen=pd.read_csv(gp)
        out['generador']={k:{'media':float(gen[k].mean()),'p95':float(gen[k].quantile(.95)),'max':float(gen[k].max())} for k in ['cpu_porcentaje','memoria_porcentaje'] if k in gen}
    ep=E/f'eventos_{name}.json';np=E/f'nodos_{name}.json'
    if ep.exists() and np.exists():
        events=json.loads(ep.read_text()).get('items',[])
        out['eventos_escalado']=[{'reason':e.get('reason'),'inicio':e.get('firstTimestamp') or e.get('eventTime'),'fin':e.get('lastTimestamp'),'message':e.get('message'),'objeto':e.get('involvedObject',{}).get('name')} for e in events if e.get('reason') in ['TriggeredScaleUp','ScaledUpGroup','ScaleUp','SuccessfulRescale']]
        out['eventos_limitacion']=[{'reason':e.get('reason'),'inicio':e.get('firstTimestamp') or e.get('eventTime'),'mensaje':e.get('message')} for e in events if e.get('reason') in ['FailedScheduling','NotTriggerScaleUp','FailedScaleUp']]
        out['nodos_ready']=[{'nombre':n['metadata']['name'],'creado':n['metadata']['creationTimestamp'],'ready':next((c.get('lastTransitionTime') for c in n.get('status',{}).get('conditions',[]) if c['type']=='Ready' and c['status']=='True'),None)} for n in json.loads(np.read_text()).get('items',[])]
    return out

out={name:scenario(name) for name in ['rampa','pico','estres','hpa','scores','stream']}
(E/'resumen_mediciones.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print(json.dumps({k:{'solicitudes':v['solicitudes'],'observacion':v.get('observacion'),'generador':v.get('generador')} for k,v in out.items() if v},ensure_ascii=False,indent=2,allow_nan=False))
