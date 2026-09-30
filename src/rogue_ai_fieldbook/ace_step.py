from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AceStepV1Settings:
    infer_steps: int = 60
    guidance_scale: float = 15.0
    scheduler_type: str = "euler"
    cfg_type: str = "apg"
    omega_scale: float = 10.0
    cpu_offload: bool = True
    torch_compile: bool = False


class AceStepV1Session:
    """Load ACE-Step once, then generate multiple named candidates reproducibly."""

    def __init__(
        self,
        checkpoint_dir: Path,
        settings: AceStepV1Settings | None = None,
        *,
        pipeline: Any | None = None,
    ) -> None:
        self.checkpoint_dir = checkpoint_dir
        self.settings = settings or AceStepV1Settings()
        if pipeline is not None:
            self.pipeline = pipeline
            self.dtype = "injected"
            return
        import torch
        from acestep.pipeline_ace_step import ACEStepPipeline

        self.dtype = "bfloat16" if torch.cuda.is_available() else "float32"
        self.pipeline = ACEStepPipeline(
            checkpoint_dir=str(checkpoint_dir),
            dtype=self.dtype,
            torch_compile=self.settings.torch_compile,
            cpu_offload=self.settings.cpu_offload,
        )

    def generate(
        self,
        *,
        prompt: str,
        duration_seconds: float,
        output_path: Path,
        seed: int,
        lyrics: str = "[instrumental]",
    ) -> dict[str, Any]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result = self.pipeline(
            format="wav",
            audio_duration=duration_seconds,
            prompt=prompt,
            lyrics=lyrics,
            infer_step=self.settings.infer_steps,
            guidance_scale=self.settings.guidance_scale,
            scheduler_type=self.settings.scheduler_type,
            cfg_type=self.settings.cfg_type,
            omega_scale=self.settings.omega_scale,
            manual_seeds=[seed],
            save_path=str(output_path),
        )
        return {
            "provider": "ace-step-v1-3.5b",
            "seed": seed,
            "duration_seconds": duration_seconds,
            "prompt": prompt,
            "lyrics": lyrics,
            "dtype": self.dtype,
            "checkpoint_dir": str(self.checkpoint_dir),
            "settings": asdict(self.settings),
            "actual_seeds": result.get("actual_seeds") if isinstance(result, dict) else None,
        }

    def extend_right(
        self,
        *,
        context_path: Path,
        context_seconds: float,
        extension_seconds: float,
        prompt: str,
        output_path: Path,
        seed: int,
        lyrics: str = "[instrumental]",
    ) -> dict[str, Any]:
        """Keep a real audio prior and generate a fresh continuation to its right."""

        if context_seconds <= 0 or extension_seconds <= 0:
            raise ValueError("context_seconds and extension_seconds must be positive")
        total_seconds = context_seconds + extension_seconds
        if total_seconds > 240:
            raise ValueError("ACE-Step v1 extension is limited to 240 seconds including context")
        if not context_path.is_file():
            raise FileNotFoundError(context_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result = self.pipeline(
            format="wav",
            audio_duration=context_seconds,
            prompt=prompt,
            lyrics=lyrics,
            infer_step=self.settings.infer_steps,
            guidance_scale=self.settings.guidance_scale,
            scheduler_type=self.settings.scheduler_type,
            cfg_type=self.settings.cfg_type,
            omega_scale=self.settings.omega_scale,
            manual_seeds=[seed],
            retake_seeds=[seed],
            retake_variance=1.0,
            task="extend",
            repaint_start=0,
            repaint_end=total_seconds,
            src_audio_path=str(context_path),
            save_path=str(output_path),
        )
        return {
            "provider": "ace-step-v1-3.5b",
            "task": "extend-right",
            "seed": seed,
            "context_seconds": context_seconds,
            "extension_seconds": extension_seconds,
            "combined_seconds": total_seconds,
            "prompt": prompt,
            "lyrics": lyrics,
            "dtype": self.dtype,
            "checkpoint_dir": str(self.checkpoint_dir),
            "settings": asdict(self.settings),
            "actual_seeds": result.get("actual_seeds") if isinstance(result, dict) else None,
            "actual_retake_seeds": result.get("retake_seeds") if isinstance(result, dict) else None,
        }
