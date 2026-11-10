"""Sustituye las imágenes y aplica los manifiestos sin modificar los originales."""
import os
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for name in ["fleet.yaml", "autoscaler.yaml", "podmonitor.yaml", "matchmaker.yaml"]:
    content = (root / "k8s" / name).read_text()
    content = content.replace("NEBULA_SERVER_IMAGE", os.environ["SERVER_IMAGE"])
    content = content.replace("NEBULA_MATCHMAKER_IMAGE", os.environ["MATCHMAKER_IMAGE"])
    subprocess.run(["kubectl", "apply", "-f", "-"], input=content, text=True, check=True)
subprocess.run(["kubectl", "apply", "-f", str(root / "k8s/dashboard.yaml")], check=True)
