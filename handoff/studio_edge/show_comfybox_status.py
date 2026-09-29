#!/usr/bin/env python3
"""Run on Myra (Pi): put ComfyBox status on the kiosk."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path.home() / "studio-edge"))
import yaml
from studio_edge.display import show_comfybox_status

cfg = yaml.safe_load((Path.home() / "studio-edge" / "config.yaml").read_text())
print(show_comfybox_status(cfg))
