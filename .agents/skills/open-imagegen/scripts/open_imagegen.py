#!/usr/bin/env python3
"""Local, open-source image generation and editing for Codex.

The default runtime is FLUX.2 [klein] 4B through Hugging Face Diffusers. Heavy
ML dependencies are imported lazily so model discovery, dry-runs, and tests are
fast and work before the runtime is installed.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import platform
import re
import sys
import time
from typing import Any, Iterable, Sequence

FIELD_BOOK_ROOT = Path(__file__).resolve().parents[4]
FIELD_BOOK_SRC = FIELD_BOOK_ROOT / "src"
if str(FIELD_BOOK_SRC) not in sys.path:
    sys.path.insert(0, str(FIELD_BOOK_SRC))

from rogue_ai_fieldbook.core import file_sha256, portable_path, write_metadata


DEFAULT_MODEL = "flux2-klein-4b"
DEFAULT_OUTPUT = "output/open-imagegen/output.png"
BIREFNET_MODEL = "ZhengPeng7/BiRefNet-matting"
BIREFNET_REVISION = "eccde0a8cbdce7ac5fecfeb06340fe7b949e85d9"
MAX_BATCH_JOBS = 100
ALLOWED_FORMATS = {"png", "jpeg", "webp"}
ALLOWED_QUALITIES = {"draft", "standard", "high"}
ALLOWED_OFFLOAD = {"auto", "balanced", "model", "sequential", "none"}
ALLOWED_MASK_MODES = {"edit-white", "preserve-white"}


@dataclass(frozen=True)
class ModelSpec:
    alias: str
    repo_id: str
    pipeline_class: str
    modes: tuple[str, ...]
    license: str
    default_steps: int
    draft_steps: int
    high_steps: int
    guidance_scale: float
    min_vram_gb: int
    default_offload: str
    strengths: str
    tested_here: bool = False
    runtime: str = "diffusers"
    gguf_repo_id: str | None = None
    gguf_filename: str | None = None


MODELS: dict[str, ModelSpec] = {
    "sensenova-u1.5-q8": ModelSpec(
        alias="sensenova-u1.5-q8",
        repo_id="sensenova/SenseNova-U1.5-8B-MoT",
        pipeline_class="SenseNovaU15Pipeline",
        modes=("generate", "edit"),
        license="Apache-2.0",
        default_steps=50,
        draft_steps=20,
        high_steps=50,
        guidance_scale=4.0,
        min_vram_gb=12,
        default_offload="balanced",
        strengths="Final-quality generation/editing, people, identity, and multi-reference composition",
        tested_here=True,
        runtime="sensenova",
        gguf_repo_id="realrebelai/SenseNova-U1.5-8B_GGUFs",
        gguf_filename="SenseNova-U1.5-8B-MoT-Q8_0.gguf",
    ),
    "flux2-klein-4b": ModelSpec(
        alias="flux2-klein-4b",
        repo_id="black-forest-labs/FLUX.2-klein-4B",
        pipeline_class="Flux2KleinPipeline",
        modes=("generate", "edit"),
        license="Apache-2.0",
        default_steps=4,
        draft_steps=2,
        high_steps=4,
        guidance_scale=1.0,
        min_vram_gb=8,
        default_offload="model",
        strengths="Best local default; fast generation, single/multi-reference editing",
        tested_here=True,
    ),
    "z-image-turbo": ModelSpec(
        alias="z-image-turbo",
        repo_id="Tongyi-MAI/Z-Image-Turbo",
        pipeline_class="ZImagePipeline",
        modes=("generate",),
        license="Apache-2.0",
        default_steps=8,
        draft_steps=4,
        high_steps=9,
        guidance_scale=0.0,
        min_vram_gb=12,
        default_offload="sequential",
        strengths="Strong aesthetics and efficient text-to-image generation",
    ),
    "ernie-image-turbo": ModelSpec(
        alias="ernie-image-turbo",
        repo_id="baidu/ERNIE-Image-Turbo",
        pipeline_class="ErnieImagePipeline",
        modes=("generate",),
        license="Apache-2.0",
        default_steps=8,
        draft_steps=4,
        high_steps=8,
        guidance_scale=1.0,
        min_vram_gb=12,
        default_offload="sequential",
        strengths="Typography, posters, infographics, and structured layouts",
    ),
    "qwen-image-2512": ModelSpec(
        alias="qwen-image-2512",
        repo_id="Qwen/Qwen-Image-2512",
        pipeline_class="QwenImagePipeline",
        modes=("generate",),
        license="Apache-2.0",
        default_steps=40,
        draft_steps=20,
        high_steps=50,
        guidance_scale=4.0,
        min_vram_gb=12,
        default_offload="sequential",
        strengths="High-quality generation, realism, and accurate visible text; slow on 12 GB",
    ),
    "qwen-image-edit-2511": ModelSpec(
        alias="qwen-image-edit-2511",
        repo_id="Qwen/Qwen-Image-Edit-2511",
        pipeline_class="QwenImageEditPlusPipeline",
        modes=("edit",),
        license="Apache-2.0",
        default_steps=40,
        draft_steps=20,
        high_steps=50,
        guidance_scale=4.0,
        min_vram_gb=12,
        default_offload="sequential",
        strengths="Geometry/identity specialist for complex 1-3 reference edits; very slow on 12 GB",
        tested_here=True,
    ),
}


def die(message: str, code: int = 2) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(code)


def warn(message: str) -> None:
    print(f"Warning: {message}", file=sys.stderr)


def repo_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "catalog.json").is_file() or (parent / ".git").exists():
            return parent
    return None


def default_cache_dir() -> Path:
    explicit = os.getenv("OPEN_IMAGEGEN_CACHE") or os.getenv("HF_HOME")
    if explicit:
        return Path(explicit).expanduser().resolve()
    root = repo_root()
    if root:
        return root / ".local" / "huggingface"
    return Path.home() / ".cache" / "open-imagegen" / "huggingface"


def activate_local_packages() -> None:
    """Prefer optional repo-local packages without mutating the global environment."""
    root = repo_root()
    if not root:
        return
    local_packages = root / ".local" / "python-packages"
    if local_packages.is_dir() and str(local_packages) not in sys.path:
        sys.path.insert(0, str(local_packages))


def parse_size(raw: str) -> tuple[int, int]:
    match = re.fullmatch(r"([1-9][0-9]*)x([1-9][0-9]*)", raw.strip().lower())
    if not match:
        die("size must use WIDTHxHEIGHT, for example 1024x1024")
    width, height = int(match.group(1)), int(match.group(2))
    if width < 256 or height < 256:
        die("width and height must each be at least 256 pixels")
    if width > 2048 or height > 2048:
        die("this local runtime caps each edge at 2048 pixels")
    if width % 16 or height % 16:
        die("width and height must be multiples of 16 pixels")
    if width * height > 4_194_304:
        die("the local runtime caps direct generation at 4,194,304 pixels")
    if max(width, height) / min(width, height) > 3:
        die("the long-to-short edge ratio must not exceed 3:1")
    return width, height


def parse_region(raw: str) -> tuple[int, int, int, int]:
    match = re.fullmatch(
        r"\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*([1-9][0-9]*)\s*,\s*([1-9][0-9]*)\s*",
        raw,
    )
    if not match:
        die("region must use X,Y,WIDTH,HEIGHT")
    return tuple(int(value) for value in match.groups())  # type: ignore[return-value]


def snap_size(width: int, height: int) -> tuple[int, int]:
    width = max(256, min(2048, round(width / 16) * 16))
    height = max(256, min(2048, round(height / 16) * 16))
    scale = min(1.0, (4_194_304 / (width * height)) ** 0.5)
    if scale < 1.0:
        width = max(256, (int(width * scale) // 16) * 16)
        height = max(256, (int(height * scale) // 16) * 16)
    return width, height


def normalize_format(raw: str | None, out: Path) -> str:
    fmt = (raw or out.suffix.lstrip(".") or "png").lower()
    if fmt == "jpg":
        fmt = "jpeg"
    if fmt not in ALLOWED_FORMATS:
        die("output format must be png, jpeg, or webp")
    return fmt


def read_prompt(prompt: str | None, prompt_file: str | None) -> str:
    if prompt and prompt_file:
        die("use --prompt or --prompt-file, not both")
    if prompt_file:
        path = Path(prompt_file)
        if not path.is_file():
            die(f"prompt file not found: {path}")
        value = path.read_text(encoding="utf-8").strip()
    else:
        value = (prompt or "").strip()
    if not value:
        die("a non-empty prompt is required")
    return value


def prompt_fields(args: argparse.Namespace) -> dict[str, str | None]:
    return {
        "use_case": getattr(args, "use_case", None),
        "asset_type": getattr(args, "asset_type", None),
        "scene": getattr(args, "scene", None),
        "subject": getattr(args, "subject", None),
        "style": getattr(args, "style", None),
        "composition": getattr(args, "composition", None),
        "lighting": getattr(args, "lighting", None),
        "palette": getattr(args, "palette", None),
        "materials": getattr(args, "materials", None),
        "text": getattr(args, "text", None),
        "constraints": getattr(args, "constraints", None),
        "negative": getattr(args, "negative", None),
    }


def augment_prompt(prompt: str, fields: dict[str, str | None], enabled: bool) -> str:
    if not enabled:
        return prompt
    labels = (
        ("Use case", "use_case"),
        ("Asset type", "asset_type"),
        ("Primary request", None),
        ("Scene/backdrop", "scene"),
        ("Subject", "subject"),
        ("Style/medium", "style"),
        ("Composition/framing", "composition"),
        ("Lighting/mood", "lighting"),
        ("Color palette", "palette"),
        ("Materials/textures", "materials"),
        ("Text (verbatim)", "text"),
        ("Constraints", "constraints"),
        ("Avoid", "negative"),
    )
    lines: list[str] = []
    for label, key in labels:
        value = prompt if key is None else fields.get(key)
        if value:
            if key == "text":
                value = f'"{value}"'
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def model_spec(alias: str, mode: str | None = None) -> ModelSpec:
    if alias == "auto":
        alias = DEFAULT_MODEL
    spec = MODELS.get(alias)
    if not spec:
        die(f"unknown model '{alias}'; run the models command to list valid aliases")
    if mode and mode not in spec.modes:
        die(f"model '{alias}' does not support {mode}; supported modes: {', '.join(spec.modes)}")
    return spec


def quality_steps(spec: ModelSpec, quality: str, override: int | None) -> int:
    if override is not None:
        if not 1 <= override <= 100:
            die("--steps must be between 1 and 100")
        return override
    if quality == "draft":
        return spec.draft_steps
    if quality == "high":
        return spec.high_steps
    return spec.default_steps


def output_paths(out: str, out_dir: str | None, count: int, fmt: str) -> list[Path]:
    ext = ".jpg" if fmt == "jpeg" else f".{fmt}"
    if out_dir:
        base = Path(out_dir)
        return [base / f"image_{index}{ext}" for index in range(1, count + 1)]
    target = Path(out)
    if not target.suffix or target.suffix.lower() not in {ext, ".jpg" if fmt == "jpeg" else ext}:
        target = target.with_suffix(ext)
    if count == 1:
        return [target]
    return [target.with_name(f"{target.stem}-{index}{target.suffix}") for index in range(1, count + 1)]


def raw_edit_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}.raw-edit{output.suffix}")


def ensure_writable(paths: Sequence[Path], force: bool, dry_run: bool) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing and not force:
        die("refusing to overwrite existing output(s): " + ", ".join(existing))
    if not dry_run:
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)


def resolve_images(raw_paths: Iterable[str]) -> list[Path]:
    paths = [Path(raw).expanduser().resolve() for raw in raw_paths]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        die("input image(s) not found: " + ", ".join(missing))
    return paths


def resolve_image_roles(
    raw_roles: Sequence[str], image_count: int, command: str
) -> tuple[list[str], bool]:
    roles = [role.strip() for role in raw_roles]
    if any(not role for role in roles):
        die("--image-role values cannot be empty")
    if roles and len(roles) != image_count:
        die("repeat --image-role exactly once for every --image")
    if roles:
        return roles, True
    if command == "edit" and image_count:
        return ["edit target", *(["supporting reference"] * (image_count - 1))], False
    return ["supporting reference"] * image_count, False


def prepend_image_roles(prompt: str, roles: Sequence[str]) -> str:
    if not roles:
        return prompt
    lines = ["Input image roles:"]
    lines.extend(f"Image {index}: {role}" for index, role in enumerate(roles, 1))
    return "\n".join(lines) + "\n" + prompt


def cache_has_model(cache_dir: Path, repo_id: str) -> bool:
    folder = "models--" + repo_id.replace("/", "--")
    return (cache_dir / "hub" / folder).is_dir() or (cache_dir / folder).is_dir()


def hub_cache_dir(cache_dir: Path) -> Path:
    return cache_dir if cache_dir.name == "hub" else cache_dir / "hub"


def registered_gguf_is_cached(spec: ModelSpec, cache_dir: Path) -> bool:
    if not spec.gguf_repo_id or not spec.gguf_filename:
        return True
    if cache_has_model(cache_dir, spec.gguf_repo_id):
        return True
    root = repo_root()
    return bool(
        root
        and (root / ".local" / "models" / spec.alias / spec.gguf_filename).is_file()
    )


def cuda_summary() -> dict[str, Any]:
    try:
        import torch

        if not torch.cuda.is_available():
            return {"available": False}
        props = torch.cuda.get_device_properties(0)
        return {
            "available": True,
            "name": props.name,
            "vram_gb": round(props.total_memory / 1024**3, 2),
            "compute_capability": f"{props.major}.{props.minor}",
            "bf16": bool(torch.cuda.is_bf16_supported()),
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
        }
    except Exception as exc:  # doctor must remain useful in partial environments
        return {"available": False, "error": str(exc)}


def system_ram_gb() -> float | None:
    try:
        import psutil

        return round(psutil.virtual_memory().total / 1024**3, 2)
    except Exception:
        return None


def runtime_versions() -> dict[str, str | None]:
    result: dict[str, str | None] = {"python": platform.python_version()}
    for package in ("torch", "diffusers", "transformers", "accelerate", "PIL"):
        try:
            module = __import__(package)
            result[package] = getattr(module, "__version__", "unknown")
        except Exception:
            result[package] = None
    try:
        import sensenova_u1

        result["sensenova_u1"] = getattr(sensenova_u1, "__version__", "unknown")
    except ImportError:
        result["sensenova_u1"] = None
    return result


def transparency_runtime_versions() -> dict[str, str | None]:
    activate_local_packages()
    result: dict[str, str | None] = {}
    for package in ("torchvision", "einops", "kornia", "timm"):
        try:
            module = __import__(package)
            result[package] = getattr(module, "__version__", "unknown")
        except Exception:
            result[package] = None
    return result


def require_runtime() -> tuple[Any, Any]:
    try:
        import torch
        import diffusers
    except ImportError as exc:
        die(
            f"missing runtime dependency '{exc.name}'. Run setup.ps1 or install requirements.txt"
        )
    if not torch.cuda.is_available():
        die("a CUDA-capable NVIDIA GPU is required for this runtime")
    return torch, diffusers


def effective_offload(spec: ModelSpec, requested: str, vram_gb: float) -> str:
    if requested != "auto":
        return requested
    if spec.runtime == "sensenova":
        return "balanced"
    if spec.alias == "flux2-klein-4b" and vram_gb >= 12:
        return "model"
    return spec.default_offload


def resolve_sensenova_gguf(
    spec: ModelSpec,
    *,
    cache_dir: Path,
    explicit: str | None,
    local_files_only: bool,
) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            die(f"GGUF checkpoint not found: {path}")
        return path
    if not spec.gguf_repo_id or not spec.gguf_filename:
        die(f"model '{spec.alias}' does not define a GGUF checkpoint")
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        die("huggingface_hub is missing; install requirements.txt")
    return Path(
        hf_hub_download(
            repo_id=spec.gguf_repo_id,
            filename=spec.gguf_filename,
            cache_dir=str(hub_cache_dir(cache_dir)),
            local_files_only=local_files_only,
        )
    ).resolve()


def resolve_sensenova_resources(
    spec: ModelSpec,
    *,
    cache_dir: Path,
    revision: str | None,
    local_files_only: bool,
) -> Path:
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        die("huggingface_hub is missing; install requirements.txt")
    return Path(
        snapshot_download(
            repo_id=spec.repo_id,
            revision=revision,
            cache_dir=str(hub_cache_dir(cache_dir)),
            local_files_only=local_files_only,
            ignore_patterns=("*.safetensors", "*.bin"),
        )
    ).resolve()


def patch_sensenova_gguf_compute_dtype() -> None:
    """Work around byte-weight dtype lookup in the current upstream GGUF path."""
    from sensenova_u1.models.neo_unify.modeling_fm_modules import (
        FlowMatchingHead,
        TimestepEmbedder,
    )

    if getattr(TimestepEmbedder, "_open_imagegen_gguf_patch", False):
        return

    def timestep_forward(self: Any, timestep: Any) -> Any:
        timestep_freq = self.timestep_embedding(timestep, self.frequency_embedding_size)
        first_layer = self.mlp[0]
        compute_dtype = getattr(first_layer, "compute_dtype", first_layer.weight.dtype)
        return self.mlp(timestep_freq.to(compute_dtype))

    def flow_matching_dtype(self: Any) -> Any:
        layer = self.net.input_proj
        return getattr(layer, "compute_dtype", layer.weight.dtype)

    TimestepEmbedder.forward = timestep_forward
    TimestepEmbedder._open_imagegen_gguf_patch = True
    FlowMatchingHead.dtype = property(flow_matching_dtype)


def sensenova_tensor_to_pil(batch: Any) -> list[Any]:
    import numpy as np
    import torch
    from PIL import Image

    mean = torch.tensor((0.5, 0.5, 0.5), device=batch.device, dtype=batch.dtype).view(1, 3, 1, 1)
    std = torch.tensor((0.5, 0.5, 0.5), device=batch.device, dtype=batch.dtype).view(1, 3, 1, 1)
    array = (batch.float() * std + mean).clamp(0, 1).permute(0, 2, 3, 1).cpu().numpy()
    array = (array * 255.0).round().astype(np.uint8)
    return [Image.fromarray(item) for item in array]


class SenseNovaU15PipelineAdapter:
    def __init__(
        self,
        model_path: str,
        *,
        gguf_checkpoint: Path,
        dtype: Any,
        offload: str,
    ) -> None:
        try:
            import sensenova_u1
            from sensenova_u1.utils import (
                load_model_and_tokenizer,
                make_offload_ctx,
                vram_mode_keeps_generation_resident,
                vram_mode_to_prefetch_count,
            )
        except ImportError as exc:
            die(
                f"missing SenseNova runtime dependency '{exc.name}'. "
                "Run scripts/setup-sensenova.ps1 in an isolated environment."
            )

        patch_sensenova_gguf_compute_dtype()
        sensenova_u1.set_attn_backend("sdpa")
        self.device = "cuda"
        self.vram_mode = {
            "none": "full",
            "sequential": "low",
            "model": "balanced",
            "balanced": "balanced",
        }.get(offload, "balanced")
        self.prefetch_count = vram_mode_to_prefetch_count(self.vram_mode)
        self._make_offload_ctx = make_offload_ctx
        self._keep_generation_resident = vram_mode_keeps_generation_resident
        self.model, self.tokenizer = load_model_and_tokenizer(
            model_path,
            dtype=dtype,
            device=self.device,
            gguf_checkpoint=str(gguf_checkpoint),
            for_offload=self.prefetch_count > 0,
        )

    def __call__(self, **kwargs: Any) -> Any:
        prompt = kwargs["prompt"]
        width = kwargs["width"]
        height = kwargs["height"]
        steps = kwargs["num_inference_steps"]
        seed = kwargs["seed"]
        guidance = kwargs["guidance_scale"]
        images = kwargs.get("image")
        if images is not None and not isinstance(images, list):
            images = [images]

        with self._make_offload_ctx(
            self.model,
            self.prefetch_count,
            self.device,
            keep_generation_resident=self._keep_generation_resident(self.vram_mode),
        ) as offloaded:
            if images:
                output = offloaded.it2i_generate(
                    self.tokenizer,
                    prompt,
                    images,
                    image_size=(width, height),
                    cfg_scale=guidance,
                    img_cfg_scale=1.0,
                    num_steps=steps,
                    batch_size=1,
                    seed=seed,
                )
            else:
                output = offloaded.t2i_generate(
                    self.tokenizer,
                    prompt,
                    image_size=(width, height),
                    cfg_scale=guidance,
                    num_steps=steps,
                    batch_size=1,
                    seed=seed,
                )
        return type("PipelineOutput", (), {"images": sensenova_tensor_to_pil(output)})()


def load_pipeline(
    spec: ModelSpec,
    *,
    cache_dir: Path,
    revision: str | None,
    offload: str,
    local_files_only: bool,
    gguf_checkpoint: str | None = None,
) -> tuple[Any, dict[str, Any]]:
    torch, diffusers = require_runtime()
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    if spec.runtime == "sensenova":
        resources_path = resolve_sensenova_resources(
            spec,
            cache_dir=cache_dir,
            revision=revision,
            local_files_only=local_files_only,
        )
        gguf_path = resolve_sensenova_gguf(
            spec,
            cache_dir=cache_dir,
            explicit=gguf_checkpoint,
            local_files_only=local_files_only,
        )
        started = time.perf_counter()
        print(f"Loading {spec.repo_id} from {gguf_path.name} ({offload} offload)...", file=sys.stderr)
        pipe = SenseNovaU15PipelineAdapter(
            str(resources_path),
            gguf_checkpoint=gguf_path,
            dtype=dtype,
            offload=offload,
        )
        return pipe, {
            "model_load_seconds": round(time.perf_counter() - started, 3),
            "resolved_revision": resources_path.name,
            "dtype": str(dtype).replace("torch.", ""),
            "offload": offload,
            "runtime": "sensenova-u1",
            "gguf_path": portable_path(gguf_path),
            "gguf_sha256": file_sha256(gguf_path),
        }

    pipeline_type = getattr(diffusers, spec.pipeline_class, None)
    if pipeline_type is None:
        die(
            f"diffusers {diffusers.__version__} does not expose {spec.pipeline_class}; upgrade diffusers"
        )

    kwargs: dict[str, Any] = {
        "torch_dtype": dtype,
        "cache_dir": str(cache_dir),
        "local_files_only": local_files_only,
    }
    if revision:
        kwargs["revision"] = revision

    started = time.perf_counter()
    print(f"Loading {spec.repo_id} ({offload} offload)...", file=sys.stderr)
    pipe = pipeline_type.from_pretrained(spec.repo_id, **kwargs)
    if offload == "sequential":
        pipe.enable_sequential_cpu_offload()
    elif offload == "model":
        pipe.enable_model_cpu_offload()
    elif offload == "none":
        pipe.to("cuda")
    else:
        die(f"invalid offload strategy: {offload}")

    if hasattr(pipe, "set_progress_bar_config"):
        pipe.set_progress_bar_config(disable=False)
    commit = None
    for component_name in ("transformer", "unet", "text_encoder"):
        component = getattr(pipe, component_name, None)
        commit = getattr(getattr(component, "config", None), "_commit_hash", None) or commit
    info = {
        "model_load_seconds": round(time.perf_counter() - started, 3),
        "resolved_revision": commit,
        "dtype": str(dtype).replace("torch.", ""),
        "offload": offload,
        "diffusers": diffusers.__version__,
    }
    return pipe, info


def load_pil_images(paths: Sequence[Path]) -> list[Any]:
    from diffusers.utils import load_image

    return [load_image(str(path)) for path in paths]


def prepare_sensenova_images(images: Sequence[Any], max_pixels: int) -> list[Any]:
    from PIL import Image

    prepared: list[Any] = []
    for image in images:
        if image.width * image.height <= max_pixels:
            prepared.append(image.convert("RGB"))
            continue
        scale = (max_pixels / (image.width * image.height)) ** 0.5
        width = max(32, round(image.width * scale / 32) * 32)
        height = max(32, round(image.height * scale / 32) * 32)
        prepared.append(image.convert("RGB").resize((width, height), Image.Resampling.LANCZOS))
    return prepared


def call_pipeline(
    pipe: Any,
    spec: ModelSpec,
    *,
    mode: str,
    prompt: str,
    images: Sequence[Any],
    width: int,
    height: int,
    steps: int,
    guidance: float,
    negative_prompt: str | None,
    seed: int,
) -> Any:
    import torch

    generator = torch.Generator(device="cuda").manual_seed(seed)
    kwargs: dict[str, Any] = {
        "prompt": prompt,
        "height": height,
        "width": width,
        "num_inference_steps": steps,
        "generator": generator,
    }
    if spec.runtime == "sensenova":
        kwargs.pop("generator")
        kwargs["seed"] = seed
    if spec.pipeline_class in {"QwenImagePipeline", "QwenImageEditPlusPipeline"}:
        kwargs["true_cfg_scale"] = guidance
        # Qwen's official Diffusers examples keep ordinary CFG disabled while
        # applying the requested strength through true CFG.
        kwargs["guidance_scale"] = 1.0
        kwargs["negative_prompt"] = negative_prompt or " "
    else:
        kwargs["guidance_scale"] = guidance
        if negative_prompt and spec.pipeline_class in {"ZImagePipeline", "ErnieImagePipeline"}:
            kwargs["negative_prompt"] = negative_prompt
    if spec.pipeline_class == "ErnieImagePipeline":
        kwargs["use_pe"] = True
    if mode == "edit":
        kwargs["image"] = list(images) if len(images) > 1 else images[0]

    with torch.inference_mode():
        return pipe(**kwargs).images[0]


def apply_mask(
    original: Any,
    edited: Any,
    mask_source: Any,
    feather: float,
    mask_mode: str = "edit-white",
) -> Any:
    from PIL import Image, ImageChops, ImageFilter

    base = original.convert("RGBA")
    result = edited.convert("RGBA").resize(base.size, Image.Resampling.LANCZOS)
    if isinstance(mask_source, (str, Path)):
        with Image.open(mask_source) as opened_mask:
            mask = opened_mask.convert("L")
    else:
        mask = mask_source.convert("L").copy()
    mask = mask.resize(base.size, Image.Resampling.LANCZOS)
    if mask_mode == "preserve-white":
        mask = ImageChops.invert(mask)
    elif mask_mode != "edit-white":
        die(f"invalid mask mode: {mask_mode}")
    if feather > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=feather))
    return Image.composite(result, base, mask)


def mask_edit_metrics(
    original: Any,
    result: Any,
    mask_path: Path,
    mask_mode: str = "edit-white",
) -> dict[str, Any]:
    """Measure saved-result locality against the requested binary mask region."""
    from PIL import Image, ImageChops

    base = original.convert("RGBA")
    candidate = result.convert("RGBA").resize(base.size, Image.Resampling.LANCZOS)
    requested = Image.open(mask_path).convert("L").resize(base.size, Image.Resampling.LANCZOS)
    if mask_mode == "preserve-white":
        requested = ImageChops.invert(requested)
    elif mask_mode != "edit-white":
        die(f"invalid mask mode: {mask_mode}")
    editable = requested.point(lambda value: 255 if value >= 128 else 0)
    protected = ImageChops.invert(editable)

    delta = ImageChops.difference(base, candidate)
    bands = delta.split()
    changed_levels = bands[0]
    for band in bands[1:]:
        changed_levels = ImageChops.lighter(changed_levels, band)
    changed = changed_levels.point(lambda value: 255 if value else 0)

    def white_pixels(image: Any) -> int:
        return image.histogram()[255]

    total_pixels = base.width * base.height
    editable_pixels = white_pixels(editable)
    protected_pixels = total_pixels - editable_pixels
    changed_pixels = white_pixels(changed)
    changed_editable = white_pixels(ImageChops.multiply(changed, editable))
    changed_protected = white_pixels(ImageChops.multiply(changed, protected))

    return {
        "total_pixels": total_pixels,
        "editable_pixels": editable_pixels,
        "protected_pixels": protected_pixels,
        "editable_changed_pct": round(
            100.0 * changed_editable / editable_pixels if editable_pixels else 0.0, 6
        ),
        "protected_exact_pct": round(
            100.0 * (protected_pixels - changed_protected) / protected_pixels
            if protected_pixels
            else 100.0,
            6,
        ),
        "whole_changed_pct": round(100.0 * changed_pixels / total_pixels, 6),
    }


def focus_box_from_mask(
    mask_path: Path,
    image_size: tuple[int, int],
    mask_mode: str,
    padding: int,
    target_aspect: float | None = None,
) -> tuple[int, int, int, int]:
    """Return a padded source-space crop around the editable mask region."""
    from PIL import Image, ImageChops

    image_width, image_height = image_size
    with Image.open(mask_path) as opened_mask:
        mask = opened_mask.convert("L").resize(image_size, Image.Resampling.LANCZOS)
    if mask_mode == "preserve-white":
        mask = ImageChops.invert(mask)
    elif mask_mode != "edit-white":
        die(f"invalid mask mode: {mask_mode}")
    editable = mask.point(lambda value: 255 if value >= 128 else 0)
    bbox = editable.getbbox()
    if bbox is None:
        die("the mask has no editable pixels")

    left = max(0, bbox[0] - padding)
    top = max(0, bbox[1] - padding)
    right = min(image_width, bbox[2] + padding)
    bottom = min(image_height, bbox[3] + padding)

    if target_aspect:
        width = right - left
        height = bottom - top
        current_aspect = width / height
        if current_aspect < target_aspect:
            desired_width = min(image_width, int(round(height * target_aspect)))
            extra = desired_width - width
            left -= extra // 2
            right += extra - extra // 2
        elif current_aspect > target_aspect:
            desired_height = min(image_height, int(round(width / target_aspect)))
            extra = desired_height - height
            top -= extra // 2
            bottom += extra - extra // 2

        if left < 0:
            right = min(image_width, right - left)
            left = 0
        if right > image_width:
            left = max(0, left - (right - image_width))
            right = image_width
        if top < 0:
            bottom = min(image_height, bottom - top)
            top = 0
        if bottom > image_height:
            top = max(0, top - (bottom - image_height))
            bottom = image_height

    return left, top, right, bottom


def focus_inference_size(box: tuple[int, int, int, int]) -> tuple[int, int]:
    width = box[2] - box[0]
    height = box[3] - box[1]
    scale = 1024.0 / max(width, height)
    return snap_size(int(round(width * scale)), int(round(height * scale)))


def remove_background(image: Any, cache_dir: Path, local_files_only: bool) -> tuple[Any, dict[str, Any]]:
    activate_local_packages()
    try:
        import torch
        from PIL import Image
        from torchvision.transforms import Compose, Normalize, Resize, ToTensor
        from transformers import AutoModelForImageSegmentation
    except ImportError as exc:
        die(f"background removal dependency '{exc.name}' is missing")

    model_id = BIREFNET_MODEL
    print(
        "Loading BiRefNet-matting for alpha extraction (Hugging Face remote model code is trusted).",
        file=sys.stderr,
    )
    started = time.perf_counter()
    model = AutoModelForImageSegmentation.from_pretrained(
        model_id,
        revision=BIREFNET_REVISION,
        trust_remote_code=True,
        cache_dir=str(cache_dir),
        local_files_only=local_files_only,
    )
    # torchvision's CUDA deformable convolution has no BF16 kernel. BiRefNet
    # matting fits this machine's 12 GB GPU in FP32, which is also the most
    # portable precision for that operator on Windows.
    dtype = torch.float32
    model = model.to(device="cuda", dtype=dtype).eval()
    transform = Compose(
        [
            Resize((1024, 1024)),
            ToTensor(),
            Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )
    tensor = transform(image.convert("RGB")).unsqueeze(0).to(device="cuda", dtype=dtype)
    with torch.inference_mode():
        prediction = model(tensor)
    if isinstance(prediction, dict):
        value = prediction.get("logits")
        prediction = value if value is not None else prediction.get("pred")
        if prediction is None:
            die("BiRefNet returned no logits or prediction tensor")
    if isinstance(prediction, (list, tuple)):
        prediction = prediction[-1]
    if prediction.ndim == 4:
        prediction = prediction[:, 0]
    mask_array = prediction.sigmoid().float().cpu()[0].numpy()
    mask = Image.fromarray((mask_array * 255).clip(0, 255).astype("uint8"), mode="L")
    mask = mask.resize(image.size, Image.Resampling.LANCZOS)
    rgba = image.convert("RGBA")
    rgba.putalpha(mask)
    del model, tensor, prediction
    torch.cuda.empty_cache()
    return rgba, {
        "model": model_id,
        "revision": BIREFNET_REVISION,
        "license": "MIT",
        "seconds": round(time.perf_counter() - started, 3),
        "dtype": str(dtype).replace("torch.", ""),
        "trust_remote_code": True,
    }


def save_image(image: Any, path: Path, fmt: str, compression: int) -> None:
    if fmt == "jpeg":
        if image.mode == "RGBA":
            from PIL import Image

            background = Image.new("RGB", image.size, "white")
            background.paste(image, mask=image.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")
        image.save(path, format="JPEG", quality=compression, optimize=True)
    elif fmt == "webp":
        image.save(path, format="WEBP", quality=compression, method=6)
    else:
        image.save(path, format="PNG", optimize=True)


def request_preview(
    *,
    command: str,
    spec: ModelSpec,
    prompt: str,
    outputs: Sequence[Path],
    width: int,
    height: int,
    steps: int,
    guidance: float,
    seed: int,
    images: Sequence[Path],
    image_roles: Sequence[str],
    transparent: bool,
    offload: str,
    raw_edit_outputs: Sequence[Path],
) -> dict[str, Any]:
    return {
        "command": command,
        "model": spec.alias,
        "repo_id": spec.repo_id,
        "license": spec.license,
        "prompt": prompt,
        "size": f"{width}x{height}",
        "steps": steps,
        "guidance_scale": guidance,
        "seed": seed,
        "input_images": [portable_path(path) for path in images],
        "input_image_roles": list(image_roles),
        "transparent": transparent,
        "offload": offload,
        "outputs": [portable_path(path) for path in outputs],
        "raw_edit_outputs": [portable_path(path) for path in raw_edit_outputs],
    }


def run_image_command(args: argparse.Namespace) -> None:
    command_started = time.perf_counter()
    command = args.command
    pipeline_mode = "edit" if command in {"edit", "compose"} else "generate"
    spec = model_spec(args.model, pipeline_mode)
    prompt_raw = read_prompt(args.prompt, args.prompt_file)
    prompt = augment_prompt(prompt_raw, prompt_fields(args), args.augment)
    inputs = resolve_images(args.image or [])
    if command in {"edit", "compose"} and not inputs:
        die(f"{command} requires at least one --image")
    if command == "generate" and inputs:
        die("generate does not consume references; use compose for a new scene from images")
    image_roles, roles_are_explicit = resolve_image_roles(
        args.image_role or [], len(inputs), command
    )
    if roles_are_explicit:
        prompt = prepend_image_roles(prompt, image_roles)
    mask_path: Path | None = None
    if args.mask:
        mask_path = Path(args.mask).expanduser().resolve()
        if not mask_path.is_file():
            die(f"mask not found: {mask_path}")

    requested_size = parse_size(args.size) if args.size else None
    focus_box: tuple[int, int, int, int] | None = None
    source_size: tuple[int, int] | None = None
    if args.focus_mask:
        from PIL import Image

        assert mask_path is not None
        with Image.open(inputs[0]) as source:
            source_size = source.size
        target_aspect = (
            requested_size[0] / requested_size[1] if requested_size else None
        )
        focus_box = focus_box_from_mask(
            mask_path,
            source_size,
            args.mask_mode,
            args.focus_padding,
            target_aspect,
        )

    if requested_size:
        width, height = requested_size
    elif focus_box:
        width, height = focus_inference_size(focus_box)
    elif command == "edit" and inputs:
        from PIL import Image

        if source_size is None:
            with Image.open(inputs[0]) as source:
                source_size = source.size
        width, height = snap_size(*source_size)
    else:
        width, height = (1024, 1024)
    if spec.runtime == "sensenova" and (width % 32 or height % 32):
        die("SenseNova width and height must be multiples of 32 pixels")

    steps = quality_steps(spec, args.quality, args.steps)
    guidance = spec.guidance_scale if args.guidance is None else args.guidance
    if args.n < 1 or args.n > 8:
        die("--n must be between 1 and 8")
    seed = args.seed if args.seed is not None else int.from_bytes(os.urandom(4), "big")
    out = Path(args.out)
    fmt = normalize_format(args.output_format, out)
    if args.transparent and fmt not in {"png", "webp"}:
        die("transparent output requires PNG or WebP")
    outputs = output_paths(args.out, args.out_dir, args.n, fmt)
    raw_edit_outputs = (
        [raw_edit_path(path) for path in outputs]
        if args.mask and args.keep_raw_edit
        else []
    )
    ensure_writable(
        outputs
        + raw_edit_outputs
        + [p.with_suffix(p.suffix + ".json") for p in outputs],
        args.force,
        args.dry_run,
    )

    gpu = cuda_summary()
    vram = float(gpu.get("vram_gb", 0))
    offload = effective_offload(spec, args.offload, vram)
    preview = request_preview(
        command=command,
        spec=spec,
        prompt=prompt,
        outputs=outputs,
        width=width,
        height=height,
        steps=steps,
        guidance=guidance,
        seed=seed,
        images=inputs,
        image_roles=image_roles,
        transparent=args.transparent,
        offload=offload,
        raw_edit_outputs=raw_edit_outputs,
    )
    if focus_box:
        preview["focus_region"] = {
            "x": focus_box[0],
            "y": focus_box[1],
            "width": focus_box[2] - focus_box[0],
            "height": focus_box[3] - focus_box[1],
            "padding": args.focus_padding,
            "aligned_same-size_references": True,
        }
    if spec.runtime == "sensenova":
        preview["input_max_pixels"] = args.input_max_pixels
        preview["gguf_checkpoint"] = args.gguf_checkpoint or spec.gguf_filename
    if args.dry_run:
        print(json.dumps(preview, indent=2, ensure_ascii=False))
        return

    cache_dir = Path(args.cache_dir).expanduser().resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    if not gpu.get("available"):
        die("CUDA is unavailable; run doctor for details")

    pipe, load_info = load_pipeline(
        spec,
        cache_dir=cache_dir,
        revision=args.revision,
        offload=offload,
        local_files_only=args.local_files_only,
        gguf_checkpoint=args.gguf_checkpoint,
    )
    loaded_inputs = load_pil_images(inputs)
    if spec.runtime == "sensenova":
        loaded_inputs = prepare_sensenova_images(loaded_inputs, args.input_max_pixels)
    full_source = loaded_inputs[0] if loaded_inputs else None
    mask_for_composite: Any = mask_path
    if focus_box:
        from PIL import Image

        assert full_source is not None
        assert mask_path is not None
        aligned_size = full_source.size
        loaded_inputs = [
            image.crop(focus_box) if image.size == aligned_size else image
            for image in loaded_inputs
        ]
        with Image.open(mask_path) as full_mask:
            mask_for_composite = (
                full_mask.convert("L")
                .resize(aligned_size, Image.Resampling.LANCZOS)
                .crop(focus_box)
            )
    source_for_mask = loaded_inputs[0] if loaded_inputs else None
    run_started = time.perf_counter()
    generated: list[tuple[Any, float, int]] = []
    for index in range(args.n):
        image_seed = seed + index
        started = time.perf_counter()
        image = call_pipeline(
            pipe,
            spec,
            mode=pipeline_mode,
            prompt=prompt,
            images=loaded_inputs,
            width=width,
            height=height,
            steps=steps,
            guidance=guidance,
            negative_prompt=args.negative,
            seed=image_seed,
        )
        generated.append((image, time.perf_counter() - started, image_seed))

    postprocess_info: dict[str, Any] | None = None
    if args.transparent:
        del pipe
        import torch

        torch.cuda.empty_cache()

    for index, (output, (image, inference_seconds, image_seed)) in enumerate(
        zip(outputs, generated)
    ):
        raw_edit_info: dict[str, str] | None = None
        if raw_edit_outputs:
            raw_output = raw_edit_outputs[index]
            save_image(image, raw_output, fmt, args.output_compression)
            raw_edit_info = {
                "path": portable_path(raw_output),
                "sha256": file_sha256(raw_output),
            }
        if args.mask:
            if source_for_mask is None:
                die("--mask can only be used with edit")
            assert mask_path is not None
            image = apply_mask(
                source_for_mask,
                image,
                mask_for_composite,
                args.mask_feather,
                args.mask_mode,
            )
        if focus_box:
            assert full_source is not None
            full_result = full_source.convert("RGBA").copy()
            full_result.paste(image.convert("RGBA"), (focus_box[0], focus_box[1]))
            image = full_result
        if args.transparent:
            image, postprocess_info = remove_background(image, cache_dir, args.local_files_only)
        save_image(image, output, fmt, args.output_compression)
        mask_metrics_info: dict[str, Any] | None = None
        if args.mask:
            from PIL import Image

            metrics_source = full_source if focus_box else source_for_mask
            assert metrics_source is not None
            assert mask_path is not None
            with Image.open(output) as saved_output:
                mask_metrics_info = mask_edit_metrics(
                    metrics_source, saved_output, mask_path, args.mask_mode
                )
        metadata = {
            **preview,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "output": portable_path(output),
            "output_sha256": file_sha256(output),
            "seed": image_seed,
            "inference_seconds": round(inference_seconds, 3),
            "generation_stage_seconds": round(time.perf_counter() - run_started, 3),
            "total_command_seconds": round(time.perf_counter() - command_started, 3),
            "model_load": load_info,
            "runtime": runtime_versions(),
            "gpu": gpu,
            "input_sha256": {portable_path(path): file_sha256(path) for path in inputs},
            "mask": portable_path(Path(args.mask)) if args.mask else None,
            "mask_mode": args.mask_mode if args.mask else None,
            "mask_feather": args.mask_feather if args.mask else None,
            "mask_metrics": mask_metrics_info,
            "raw_edit": raw_edit_info,
            "postprocess": postprocess_info,
        }
        sidecar = write_metadata(output, metadata)
        print(str(output.resolve()))
        print(str(sidecar.resolve()))


def run_models(args: argparse.Namespace) -> None:
    cache = Path(args.cache_dir).expanduser().resolve()
    data = []
    for spec in MODELS.values():
        row = asdict(spec)
        row["modes"] = list(spec.modes)
        row["cached"] = cache_has_model(cache, spec.repo_id)
        if spec.gguf_repo_id:
            row["cached"] = row["cached"] and registered_gguf_is_cached(spec, cache)
        data.append(row)
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    print(f"{'ALIAS':24} {'MODES':13} {'CACHE':6} {'LICENSE':12} STRENGTHS")
    for row in data:
        print(
            f"{row['alias']:24} {','.join(row['modes']):13} "
            f"{('yes' if row['cached'] else 'no'):6} {row['license']:12} {row['strengths']}"
        )


def run_doctor(args: argparse.Namespace) -> None:
    cache = Path(args.cache_dir).expanduser().resolve()
    transparency_runtime = transparency_runtime_versions()
    report = {
        "ok": False,
        "platform": platform.platform(),
        "runtime": runtime_versions(),
        "gpu": cuda_summary(),
        "system_ram_gb": system_ram_gb(),
        "cache_dir": str(cache),
        "cache_exists": cache.exists(),
        "default_model": DEFAULT_MODEL,
        "default_model_cached": cache_has_model(cache, MODELS[DEFAULT_MODEL].repo_id),
        "transparency_runtime": transparency_runtime,
        "transparency_ready": all(transparency_runtime.values()),
        "birefnet_cached": cache_has_model(cache, BIREFNET_MODEL),
    }
    required = ("torch", "diffusers", "transformers", "accelerate", "PIL")
    report["ok"] = bool(report["gpu"].get("available")) and all(
        report["runtime"].get(name) for name in required
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


def run_download(args: argparse.Namespace) -> None:
    spec = model_spec(args.model)
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        die("huggingface_hub is missing; install requirements-imagegen.txt")
    cache = Path(args.cache_dir).expanduser().resolve()
    cache.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {spec.repo_id} to {cache}...", file=sys.stderr)
    if spec.runtime == "sensenova":
        resources = resolve_sensenova_resources(
            spec,
            cache_dir=cache,
            revision=args.revision,
            local_files_only=args.local_files_only,
        )
        gguf = resolve_sensenova_gguf(
            spec,
            cache_dir=cache,
            explicit=args.gguf_checkpoint,
            local_files_only=args.local_files_only,
        )
        print(resources)
        print(gguf)
        return
    path = snapshot_download(
        repo_id=spec.repo_id,
        revision=args.revision,
        cache_dir=str(cache),
        local_files_only=args.local_files_only,
    )
    print(path)


def run_remove_background(args: argparse.Namespace) -> None:
    source = Path(args.image).expanduser().resolve()
    if not source.is_file():
        die(f"input image not found: {source}")
    target = Path(args.out)
    fmt = normalize_format(args.output_format, target)
    if fmt not in {"png", "webp"}:
        die("background removal requires PNG or WebP output")
    outputs = output_paths(args.out, None, 1, fmt)
    target = outputs[0]
    sidecar = target.with_suffix(target.suffix + ".json")
    ensure_writable([target, sidecar], args.force, args.dry_run)
    preview = {
        "command": "remove-background",
        "model": BIREFNET_MODEL,
        "revision": BIREFNET_REVISION,
        "license": "MIT",
        "input": portable_path(source),
        "output": portable_path(target),
        "trust_remote_code": True,
    }
    if args.dry_run:
        print(json.dumps(preview, indent=2, ensure_ascii=False))
        return

    from PIL import Image

    cache = Path(args.cache_dir).expanduser().resolve()
    cache.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with Image.open(source) as input_image:
        rgba, postprocess = remove_background(input_image, cache, args.local_files_only)
    save_image(rgba, target, fmt, args.output_compression)
    metadata = {
        **preview,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "output_sha256": file_sha256(target),
        "input_sha256": file_sha256(source),
        "total_command_seconds": round(time.perf_counter() - started, 3),
        "runtime": runtime_versions(),
        "gpu": cuda_summary(),
        "postprocess": postprocess,
    }
    write_metadata(target, metadata)
    print(str(target.resolve()))
    print(str(sidecar.resolve()))


def run_composite_mask(args: argparse.Namespace) -> None:
    base_path = Path(args.base).expanduser().resolve()
    edited_path = Path(args.edited).expanduser().resolve()
    mask_path = Path(args.mask).expanduser().resolve()
    for label, path in (("base", base_path), ("edited", edited_path), ("mask", mask_path)):
        if not path.is_file():
            die(f"{label} image not found: {path}")
    target = Path(args.out)
    fmt = normalize_format(args.output_format, target)
    outputs = output_paths(args.out, None, 1, fmt)
    target = outputs[0]
    sidecar = target.with_suffix(target.suffix + ".json")
    ensure_writable([target, sidecar], args.force, args.dry_run)
    preview = {
        "command": "composite-mask",
        "base": portable_path(base_path),
        "edited": portable_path(edited_path),
        "mask": portable_path(mask_path),
        "mask_mode": args.mask_mode,
        "mask_feather": args.mask_feather,
        "output": portable_path(target),
    }
    region = parse_region(args.region) if args.region else None
    if region:
        preview["region"] = {
            "x": region[0],
            "y": region[1],
            "width": region[2],
            "height": region[3],
        }
    if args.dry_run:
        print(json.dumps(preview, indent=2, ensure_ascii=False))
        return

    from PIL import Image

    with Image.open(base_path) as base, Image.open(edited_path) as edited:
        if region:
            x, y, width, height = region
            if x + width > base.width or y + height > base.height:
                die("region extends beyond the base image")
            box = (x, y, x + width, y + height)
            base_region = base.crop(box)
            with Image.open(mask_path) as full_mask:
                region_mask = (
                    full_mask.convert("L")
                    .resize(base.size, Image.Resampling.LANCZOS)
                    .crop(box)
                )
            edited_region = apply_mask(
                base_region, edited, region_mask, args.mask_feather, args.mask_mode
            )
            result = base.convert("RGBA").copy()
            result.paste(edited_region.convert("RGBA"), (x, y))
        else:
            result = apply_mask(
                base, edited, mask_path, args.mask_feather, args.mask_mode
            )
    save_image(result, target, fmt, args.output_compression)
    with Image.open(base_path) as base, Image.open(target) as saved_result:
        metrics = mask_edit_metrics(base, saved_result, mask_path, args.mask_mode)
    metadata = {
        **preview,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "output_sha256": file_sha256(target),
        "base_sha256": file_sha256(base_path),
        "edited_sha256": file_sha256(edited_path),
        "mask_sha256": file_sha256(mask_path),
        "mask_metrics": metrics,
        "runtime": runtime_versions(),
    }
    write_metadata(target, metadata)
    print(str(target.resolve()))
    print(str(sidecar.resolve()))


def read_batch_jobs(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        die(f"batch file not found: {path}")
    jobs: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            item = json.loads(line) if line.startswith("{") else {"prompt": line}
        except json.JSONDecodeError as exc:
            die(f"invalid JSON on line {line_number}: {exc}")
        if not isinstance(item, dict) or not str(item.get("prompt", "")).strip():
            die(f"batch line {line_number} must be an object with a prompt")
        jobs.append(item)
    if not jobs:
        die("batch file contains no jobs")
    if len(jobs) > MAX_BATCH_JOBS:
        die(f"batch contains {len(jobs)} jobs; maximum is {MAX_BATCH_JOBS}")
    return jobs


def run_batch(args: argparse.Namespace) -> None:
    jobs = read_batch_jobs(Path(args.input))
    out_dir = Path(args.out_dir)
    for index, job in enumerate(jobs, 1):
        job_args = argparse.Namespace(**vars(args))
        job_args.command = "generate"
        job_args.prompt = str(job["prompt"])
        job_args.prompt_file = None
        job_args.model = str(job.get("model", args.model))
        job_args.size = str(job.get("size", args.size)) if job.get("size", args.size) else None
        job_args.quality = str(job.get("quality", args.quality))
        job_args.seed = int(job.get("seed", args.seed + index - 1 if args.seed is not None else index))
        job_args.n = int(job.get("n", 1))
        job_args.image = []
        job_args.image_role = []
        job_args.mask = None
        job_args.transparent = bool(job.get("transparent", args.transparent))
        job_args.out_dir = None
        raw_name = str(job.get("out", f"{index:03d}.png"))
        job_args.out = str(out_dir / Path(raw_name).name)
        for field in prompt_fields(args):
            setattr(job_args, field, job.get(field, getattr(args, field, None)))
        print(f"[job {index}/{len(jobs)}]", file=sys.stderr)
        run_image_command(job_args)


def add_shared_generation_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default="auto", choices=["auto", *MODELS.keys()])
    parser.add_argument("--revision", help="Hugging Face revision, tag, or commit")
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file")
    parser.add_argument("--size", help="WIDTHxHEIGHT; defaults to 1024x1024 or source size")
    parser.add_argument("--quality", choices=sorted(ALLOWED_QUALITIES), default="standard")
    parser.add_argument("--steps", type=int)
    parser.add_argument("--guidance", type=float)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--out", default=DEFAULT_OUTPUT)
    parser.add_argument("--out-dir")
    parser.add_argument("--output-format", choices=sorted(ALLOWED_FORMATS))
    parser.add_argument("--output-compression", type=int, default=95)
    parser.add_argument("--transparent", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--cache-dir", default=str(default_cache_dir()))
    parser.add_argument(
        "--gguf-checkpoint",
        help="Explicit SenseNova .gguf path; otherwise the registered Q8 file is resolved from the cache",
    )
    parser.add_argument(
        "--input-max-pixels",
        type=int,
        default=1_048_576,
        help="Per-reference pixel budget for SenseNova; aspect ratio is preserved",
    )
    parser.add_argument("--offload", choices=sorted(ALLOWED_OFFLOAD), default="auto")
    parser.add_argument("--augment", dest="augment", action="store_true")
    parser.add_argument("--no-augment", dest="augment", action="store_false")
    parser.set_defaults(augment=True)
    parser.add_argument("--use-case")
    parser.add_argument("--asset-type")
    parser.add_argument("--scene")
    parser.add_argument("--subject")
    parser.add_argument("--style")
    parser.add_argument("--composition")
    parser.add_argument("--lighting")
    parser.add_argument("--palette")
    parser.add_argument("--materials")
    parser.add_argument("--text")
    parser.add_argument("--constraints")
    parser.add_argument("--negative")
    parser.add_argument("--mask")
    parser.add_argument("--mask-feather", type=float, default=2.0)
    parser.add_argument(
        "--focus-mask",
        action="store_true",
        help="Crop around the editable mask for inference, then restore into the full target",
    )
    parser.add_argument(
        "--focus-padding",
        type=int,
        default=96,
        help="Source pixels of context around a focused mask crop",
    )
    parser.add_argument("--image", action="append", default=[])
    parser.add_argument(
        "--image-role",
        action="append",
        default=[],
        help="Role/authority for the corresponding --image; repeat in the same order",
    )
    parser.add_argument(
        "--mask-mode",
        choices=sorted(ALLOWED_MASK_MODES),
        default="edit-white",
        help="edit-white edits white mask pixels; preserve-white keeps them unchanged",
    )
    parser.add_argument(
        "--keep-raw-edit",
        dest="keep_raw_edit",
        action="store_true",
        help="Keep the full generated edit before deterministic mask compositing",
    )
    parser.add_argument(
        "--discard-raw-edit",
        dest="keep_raw_edit",
        action="store_false",
        help="Discard the full generated edit after mask compositing",
    )
    parser.set_defaults(keep_raw_edit=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate and edit images locally with open-source models"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    models_parser = sub.add_parser("models", help="List supported model profiles")
    models_parser.add_argument("--json", action="store_true")
    models_parser.add_argument("--cache-dir", default=str(default_cache_dir()))
    models_parser.set_defaults(func=run_models)

    doctor_parser = sub.add_parser("doctor", help="Check the local runtime and GPU")
    doctor_parser.add_argument("--cache-dir", default=str(default_cache_dir()))
    doctor_parser.set_defaults(func=run_doctor)

    download_parser = sub.add_parser("download", help="Download a model before offline use")
    download_parser.add_argument("--model", required=True, choices=sorted(MODELS))
    download_parser.add_argument("--revision")
    download_parser.add_argument("--cache-dir", default=str(default_cache_dir()))
    download_parser.add_argument("--local-files-only", action="store_true")
    download_parser.add_argument("--gguf-checkpoint")
    download_parser.set_defaults(func=run_download)

    cutout_parser = sub.add_parser(
        "remove-background", help="Create a transparent cutout with BiRefNet"
    )
    cutout_parser.add_argument("--image", required=True)
    cutout_parser.add_argument("--out", default="output/open-imagegen/cutout.png")
    cutout_parser.add_argument("--output-format", choices=("png", "webp"))
    cutout_parser.add_argument("--output-compression", type=int, default=95)
    cutout_parser.add_argument("--cache-dir", default=str(default_cache_dir()))
    cutout_parser.add_argument("--local-files-only", action="store_true")
    cutout_parser.add_argument("--force", action="store_true")
    cutout_parser.add_argument("--dry-run", action="store_true")
    cutout_parser.set_defaults(func=run_remove_background)

    composite_parser = sub.add_parser(
        "composite-mask",
        help="Recombine an existing generated edit with its source without inference",
    )
    composite_parser.add_argument("--base", required=True)
    composite_parser.add_argument("--edited", required=True)
    composite_parser.add_argument("--mask", required=True)
    composite_parser.add_argument(
        "--region",
        help="Optional X,Y,WIDTH,HEIGHT when --edited is a focused raw crop",
    )
    composite_parser.add_argument("--mask-mode", choices=sorted(ALLOWED_MASK_MODES), default="edit-white")
    composite_parser.add_argument("--mask-feather", type=float, default=2.0)
    composite_parser.add_argument("--out", required=True)
    composite_parser.add_argument("--output-format", choices=sorted(ALLOWED_FORMATS))
    composite_parser.add_argument("--output-compression", type=int, default=95)
    composite_parser.add_argument("--force", action="store_true")
    composite_parser.add_argument("--dry-run", action="store_true")
    composite_parser.set_defaults(func=run_composite_mask)

    for command in ("generate", "edit", "compose"):
        command_parser = sub.add_parser(command, help=f"{command.capitalize()} an image")
        add_shared_generation_args(command_parser)
        command_parser.set_defaults(func=run_image_command)

    batch_parser = sub.add_parser("generate-batch", help="Run generation jobs from JSONL")
    add_shared_generation_args(batch_parser)
    batch_parser.add_argument("--input", required=True)
    batch_parser.set_defaults(func=run_batch)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "output_compression", 95) not in range(1, 101):
        die("--output-compression must be between 1 and 100")
    if getattr(args, "mask_feather", 0) < 0:
        die("--mask-feather cannot be negative")
    if getattr(args, "focus_padding", 0) < 0:
        die("--focus-padding cannot be negative")
    if hasattr(args, "input_max_pixels") and args.input_max_pixels < 262_144:
        die("--input-max-pixels must be at least 262144")
    if getattr(args, "focus_mask", False):
        if getattr(args, "command", None) != "edit" or not getattr(args, "mask", None):
            die("--focus-mask requires the edit command and --mask")
        if getattr(args, "transparent", False):
            die("--focus-mask cannot be combined with --transparent")
    if getattr(args, "command", None) == "generate" and getattr(args, "mask", None):
        die("--mask is edit-only")
    if getattr(args, "command", None) == "compose" and getattr(args, "mask", None):
        die("--mask requires an edit target; use the edit command")
    if getattr(args, "command", None) == "generate-batch" and not args.out_dir:
        die("generate-batch requires --out-dir")
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
