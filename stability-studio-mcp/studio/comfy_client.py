from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests


class ComfyUIClient:
    def __init__(self, base_url: str, timeout: int = 600) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client_id = str(uuid.uuid4())
        self._object_info_cache: dict[str, Any] | None = None

    def is_running(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/system_stats", timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def get_system_stats(self) -> dict[str, Any] | None:
        """Return ComfyUI /system_stats payload, or None if unreachable."""
        try:
            r = requests.get(f"{self.base_url}/system_stats", timeout=5)
            if r.status_code != 200:
                return None
            return r.json()
        except requests.RequestException:
            return None

    def get_object_info(self, *, refresh: bool = False) -> dict[str, Any]:
        if self._object_info_cache is not None and not refresh:
            return self._object_info_cache
        r = requests.get(f"{self.base_url}/object_info", timeout=30)
        r.raise_for_status()
        self._object_info_cache = r.json()
        return self._object_info_cache

    def queue_prompt(self, workflow: dict[str, Any]) -> str:
        payload = {"prompt": workflow, "client_id": self.client_id}
        r = requests.post(
            f"{self.base_url}/prompt",
            json=payload,
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"ComfyUI queue failed ({r.status_code}): {r.text}")
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"ComfyUI error: {json.dumps(data['error'])}")
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"ComfyUI returned no prompt_id: {data}")
        return prompt_id

    def wait_for_completion(self, prompt_id: str) -> dict[str, Any]:
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            try:
                hist = self.get_history(prompt_id)
            except requests.RequestException as exc:
                raise RuntimeError(
                    f"ComfyUI connection lost while waiting for prompt {prompt_id}. "
                    "Restart ComfyUI from Stability Matrix and check for GPU OOM in the console."
                ) from exc
            if prompt_id in hist:
                entry = hist[prompt_id]
                status = entry.get("status", {})
                if status.get("completed"):
                    return entry
                if status.get("status_str") == "error":
                    messages = status.get("messages", [])
                    raise RuntimeError(f"ComfyUI generation error: {messages}")
            time.sleep(1.5)
        raise TimeoutError(f"Timed out waiting for ComfyUI prompt {prompt_id}")

    def get_history(self, prompt_id: str | None = None) -> dict[str, Any]:
        url = f"{self.base_url}/history"
        if prompt_id:
            url += f"/{prompt_id}"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.json()

    def collect_outputs(self, history_entry: dict[str, Any]) -> list[dict[str, Any]]:
        outputs = history_entry.get("outputs", {})
        files: list[dict[str, Any]] = []
        for node_id, node_out in outputs.items():
            for image in node_out.get("images", []):
                files.append(
                    {
                        "node_id": node_id,
                        "filename": image.get("filename"),
                        "subfolder": image.get("subfolder", ""),
                        "type": image.get("type", "output"),
                        "view_url": self.view_url(image),
                    }
                )
            for key in ("gifs", "videos"):
                for vid in node_out.get(key, []) or []:
                    files.append(
                        {
                            "node_id": node_id,
                            "filename": vid.get("filename"),
                            "subfolder": vid.get("subfolder", ""),
                            "type": vid.get("type", "output"),
                            "view_url": self.view_url(vid),
                        }
                    )
            for audio in node_out.get("audio", []) or []:
                files.append(
                    {
                        "node_id": node_id,
                        "filename": audio.get("filename"),
                        "subfolder": audio.get("subfolder", ""),
                        "type": audio.get("type", "output"),
                        "view_url": self.view_url(audio),
                    }
                )
        return files

    def view_url(self, file_info: dict[str, Any]) -> str:
        params = {
            "filename": file_info.get("filename", ""),
            "subfolder": file_info.get("subfolder", ""),
            "type": file_info.get("type", "output"),
        }
        return f"{self.base_url}/view?{urlencode(params)}"

    def upload_image(self, path: Path, *, subfolder: str = "", overwrite: bool = True) -> str:
        """Upload a local image to ComfyUI's input folder; returns the stored filename."""
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        with path.open("rb") as handle:
            files = {"image": (path.name, handle, mime)}
            data: dict[str, str] = {
                "type": "input",
                "overwrite": "true" if overwrite else "false",
            }
            if subfolder:
                data["subfolder"] = subfolder
            r = requests.post(
                f"{self.base_url}/upload/image",
                files=files,
                data=data,
                timeout=120,
            )
        if r.status_code != 200:
            raise RuntimeError(f"ComfyUI image upload failed ({r.status_code}): {r.text}")
        payload = r.json()
        name = payload.get("name")
        if not name:
            raise RuntimeError(f"ComfyUI upload returned no filename: {payload}")
        return str(name)

    def get_queue(self) -> dict[str, Any]:
        r = requests.get(f"{self.base_url}/queue", timeout=10)
        r.raise_for_status()
        return r.json()

    def interrupt(self) -> None:
        r = requests.post(f"{self.base_url}/interrupt", timeout=10)
        r.raise_for_status()

    def clear_queue(self) -> None:
        r = requests.post(f"{self.base_url}/queue", json={"clear": True}, timeout=10)
        r.raise_for_status()

    def cancel_all(self, *, repeats: int = 3) -> dict[str, int]:
        """Interrupt running work and clear pending queue. May not stop a CUDA hang."""
        for _ in range(repeats):
            try:
                self.interrupt()
            except requests.RequestException:
                pass
            time.sleep(1.0)
        try:
            self.clear_queue()
        except requests.RequestException:
            pass
        q = self.get_queue()
        return {
            "running": len(q.get("queue_running", [])),
            "pending": len(q.get("queue_pending", [])),
        }

    def download_file(self, file_info: dict[str, Any], dest_dir: Path) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        url = self.view_url(file_info)
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        out = dest_dir / file_info["filename"]
        out.write_bytes(r.content)
        return out
