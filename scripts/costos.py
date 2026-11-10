"""Estimaciones reproducibles en USD. No representan una factura de consumo."""
import json
import math


def egress_gb(viewers, kbps, seconds):
    return viewers * kbps * seconds / 8_000_000


def fleet_servers(players, per_match=10, ready_fraction=.2):
    return math.ceil(math.ceil(players / per_match) / (1 - ready_fraction))


def cdn_norteamerica(gib):
    # Mes sin consumo previo. Tarifas por GiB según destino Norteamérica.
    first = min(gib, 10 * 1024)
    second = min(max(0, gib - first), 140 * 1024)
    third = min(max(0, gib - first - second), 850 * 1024)
    last = max(0, gib - first - second - third)
    return first * .08 + second * .055 + third * .03 + last * .02


def estimate():
    n2, e2, gke, ip, disk_month = .388472, .26804568, .10, .005, .04
    disk_hour = disk_month / 730
    game = 3 * n2 + gke + 3 * ip + 90 * disk_hour + .025
    generator = e2 + ip + 20 * disk_hour
    gb = egress_gb(20000, 6000, 3600)
    gib = gb * 1e9 / 2**30
    # Ejemplo sin solapar solicitudes. No inferir costo real con concurrencia=40.
    run_gross = 200000 * .1 * (.000024 + .5 * .0000025) + .2 * .40
    return {
        "tarifas_referencia_usd": {
            "n2_standard_8_h": n2, "e2_standard_8_h": e2,
            "gestion_gke_h": gke, "ip_externa_vm_h": ip,
            "pd_standard_gib_mes": disk_month, "mes_horas": 730,
            "lb_regional_primeras_5_reglas_h": .025,
            "lb_global_primeras_5_reglas_h": .025,
        },
        "dimensionamiento_teorico_1000": {
            "jugadores": 1000, "partidas_llenas": 100,
            "servidores_con_buffer_20_por_ciento_total": fleet_servers(1000),
            "vCPU_requests_juego_100m": fleet_servers(1000) * .1,
            "vCPU_requests_sdk_30m": fleet_servers(1000) * .03,
            "nota": "Sumar sistema y monitoreo. Las salas parciales pueden elevar el número real."
        },
        "juego_3_nodos_n2_standard_8": {
            "computo_h": 3 * n2, "gestion_h": gke, "ip_h": 3 * ip,
            "disco_90gib_h": 90 * disk_hour, "balanceador_interno_h": .025,
            "fijo_total_h": game, "fijo_por_jugador_h_a_1000": game / 1000,
            "nota": "Monitoreo comparte los nodos. No incluye generador ni CDN."
        },
        "generador_e2_standard_8_fijo_h": generator,
        "cdn_balanceador_global_fijo_h": .025,
        "laboratorio_fijo_3_nodos_mas_generador_y_lb_cdn_h": game + generator + .025,
        "stream_500_360p_5min_gb": egress_gb(500, 800, 300),
        "stream_20000_1080p_1h_gb": gb,
        "stream_20000_1080p_1h_gib": gib,
        "cdn_norteamerica_solo_transferencia_usd": cdn_norteamerica(gib),
        "serverless_ejemplo_200000_peticiones_100ms_usd_sin_capa_gratuita": run_gross,
        "vm_e2_small_730h_solo_computo_usd": .016752855 * 730,
        "exclusiones_del_fijo": "Tráfico y procesamiento de red, solicitudes y llenado de CDN, Storage, Artifact Registry, Firestore, Logging, impuestos y otros cargos variables. No se asumen créditos disponibles ni una factura final.",
        "fuentes": [
            "https://cloud.google.com/products/compute/pricing/general-purpose",
            "https://cloud.google.com/kubernetes-engine/pricing",
            "https://cloud.google.com/compute/disks-image-pricing",
            "https://cloud.google.com/vpc/network-pricing",
            "https://cloud.google.com/load-balancing/pricing",
            "https://cloud.google.com/run/pricing", "https://cloud.google.com/cdn/pricing",
            "https://cloud.google.com/artifact-registry/pricing"
        ]
    }


if __name__ == "__main__":
    print(json.dumps(estimate(), indent=2, ensure_ascii=False))
