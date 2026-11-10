"""Muestra evidencia descargada de Cloud Monitoring en una terminal legible."""
import json
from pathlib import Path
import pandas as pd
E=Path('evidencias')
r=json.loads((E/'cloud_run_resumen.json').read_text())
c=json.loads((E/'cloud_run_configuracion.json').read_text())
print('CLOUD RUN - NEBULA ARENA')
print('Intervalo UTC:',r['inicio_carga_utc'][:19],'a',r['fin_carga_utc'][:19])
print('Usuarios Locust: 500; pesos: 80% lecturas / 20% escrituras')
print('Concurrencia configurada:',c['spec']['template']['spec']['containerConcurrency'])
print('Maximo de instancias activas observado:',r['instancias_activas_max'])
print('Media de maximos concurrentes por instancia (intervalos de 1 minuto):')
f=pd.read_csv(E/'cloud_run_concurrencia.csv')
f['utc']=pd.to_datetime(f.utc).dt.strftime('%H:%M:%S UTC')
print(f[['utc','media_maximos','muestras']].rename(columns={'utc':'Hora','media_maximos':'Concurrencia_media','muestras':'Muestras'}).to_string(index=False,float_format=lambda v:f'{v:.2f}'))
print('Fuente: Cloud Monitoring, container/max_request_concurrencies')
print('Archivos originales: evidencias/cloud_run_monitoring.json')
