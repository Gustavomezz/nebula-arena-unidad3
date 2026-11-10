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
    rtt["Timestamp"] = pd.to_numeric(rtt["Timestamp"], errors="coerce").astype(float)
    observed = pd.read_csv(metrics).apply(pd.to_numeric, errors="coerce")
    aligned = pd.merge_asof(rtt.sort_values("Timestamp"), observed.sort_values("timestamp"),
                            left_on="Timestamp", right_on="timestamp", direction="nearest", tolerance=6)
    aligned = aligned.dropna(subset=["ccu", "p95"])
    aligned = aligned[(aligned.ccu > 0) & (aligned["User Count"] > 0)]
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
    fig, axes = plt.subplots(2, 1, figsize=(6.8, 4.5), sharex=True)
    for column, style, label in [("ready", "-", "Listos"), ("allocated", "--", "Asignados")]:
        axes[0].step(seconds, observed[column], where="post", linestyle=style, color="black", label=label)
    for column, style, label in [("nodos", "-", "Nodos"), ("pods_matchmaker", "--", "Réplicas matchmaking")]:
        axes[1].step(seconds, observed[column], where="post", linestyle=style, color="black", label=label)
    axes[0].set(ylabel="Servidores de partida")
    axes[1].set(xlabel="Tiempo transcurrido (s)", ylabel="Cantidad")
    for ax in axes:
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "escalado.png", dpi=170)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(6.8, 3.3))
    for name, label, style in [("asignacion", "Asignación HTTP", "-"),
                               ("conexion", "Conexión WS", "--"), ("rtt", "RTT WS", ":")]:
        series = history[history["Name"] == name]
        ax.plot(series.Timestamp - history.Timestamp.min(),
                pd.to_numeric(series["Failures/s"], errors="coerce"),
                color="black", linestyle=style, label=label)
    ax.set(xlabel="Tiempo transcurrido (s)", ylabel="Errores por segundo")
    ax.legend(fontsize=8)
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
              "se_observo_p95_80ms_o_mas": crossing,
              "nota_capacidad": "El cruce de 80 ms requiere revisar errores, CPU del generador y duración antes de atribuir un límite al servidor. Si no se cruza, solo se conoce un límite inferior.",
              "segundos_desde_subida_ccu_hasta_primer_nodo_nuevo": reaction,
              "nota_escalado": "Se usan las marcas reales del CSV. Agones y nodos pueden tener una resolución de 30 s en la fuente. Contrastar con eventos de Kubernetes.",
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
