from __future__ import annotations

import os
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .common import AppConfig


def _split_command(command: str) -> List[str]:
    if not command.strip():
        return []
    return shlex.split(command, posix=os.name != "nt")


@dataclass
class ModelRegistry:
    root_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1])
    outputs_dir: Path = field(init=False)
    assets_dir: Path = field(init=False)
    models_dir: Path = field(init=False)
    cosyvoice_dir: Path = field(init=False)
    cosyvoice_weights_dir: Path = field(init=False)
    cosyvoice_bridge_script: Path = field(init=False)
    musetalk_dir: Path = field(init=False)
    wav2lip_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.outputs_dir = self.root_dir / "outputs"
        self.assets_dir = self.root_dir / "assets"
        self.models_dir = self.root_dir / "models"
        self.cosyvoice_dir = self.models_dir / "CosyVoice"
        self.cosyvoice_weights_dir = self.cosyvoice_dir / "pretrained_models"
        self.cosyvoice_bridge_script = self.root_dir / "scripts" / "cosyvoice_bridge.py"
        self.musetalk_dir = self.models_dir / "MuseTalk"
        self.wav2lip_dir = self.models_dir / "Wav2Lip"

    @classmethod
    def from_config(cls, config: AppConfig) -> "ModelRegistry":
        registry = cls(root_dir=config.root_dir)
        registry.outputs_dir = config.outputs_dir
        registry.assets_dir = config.assets_dir
        registry.models_dir = config.models_dir
        registry.cosyvoice_dir = Path(os.getenv("DHD_COSYVOICE_DIR", str(registry.models_dir / "CosyVoice"))).resolve()
        registry.cosyvoice_weights_dir = Path(
            os.getenv("DHD_COSYVOICE_WEIGHTS_DIR", str(registry.cosyvoice_dir / "pretrained_models"))
        ).resolve()
        registry.cosyvoice_bridge_script = registry.root_dir / "scripts" / "cosyvoice_bridge.py"
        registry.musetalk_dir = Path(os.getenv("DHD_MUSETALK_DIR", str(registry.models_dir / "MuseTalk"))).resolve()
        registry.wav2lip_dir = Path(os.getenv("DHD_WAV2LIP_DIR", str(registry.models_dir / "Wav2Lip"))).resolve()
        return registry

    def ensure_dirs(self) -> None:
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, str]:
        return {
            "root_dir": str(self.root_dir),
            "outputs_dir": str(self.outputs_dir),
            "assets_dir": str(self.assets_dir),
            "models_dir": str(self.models_dir),
            "cosyvoice_dir": str(self.cosyvoice_dir),
            "cosyvoice_weights_dir": str(self.cosyvoice_weights_dir),
            "cosyvoice_bridge_script": str(self.cosyvoice_bridge_script),
            "musetalk_dir": str(self.musetalk_dir),
            "wav2lip_dir": str(self.wav2lip_dir),
        }

    def backend_dir(self, backend_name: str) -> Path:
        backend_name = backend_name.lower()
        if backend_name == "cosyvoice":
            return self.cosyvoice_dir
        if backend_name == "musetalk":
            return self.musetalk_dir
        if backend_name == "wav2lip":
            return self.wav2lip_dir
        return self.models_dir / backend_name

    def launcher_command(
        self,
        backend_name: str,
        script_candidates: Sequence[str],
        executable: Optional[str] = None,
    ) -> Optional[List[str]]:
        backend_key = backend_name.upper()
        explicit_cmd = os.getenv("DHD_%s_CMD" % backend_key, "").strip()
        if explicit_cmd:
            return _split_command(explicit_cmd)

        explicit_script = os.getenv("DHD_%s_SCRIPT" % backend_key, "").strip()
        if explicit_script:
            script_path = Path(explicit_script)
            if not script_path.is_absolute():
                script_path = self.backend_dir(backend_name) / script_path
            if script_path.exists():
                return [executable or os.sys.executable, str(script_path)]

        backend_dir = self.backend_dir(backend_name)
        for candidate in script_candidates:
            script_path = Path(candidate)
            if not script_path.is_absolute():
                script_path = backend_dir / script_path
            if script_path.exists():
                return [executable or os.sys.executable, str(script_path)]
        return None

    def has_cosyvoice_source(self) -> bool:
        return any(
            [
                (self.cosyvoice_dir / "cosyvoice" / "cli" / "cosyvoice.py").exists(),
                (self.cosyvoice_dir / "example.py").exists(),
                (self.cosyvoice_dir / "webui.py").exists(),
            ]
        )

    def _candidate_cosyvoice_weights(self) -> List[Path]:
        candidates = [
            self.cosyvoice_weights_dir,
            self.cosyvoice_dir / "pretrained_models" / "CosyVoice-300M-SFT",
            self.cosyvoice_dir / "pretrained_models" / "CosyVoice-300M-Instruct",
            self.cosyvoice_dir / "pretrained_models" / "CosyVoice-300M",
            self.cosyvoice_dir / "pretrained_models" / "CosyVoice2-0.5B",
            self.cosyvoice_dir / "pretrained_models" / "Fun-CosyVoice3-0.5B",
            self.cosyvoice_dir / "pretrained_models" / "iic" / "CosyVoice-300M-SFT",
            self.cosyvoice_dir / "pretrained_models" / "iic" / "CosyVoice-300M-Instruct",
            self.cosyvoice_dir / "pretrained_models" / "iic" / "CosyVoice2-0.5B",
            self.cosyvoice_dir / "pretrained_models" / "iic" / "Fun-CosyVoice3-0.5B",
        ]
        return candidates

    def _looks_like_cosyvoice_weights(self, candidate: Path) -> bool:
        if not candidate.exists() or not candidate.is_dir():
            return False
        markers = [
            candidate / "cosyvoice.yaml",
            candidate / "llm.pt",
            candidate / "flow.pt",
            candidate / "hift.pt",
            candidate / "spk2info.pt",
        ]
        return any(marker.exists() for marker in markers)

    def find_cosyvoice_weights(self) -> Optional[Path]:
        explicit = os.getenv("DHD_COSYVOICE_WEIGHTS_DIR", "").strip()
        if explicit:
            candidate = Path(explicit).expanduser().resolve()
            if self._looks_like_cosyvoice_weights(candidate):
                return candidate

        for candidate in self._candidate_cosyvoice_weights():
            if self._looks_like_cosyvoice_weights(candidate):
                return candidate.resolve()

        if self.cosyvoice_dir.exists():
            for marker in self.cosyvoice_dir.rglob("cosyvoice.yaml"):
                if marker.is_file():
                    return marker.parent.resolve()
        return None

    def cosyvoice_ready(self) -> bool:
        return self.has_cosyvoice_source() and self.find_cosyvoice_weights() is not None

    def available_backends(self, script_map: Dict[str, Sequence[str]]) -> Dict[str, bool]:
        result: Dict[str, bool] = {}
        for name, candidates in script_map.items():
            result[name] = self.launcher_command(name, candidates) is not None
        return result

    def summary(self, script_map: Dict[str, Sequence[str]]) -> Dict[str, object]:
        payload = self.to_dict()
        payload["available_backends"] = self.available_backends(script_map)
        payload["cosyvoice_source_ready"] = self.has_cosyvoice_source()
        payload["cosyvoice_weights_found"] = str(self.find_cosyvoice_weights() or "")
        payload["cosyvoice_ready"] = self.cosyvoice_ready()
        return payload


def load_registry(config: AppConfig) -> ModelRegistry:
    registry = ModelRegistry.from_config(config)
    registry.ensure_dirs()
    return registry