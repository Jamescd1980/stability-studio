from __future__ import annotations

import time
from typing import Any

import requests


class InvokeAIClient:
    def __init__(self, base_url: str, timeout: int = 600) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def is_running(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/v1/models/", timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def list_models(self, model_type: str = "main") -> list[dict[str, Any]]:
        r = requests.get(
            f"{self.base_url}/api/v1/models/",
            params={"model_type": model_type},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("items", data if isinstance(data, list) else [])

    def generate_image_simple(
        self,
        *,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 30,
        cfg_scale: float = 7.5,
        seed: int | None = None,
        model_key: str | None = None,
        lora_key: str | None = None,
        lora_weight: float = 0.75,
    ) -> dict[str, Any]:
        """Queue generation via InvokeAI — requires a compatible graph template."""
        models = self.list_models("main")
        if not models:
            raise RuntimeError("No InvokeAI main models found")

        chosen = None
        if model_key:
            for m in models:
                if m.get("key") == model_key or m.get("name") == model_key:
                    chosen = m
                    break
        if not chosen:
            chosen = models[0]

        model_hash = chosen.get("hash") or chosen.get("model_hash", "")
        model_name = chosen.get("name", "model")
        key = chosen.get("key", model_name)

        graph = self._build_txt2img_graph(
            prompt=prompt,
            negative_prompt=negative_prompt or "blurry, low quality",
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale,
            seed=seed or int(time.time()) % 2_000_000_000,
            model_key=key,
            model_hash=model_hash,
            model_name=model_name,
            base=chosen.get("base", "sdxl"),
            lora_key=lora_key,
            lora_weight=lora_weight,
        )

        payload = {
            "batch": {
                "graph": graph,
                "origin": "api",
                "destination": "gallery",
            }
        }

        r = requests.post(
            f"{self.base_url}/api/v1/queue/default/enqueue_batch",
            json=payload,
            timeout=60,
        )
        if r.status_code != 200:
            raise RuntimeError(f"InvokeAI enqueue failed ({r.status_code}): {r.text}")

        batch_id = r.json().get("batch_id") or r.json().get("batch", {}).get("batch_id")
        return self._wait_for_batch(batch_id)

    def _build_txt2img_graph(
        self,
        *,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        cfg_scale: float,
        seed: int,
        model_key: str,
        model_hash: str,
        model_name: str,
        base: str,
        lora_key: str | None,
        lora_weight: float,
    ) -> dict[str, Any]:
        is_sdxl = "xl" in base.lower() or "sdxl" in model_name.lower()
        prompt_type = "sdxl_compel_prompt" if is_sdxl else "compel"
        model_loader_type = "sdxl_model_loader" if is_sdxl else "main_model_loader"

        nodes: dict[str, Any] = {
            "model_loader": {
                "id": "model_loader",
                "type": model_loader_type,
                "model": {
                    "key": model_key,
                    "hash": model_hash,
                    "name": model_name,
                    "base": base,
                    "type": "main",
                },
            },
            "pos_prompt": {
                "id": "pos_prompt",
                "type": prompt_type,
                "prompt": prompt,
            },
            "neg_prompt": {
                "id": "neg_prompt",
                "type": prompt_type,
                "prompt": negative_prompt,
            },
            "noise": {
                "id": "noise",
                "type": "noise",
                "width": width,
                "height": height,
                "seed": seed,
            },
            "denoise": {
                "id": "denoise",
                "type": "denoise_latents",
                "steps": steps,
                "cfg_scale": cfg_scale,
                "scheduler": "euler",
            },
            "l2i": {"id": "l2i", "type": "l2i"},
        }

        edges = [
            {"source": {"node_id": "model_loader", "field": "unet"}, "destination": {"node_id": "denoise", "field": "unet"}},
            {"source": {"node_id": "model_loader", "field": "clip"}, "destination": {"node_id": "pos_prompt", "field": "clip"}},
            {"source": {"node_id": "model_loader", "field": "clip"}, "destination": {"node_id": "neg_prompt", "field": "clip"}},
            {"source": {"node_id": "pos_prompt", "field": "conditioning"}, "destination": {"node_id": "denoise", "field": "positive_conditioning"}},
            {"source": {"node_id": "neg_prompt", "field": "conditioning"}, "destination": {"node_id": "denoise", "field": "negative_conditioning"}},
            {"source": {"node_id": "noise", "field": "noise"}, "destination": {"node_id": "denoise", "field": "noise"}},
            {"source": {"node_id": "denoise", "field": "latents"}, "destination": {"node_id": "l2i", "field": "latents"}},
            {"source": {"node_id": "model_loader", "field": "vae"}, "destination": {"node_id": "l2i", "field": "vae"}},
        ]

        if lora_key:
            loras = self.list_models("lora")
            lora = next((m for m in loras if m.get("key") == lora_key or m.get("name") == lora_key), None)
            if lora:
                nodes["lora_loader"] = {
                    "id": "lora_loader",
                    "type": "sdxl_lora_loader" if is_sdxl else "lora_loader",
                    "lora": {"key": lora["key"], "name": lora.get("name", lora["key"])},
                    "weight": lora_weight,
                }
                edges = [
                    {"source": {"node_id": "model_loader", "field": "unet"}, "destination": {"node_id": "lora_loader", "field": "unet"}},
                    {"source": {"node_id": "model_loader", "field": "clip"}, "destination": {"node_id": "lora_loader", "field": "clip"}},
                    {"source": {"node_id": "lora_loader", "field": "unet"}, "destination": {"node_id": "denoise", "field": "unet"}},
                    {"source": {"node_id": "lora_loader", "field": "clip"}, "destination": {"node_id": "pos_prompt", "field": "clip"}},
                    {"source": {"node_id": "lora_loader", "field": "clip"}, "destination": {"node_id": "neg_prompt", "field": "clip"}},
                    edges[5],
                    edges[6],
                ]

        return {"nodes": nodes, "edges": edges}

    def _wait_for_batch(self, batch_id: str | None) -> dict[str, Any]:
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            r = requests.get(f"{self.base_url}/api/v1/queue/default/current", timeout=15)
            if r.status_code == 200:
                data = r.json()
                if not data.get("item_ids"):
                    return {"status": "completed", "batch_id": batch_id, "note": "Check InvokeAI gallery for output"}
            time.sleep(2)
        return {"status": "timeout", "batch_id": batch_id, "note": "Generation may still be running in InvokeAI gallery"}
