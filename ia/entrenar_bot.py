"""Práctica 3.1: entrenamiento PPO y medición real de inferencia en CPU."""
import argparse
import json
import math
import platform
import time
from pathlib import Path

import gymnasium as gym
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy


def benchmark(device, steps, output):
    torch.set_num_threads(1)
    env = gym.make("CartPole-v1")
    env.reset(seed=42)
    model = PPO("MlpPolicy", env, seed=42, device=device, verbose=0)
    start = time.perf_counter()
    model.learn(total_timesteps=steps)
    elapsed = time.perf_counter() - start
    actual_steps = model.num_timesteps
    output.mkdir(parents=True, exist_ok=True)
    model.save(output / f"bot_nebula_{device}")
    # Inferencia en CPU incluso cuando el entrenamiento se hizo en CUDA.
    model.policy.to("cpu")
    model.device = torch.device("cpu")
    observations = []
    obs, _ = env.reset(seed=99)
    for _ in range(100):
        observations.append(obs.copy())
        obs, _, terminated, truncated, _ = env.step(env.action_space.sample())
        if terminated or truncated:
            obs, _ = env.reset()
    for obs in observations:
        model.predict(obs, deterministic=True)
    durations = []
    for i in range(10000):
        start = time.perf_counter_ns()
        model.predict(observations[i % len(observations)], deterministic=True)
        durations.append((time.perf_counter_ns() - start) / 1e6)
    mean_ms = float(np.mean(durations))
    capacity = 1000 / mean_ms
    reward, std = evaluate_policy(model, env, n_eval_episodes=10, deterministic=True, warn=False)
    result = {
        "dispositivo_entrenamiento": device, "equipo": platform.platform(),
        "torch": torch.__version__, "pasos_solicitados": steps, "pasos_reales": actual_steps,
        "semilla": 42, "hilos_cpu": 1, "entrenamiento_s": elapsed,
        "inferencia_cpu_media_ms": mean_ms, "inferencia_cpu_p95_ms": float(np.percentile(durations, 95)),
        "decisiones_s_por_hilo": capacity, "demanda_bots_s": 2000 * 10,
        "vCPU_con_margen_30_por_ciento": math.ceil(20000 / capacity * 1.3),
        "recompensa_media_10_episodios": float(reward), "recompensa_desviacion": float(std),
        "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "nota": "Una medición local de un hilo no equivale a medir una vCPU de Google Cloud."
    }
    (output / f"resultado_{device}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    env.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--steps", type=int, default=100000)
    parser.add_argument("--output", type=Path, default=Path("evidencias/ia"))
    args = parser.parse_args()
    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA no está disponible. Ejecuta esta variante en Colab con GPU T4.")
    benchmark(args.device, args.steps, args.output)
