"""Registra si la VM generadora llega a ser el límite de la prueba."""
import argparse
import csv
import time

import psutil


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with open(args.output, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "cpu_porcentaje", "memoria_porcentaje", "bytes_enviados", "bytes_recibidos"])
        end = time.monotonic() + args.seconds
        while time.monotonic() < end:
            cpu = psutil.cpu_percent(interval=5)
            network = psutil.net_io_counters()
            writer.writerow([time.time(), cpu, psutil.virtual_memory().percent,
                             network.bytes_sent, network.bytes_recv])
            file.flush()
