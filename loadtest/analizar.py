"""Gráficas de resultados observados, sin completar datos que no se midieron."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def analyze(prefix, metrics, output):
    output.mkdir(parents=True, exist_ok=True)
    history = pd.read_csv(str(prefix) + "_stats_history.csv")
    # La fila agregada mezcla conexión y RTT. Para la latencia se usa solo rtt.
    rtt = history[(history["Name"] == "rtt") & (history["Type"] == "WS")].copy()
    rtt["p95"] = pd.to_numeric(rtt["95%"], errors="coerce")
    rtt["Timestamp"] = pd.to_numeric(rtt["Timestamp"], errors="coerce")
    observed = pd.read_csv(metrics).apply(pd.to_numeric, errors="coerce")
    aligned = pd.merge_asof(rtt.sort_values("Timestamp"), observed.sort_values("timestamp"),
                            left_on="Timestamp", right_on="timestamp", direction="nearest", tolerance=6)
    aligned = aligned.dropna(subset=["ccu", "p95"])
    if aligned.empty:
        raise ValueError("No hay mediciones RTT que coincidan con el CCU observado en Prometheus.")
    fig, ax = plt.subplots(figsize=(6.8, 3.5))
    ax.scatter(aligned.ccu, aligned.p95, color="black", s=12)
    ax.axhline(80, color="black", linestyle="--", label="Meta de 80 ms")
    ax.set(xlabel="Jugadores conectados observados", ylabel="RTT p95 (ms)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "ccu_vs_p95.png", dpi=170)
    plt.close(fig)
    seconds = observed.timestamp - observed.timestamp.iloc[0]
    fig, ax = plt.subplots(figsize=(6.8, 3.5))
    for column, style in [("ready", "-"), ("allocated", "--"), ("nodos", ":")]:
        ax.plot(seconds, observed[column], style, color="black", label=column)
    ax.set(xlabel="Tiempo transcurrido (s)", ylabel="Cantidad")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "escalado.png", dpi=170)
    plt.close(fig)
    errors = pd.to_numeric(rtt["Failures/s"], errors="coerce")
    fig, ax = plt.subplots(figsize=(6.8, 3.3))
    ax.plot(rtt.Timestamp - rtt.Timestamp.iloc[0], errors, color="black")
    ax.set(xlabel="Tiempo transcurrido (s)", ylabel="Errores RTT por segundo")
    fig.tight_layout()
    fig.savefig(output / "errores.png", dpi=170)
    plt.close(fig)
    good = aligned[aligned.p95 < 80]
    maximum = float(good.ccu.max()) if not good.empty else None
    crossing = bool((aligned.p95 >= 80).any())
    node_times = observed.loc[observed.nodos > observed.nodos.iloc[0], "timestamp"]
    growth = observed.loc[observed.ccu > observed.ccu.iloc[0], "timestamp"]
    reaction = float(node_times.iloc[0] - growth.iloc[0]) if len(node_times) and len(growth) else None
    result = {"maximo_ccu_observado_bajo_80ms": maximum,
              "se_observo_limite_de_latencia": crossing,
              "nota_capacidad": "Si no se cruzó el umbral, solo se conoce un límite inferior de capacidad.",
              "segundos_desde_subida_ccu_hasta_primer_nodo_nuevo": reaction,
              "nota_escalado": "Resolución de muestreo de 5 s. También revisar pods pendientes y eventos de Kubernetes.",
              "muestras_validas": len(aligned)}
    (output / "resumen.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--metricas", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("evidencias/graficas"))
    args = parser.parse_args()
    analyze(args.prefix, args.metricas, args.output)
