"""Relaciona eventos reales de Cluster Autoscaler con Node Ready."""
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
E=Path('evidencias')

def dt(v):return datetime.fromisoformat(v.replace('Z','+00:00'))
phases=json.loads((E/'ejecucion_cargas.json').read_text())['fases']
begin=dt(next(x for x in phases if x['nombre']=='rampa')['inicio_utc'])
events=json.loads((E/'eventos_rampa.json').read_text())['items']
nodes=json.loads((E/'nodos_rampa.json').read_text())['items']
triggers=[]
for e in events:
    stamp=e.get('firstTimestamp') or e.get('eventTime')
    if e.get('reason')=='TriggeredScaleUp' and stamp and dt(stamp)>=begin:
        triggers.append({'timestamp':stamp,'mensaje':e.get('message')})
result=[]
for n in nodes:
    created=dt(n['metadata']['creationTimestamp'])
    if created<begin:continue
    ready=next(c['lastTransitionTime'] for c in n['status']['conditions'] if c['type']=='Ready' and c['status']=='True')
    prior=[e for e in triggers if dt(e['timestamp'])<=created]
    if prior:
        event=max(prior,key=lambda e:e['timestamp'])
        result.append({'nodo':n['metadata']['name'],'evento_utc':event['timestamp'],
                       'node_ready_utc':ready,'reaccion_s':(dt(ready)-dt(event['timestamp'])).total_seconds(),
                       'evento':event['mensaje']})
text='El clúster creció de uno a tres nodos. '+ ' '.join(f"El nodo adicional {i+1} tardó {x['reaccion_s']:.0f} s desde TriggeredScaleUp hasta Node Ready." for i,x in enumerate(sorted(result,key=lambda x:x['evento_utc'])))
out={'nodos':result,'descripcion_reaccion':text,
     'nota':'No es el tiempo total desde el primer jugador. Los CSV de nodos pueden reflejar Ready unos segundos después por el intervalo de scrape.',
     'interpretacion_capacidad':'La rampa comprobó al menos 1,000 jugadores sostenidos bajo 80 ms. Los escenarios adicionales deben revisarse junto con la CPU de la generadora antes de atribuir una capacidad máxima al clúster.'}
(E/'reaccion_escalado.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')

# La capacidad se informa como máximo observado con esta configuración.
if (E/'estres_stats_history.csv').exists():
    metrics=pd.read_csv(E/'metricas_estres.csv')
    maximum=int(metrics.ccu.max());node_count=int(metrics.nodos.max())
    history=pd.read_csv(E/'estres_stats_history.csv')
    rtt=history[(history.Type=='WS')&(history.Name=='rtt')]
    recent=rtt[(rtt.Timestamp>=rtt.Timestamp.max()-65)&(rtt['User Count']>0)]
    generator=pd.read_csv(E/'generador_estres.csv')
    recent_gen=generator[generator.timestamp>=generator.timestamp.max()-65]
    duration=float(metrics.timestamp.diff().shift(-1).where(metrics.ccu>=maximum-10).sum())
    stats=pd.read_csv(E/'estres_stats.csv')
    failed=int(stats.loc[stats.Name=='conexion','Failure Count'].iloc[0])
    stress_begin=next(x['inicio_utc'] for x in phases if x['nombre']=='estres')
    ee=json.loads((E/'eventos_estres.json').read_text())['items']
    messages=sorted({e.get('message','') for e in ee if e.get('reason') in ['FailedScheduling','NotTriggerScaleUp'] and (e.get('lastTimestamp') or e.get('firstTimestamp') or '')>=stress_begin[:19]})
    cause='Kubernetes indicó CPU insuficiente y tope de nodos.' if any('Insufficient cpu' in x for x in messages) and any('max node group size' in x for x in messages) else 'La causa del límite requiere revisar los eventos de Kubernetes.'
    value={'maximo_ccu_observado':maximum,'nodos':node_count,'promedio_jugadores_por_nodo':maximum/node_count,
           'segundos_observados_cerca_del_maximo':duration,'fallos_conexion':failed,
           'p95_por_ventana_ultimos_65s_min_ms':float(recent['95%'].min()),
           'p95_por_ventana_ultimos_65s_max_ms':float(recent['95%'].max()),
           'cpu_generador_ultimos_65s_media':float(recent_gen.cpu_porcentaje.mean()),
           'cpu_generador_ultimos_65s_max':float(recent_gen.cpu_porcentaje.max()),
           'eventos_limitacion':messages}
    (E/'capacidad_observada.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    out['interpretacion_capacidad']=(f"El máximo observado fue {maximum} jugadores sobre {node_count} nodos, unos {duration:.0f} s cerca de ese nivel. En los últimos 65 s el p95 por ventana fue de {recent['95%'].min():.0f} a {recent['95%'].max():.0f} ms y la generadora no pasó de {recent_gen.cpu_porcentaje.max():.1f}% de CPU. Hubo {failed} clientes que no consiguieron servidor. {cause} Es el límite de admisión observado de esta configuración, no un máximo universal del juego. El p95 acumulado del estrés incluye el transitorio inicial.")
    (E/'reaccion_escalado.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(value,ensure_ascii=False,indent=2))

print(json.dumps(out,ensure_ascii=False,indent=2))
