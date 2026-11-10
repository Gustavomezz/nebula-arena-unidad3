"""Cálculos reproducibles. Tarifas de referencia, no una factura de consumo."""
import json
import math


def egress_gb(viewers, kbps, seconds):
    return viewers * kbps * seconds / 8_000_000


def fleet_servers(players, per_match=10, ready_fraction=.2):
    return math.ceil(math.ceil(players / per_match) / (1 - ready_fraction))


def cdn_norteamerica(gib):
    # Tarifas escalonadas por GiB. Se supone que el mes inicia sin consumo previo.
    first = min(gib, 10 * 1024)
    second = min(max(0, gib - first), 140 * 1024)
    third = min(max(0, gib - first - second), 850 * 1024)
    last = max(0, gib - first - second - third)
    return first * .08 + second * .055 + third * .03 + last * .02


def estimate():
    node = .13402284
    servers = fleet_servers(1000)
    gb = egress_gb(20000, 6000, 3600)
    gib = gb * 1e9 / 2**30
    # Ejemplo, no duración medida: 200000 peticiones mensuales a 0.1 s sin concurrencia.
    invocations, duration = 200000, .1
    run_gross = invocations * duration * (.000024 + .5 * .0000025) + invocations / 1e6 * .40
    return {
        "tarifas_referencia_usd": {"e2_standard_4_h": node, "e2_standard_8_h": node * 2,
                                    "gestion_gke_h": .1, "ip_externa_h": .005},
        "capacidad_configurada_no_medida": {"jugadores": 1000, "partidas": 100,
                                             "servidores_con_buffer": servers,
                                             "vCPU_solo_contenedores_juego": servers * .25},
        "escenario_10_nodos": {"computo_y_gestion_h": 10 * node + .1,
                              "computo_gestion_por_jugador_h": (10 * node + .1) / 1000},
        "stream_500_360p_5min_gb": egress_gb(500, 800, 300),
        "stream_20000_1080p_1h_gb": gb,
        "stream_20000_1080p_1h_gib": gib,
        "cdn_norteamerica_solo_transferencia_usd": cdn_norteamerica(gib),
        "serverless_ejemplo_200000_peticiones_100ms_usd_sin_capa_gratuita": run_gross,
        "vm_e2_small_730h_solo_computo_usd": .016752855 * 730,
        "exclusiones": "Discos, IP, balanceadores, observabilidad, registro, Firestore, solicitudes CDN e impuestos. Verificar en calculadora antes de ejecutar.",
        "fuentes": ["https://cloud.google.com/products/compute/pricing/general-purpose",
                    "https://cloud.google.com/kubernetes-engine/pricing", "https://cloud.google.com/run/pricing",
                    "https://cloud.google.com/cdn/pricing"]
    }


if __name__ == "__main__":
    print(json.dumps(estimate(), indent=2, ensure_ascii=False))
