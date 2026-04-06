from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import types
import wave
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
MKL_BIN_DIR = ROOT_DIR / ".mkl_bin"
HF_HOME_DIR = ROOT_DIR / ".cache" / "huggingface"


def _prepend_path(path: Path) -> None:
    if path.exists():
        resolved = str(path.resolve())
        if resolved not in sys.path:
            sys.path.insert(0, resolved)


def _add_dll_directory(path: Path) -> None:
    if not path.exists():
        return
    resolved = str(path.resolve())
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(resolved)
    current_path = os.environ.get("PATH", "")
    parts = current_path.split(";") if current_path else []
    if resolved not in parts:
        os.environ["PATH"] = resolved + (";" + current_path if current_path else "")


def _configure_imports(repo_dir: Path) -> None:
    HF_HOME_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(HF_HOME_DIR))
    os.environ.setdefault("HF_HUB_CACHE", str(HF_HOME_DIR / "hub"))
    os.environ.setdefault("HF_ASSETS_CACHE", str(HF_HOME_DIR / "assets"))
    _add_dll_directory(MKL_BIN_DIR)
    _prepend_path(ROOT_DIR)
    _prepend_path(repo_dir)
    third_party = repo_dir / "third_party"
    if third_party.exists():
        for child in sorted(third_party.iterdir()):
            if child.is_dir():
                _prepend_path(child)
                src_dir = child / "src"
                if src_dir.exists():
                    _prepend_path(src_dir)


def _patch_runtime() -> None:
    checkpoint_mod = types.ModuleType("torch.utils.checkpoint")

    def _checkpoint(function, *args, **kwargs):
        return function(*args, **kwargs)

    checkpoint_mod.checkpoint = _checkpoint
    sys.modules["torch.utils.checkpoint"] = checkpoint_mod


def _resolve_bool(value: str, default: bool = True) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_text(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return cleaned
    if cleaned[-1] not in ".!?;,:，。！？；：":
        cleaned += "。"
    return cleaned


def _tensor_to_pcm16(tensor) -> bytes:
    if hasattr(tensor, "detach"):
        tensor = tensor.detach()
    if hasattr(tensor, "cpu"):
        tensor = tensor.cpu()
    if hasattr(tensor, "float"):
        tensor = tensor.float()
    if hasattr(tensor, "flatten"):
        tensor = tensor.flatten()
    values = tensor.tolist() if hasattr(tensor, "tolist") else list(tensor)
    frame = bytearray()
    for value in values:
        sample = int(round(float(value) * 32767.0))
        if sample > 32767:
            sample = 32767
        elif sample < -32768:
            sample = -32768
        frame.extend(struct.pack("<h", sample))
    return bytes(frame)


def _choose_model_class(weights_dir: Path, explicit_kind: str) -> str:
    explicit_kind = (explicit_kind or "").strip().lower()
    if explicit_kind in {"2", "cosyvoice2", "cosyvoice3", "v2", "v3"}:
        return "cosyvoice2"
    if explicit_kind in {"1", "cosyvoice", "cosyvoice1", "base"}:
        return "cosyvoice"

    name = weights_dir.name.lower()
    if any(token in name for token in ["cosyvoice2", "fun-cosyvoice3", "cosyvoice3"]):
        return "cosyvoice2"
    return "cosyvoice"


def _preferred_speakers() -> list[str]:
    return ["中文女", "中文男", "粤语女", "英文女", "英文男", "日语男", "韩语女"]


def _pick_speaker(model, requested: str) -> str:
    available = []
    if hasattr(model, "list_available_spks"):
        try:
            available = list(model.list_available_spks())
        except Exception:
            available = []
    if requested and (not available or requested in available):
        return requested
    for candidate in _preferred_speakers():
        if candidate in available:
            return candidate
    return available[0] if available else (requested or "")


def _load_model(repo_dir: Path, weights_dir: Path, explicit_kind: str):
    _configure_imports(repo_dir)
    _patch_runtime()
    try:
        from cosyvoice.cli.cosyvoice import CosyVoice, CosyVoice2
    except Exception as exc:
        raise RuntimeError(
            "Unable to import official CosyVoice code. Make sure the repo exists under models/CosyVoice and its runtime dependencies are available."
        ) from exc

    model_kind = _choose_model_class(weights_dir, explicit_kind)
    model_cls = CosyVoice2 if model_kind == "cosyvoice2" else CosyVoice
    init_kwargs = (
        [
            {"load_jit": False, "load_trt": False, "load_vllm": False, "fp16": False},
            {"load_jit": True, "load_onnx": False, "fp16": True},
            {},
        ]
        if model_kind == "cosyvoice2"
        else [
            {"load_jit": True, "load_onnx": False, "fp16": True},
            {},
        ]
    )
    last_error: Exception | None = None
    for kwargs in init_kwargs:
        try:
            return model_cls(str(weights_dir), **kwargs)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Failed to initialize CosyVoice: {last_error}") from last_error


def _write_streaming_wav(model, outputs: Iterable[dict], out_path: Path) -> int:
    sample_rate = getattr(model, "sample_rate", None)
    if sample_rate is None:
        raise RuntimeError("CosyVoice instance does not expose sample_rate.")

    total_frames = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(int(sample_rate))
        for item in outputs:
            speech = item.get("tts_speech")
            if speech is None:
                continue
            pcm_bytes = _tensor_to_pcm16(speech)
            wav_file.writeframesraw(pcm_bytes)
            total_frames += len(pcm_bytes) // 2
    if total_frames <= 0:
        raise RuntimeError("CosyVoice produced no audio frames.")
    return int(sample_rate)


def _load_wav_helper():
    try:
        from cosyvoice.utils.file_utils import load_wav
    except Exception as exc:
        raise RuntimeError("Unable to import CosyVoice load_wav helper.") from exc
    return load_wav


def _run_sft(model, text: str, spk_id: str, text_frontend: bool, out_path: Path) -> int:
    speaker = _pick_speaker(model, spk_id)
    if not speaker:
        raise RuntimeError("No usable SFT speaker was found in the CosyVoice checkpoint.")
    outputs = model.inference_sft(
        _normalize_text(text),
        speaker,
        stream=True,
        text_frontend=text_frontend,
    )
    return _write_streaming_wav(model, outputs, out_path)


def _run_zero_shot(
    model,
    text: str,
    prompt_text: str,
    prompt_wav: Path,
    zero_shot_spk_id: str,
    text_frontend: bool,
    out_path: Path,
) -> int:
    load_wav = _load_wav_helper()
    prompt_audio = load_wav(str(prompt_wav), 16000)
    outputs = model.inference_zero_shot(
        _normalize_text(text),
        _normalize_text(prompt_text),
        prompt_audio,
        zero_shot_spk_id=zero_shot_spk_id,
        stream=True,
        text_frontend=text_frontend,
    )
    return _write_streaming_wav(model, outputs, out_path)


def _run_instruct2(
    model,
    text: str,
    instruct_text: str,
    prompt_wav: Path,
    zero_shot_spk_id: str,
    text_frontend: bool,
    out_path: Path,
) -> int:
    load_wav = _load_wav_helper()
    prompt_audio = load_wav(str(prompt_wav), 16000)
    outputs = model.inference_instruct2(
        _normalize_text(text),
        _normalize_text(instruct_text),
        prompt_audio,
        zero_shot_spk_id=zero_shot_spk_id,
        stream=True,
        text_frontend=text_frontend,
    )
    return _write_streaming_wav(model, outputs, out_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CosyVoice bridge for Lite Digital Human")
    parser.add_argument("--repo-dir", default=os.getenv("DHD_COSYVOICE_REPO_DIR", ""), help="CosyVoice repository root")
    parser.add_argument("--weights-dir", default=os.getenv("DHD_COSYVOICE_WEIGHTS_DIR", ""), help="CosyVoice pretrained model directory")
    parser.add_argument("--mode", default=os.getenv("DHD_COSYVOICE_MODE", "auto"), help="auto, sft, zero_shot or instruct2")
    parser.add_argument("--model-kind", default=os.getenv("DHD_COSYVOICE_MODEL_KIND", ""), help="Explicit CosyVoice model family")
    parser.add_argument("--spk-id", default=os.getenv("DHD_COSYVOICE_SPK_ID", ""), help="SFT speaker id")
    parser.add_argument("--zero-shot-spk-id", default=os.getenv("DHD_COSYVOICE_ZERO_SHOT_SPK_ID", ""), help="Zero-shot speaker id")
    parser.add_argument("--prompt-text", default=os.getenv("DHD_COSYVOICE_PROMPT_TEXT", ""), help="Zero-shot prompt text")
    parser.add_argument("--prompt-wav", default=os.getenv("DHD_COSYVOICE_PROMPT_WAV", ""), help="Zero-shot prompt wav")
    parser.add_argument("--instruct-text", default=os.getenv("DHD_COSYVOICE_INSTRUCT_TEXT", ""), help="Instruct text for CosyVoice2")
    parser.add_argument("--text-frontend", default=os.getenv("DHD_COSYVOICE_TEXT_FRONTEND", "1"), help="Use CosyVoice text frontend")
    parser.add_argument("--text", default=os.getenv("DHD_TTS_TEXT", ""), help="Text to synthesize")
    parser.add_argument("--out", default=os.getenv("DHD_TTS_OUT", ""), help="Output wav path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.repo_dir:
        raise SystemExit("Missing --repo-dir or DHD_COSYVOICE_REPO_DIR")
    if not args.weights_dir:
        raise SystemExit("Missing --weights-dir or DHD_COSYVOICE_WEIGHTS_DIR")
    if not args.text:
        raise SystemExit("Missing text to synthesize")
    if not args.out:
        raise SystemExit("Missing output wav path")

    repo_dir = Path(args.repo_dir).expanduser().resolve()
    weights_dir = Path(args.weights_dir).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()

    if not repo_dir.exists():
        raise SystemExit(f"CosyVoice repo directory does not exist: {repo_dir}")
    if not weights_dir.exists():
        raise SystemExit(f"CosyVoice weights directory does not exist: {weights_dir}")

    model = _load_model(repo_dir, weights_dir, args.model_kind)
    text_frontend = _resolve_bool(args.text_frontend, True)
    mode = (args.mode or "auto").strip().lower()
    if mode == "auto":
        if args.prompt_wav and args.prompt_text:
            mode = "zero_shot"
        elif args.prompt_wav and args.instruct_text:
            mode = "instruct2"
        else:
            mode = "sft"

    if mode == "zero_shot":
        if not args.prompt_wav or not args.prompt_text:
            raise SystemExit("zero_shot mode requires both --prompt-wav and --prompt-text")
        _run_zero_shot(model, args.text, args.prompt_text, Path(args.prompt_wav), args.zero_shot_spk_id, text_frontend, out_path)
    elif mode == "instruct2":
        if not args.prompt_wav or not args.instruct_text:
            raise SystemExit("instruct2 mode requires both --prompt-wav and --instruct-text")
        _run_instruct2(model, args.text, args.instruct_text, Path(args.prompt_wav), args.zero_shot_spk_id, text_frontend, out_path)
    elif mode == "sft":
        _run_sft(model, args.text, args.spk_id, text_frontend, out_path)
    else:
        raise SystemExit(f"Unsupported CosyVoice mode: {mode}")

    print(
        json.dumps(
            {
                "backend": "cosyvoice",
                "mode": mode,
                "repo_dir": str(repo_dir),
                "weights_dir": str(weights_dir),
                "out": str(out_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
