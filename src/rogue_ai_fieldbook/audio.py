from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class AudioMetrics:
    peak: float
    rms: float
    seam_delta: float
    typical_delta: float
    seam_ratio: float
    reference_quantile: float

    def to_dict(self) -> dict[str, float]:
        return {key: round(value, 8) for key, value in asdict(self).items()}


@dataclass(frozen=True)
class LoopCandidate:
    audio: np.ndarray
    sample_rate: int
    start_fraction: float
    start_sample: int
    crossfade_seconds: float
    duration_seconds: float
    metrics: AudioMetrics


def bars_to_seconds(bpm: float, bars: int, beats_per_bar: int = 4) -> float:
    if bpm <= 0 or bars <= 0 or beats_per_bar <= 0:
        raise ValueError("bpm, bars and beats_per_bar must be positive")
    return bars * beats_per_bar * 60.0 / bpm


def _samples_last(audio: np.ndarray, sample_axis: int) -> tuple[np.ndarray, int]:
    array = np.asarray(audio, dtype=np.float32)
    if array.ndim == 0 or array.ndim > 2:
        raise ValueError("audio must be mono or two-dimensional")
    if array.ndim == 1:
        return array[np.newaxis, :], 0
    normalized_axis = sample_axis % array.ndim
    return np.moveaxis(array, normalized_axis, -1), normalized_axis


def _restore_axis(audio: np.ndarray, original: np.ndarray, sample_axis: int) -> np.ndarray:
    if np.asarray(original).ndim == 1:
        return audio[0]
    return np.moveaxis(audio, -1, sample_axis % 2)


def measure_audio(audio: np.ndarray, *, sample_axis: int = -1, reference_quantile: float = 0.5) -> AudioMetrics:
    if not 0 < reference_quantile < 1:
        raise ValueError("reference_quantile must be between 0 and 1")
    channels, _ = _samples_last(audio, sample_axis)
    if channels.shape[-1] < 2:
        raise ValueError("audio needs at least two samples")
    mono = channels.mean(axis=0)
    deltas = np.abs(np.diff(mono))
    typical = float(np.quantile(deltas, reference_quantile))
    seam = float(abs(mono[0] - mono[-1]))
    return AudioMetrics(
        peak=float(np.abs(channels).max()),
        rms=float(np.sqrt(np.mean(channels.astype(np.float64) ** 2))),
        seam_delta=seam,
        typical_delta=typical,
        seam_ratio=seam / typical if typical > 0 else (0.0 if seam == 0 else float("inf")),
        reference_quantile=reference_quantile,
    )


def build_crossfaded_loop(
    audio: np.ndarray,
    sample_rate: int,
    duration_seconds: float,
    crossfade_seconds: float,
    start_fraction: float,
    *,
    sample_axis: int = -1,
) -> np.ndarray | None:
    if sample_rate <= 0 or duration_seconds <= 0 or crossfade_seconds <= 0:
        raise ValueError("sample_rate, duration_seconds and crossfade_seconds must be positive")
    if not 0 <= start_fraction <= 1:
        raise ValueError("start_fraction must be between 0 and 1")
    original = np.asarray(audio)
    channels, axis = _samples_last(original, sample_axis)
    total = channels.shape[-1]
    fade = int(round(crossfade_seconds * sample_rate))
    body_samples = int(round(duration_seconds * sample_rate))
    wanted = body_samples + fade
    start = int(total * start_fraction)
    if fade >= body_samples or start + wanted > total:
        return None
    chunk = channels[:, start : start + wanted]
    body = chunk[:, :body_samples].copy()
    tail = chunk[:, body_samples:]
    ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
    body[:, :fade] = body[:, :fade] * ramp + tail * (1.0 - ramp)
    return _restore_axis(body, original, axis)


def search_best_loop(
    audio: np.ndarray,
    sample_rate: int,
    *,
    bpm: float,
    bars: int,
    beats_per_bar: int = 4,
    crossfades: Iterable[float] = (1.5, 2.0, 3.0, 4.0, 6.0),
    start_fractions: Iterable[float] = (0.15, 0.25, 0.35, 0.45, 0.55),
    sample_axis: int = -1,
    reference_quantile: float = 0.5,
) -> LoopCandidate:
    duration = bars_to_seconds(bpm, bars, beats_per_bar)
    total_samples = np.asarray(audio).shape[sample_axis]
    best: LoopCandidate | None = None
    for crossfade in crossfades:
        for start_fraction in start_fractions:
            loop = build_crossfaded_loop(
                audio,
                sample_rate,
                duration,
                float(crossfade),
                float(start_fraction),
                sample_axis=sample_axis,
            )
            if loop is None:
                continue
            metrics = measure_audio(loop, sample_axis=sample_axis, reference_quantile=reference_quantile)
            candidate = LoopCandidate(
                audio=loop,
                sample_rate=sample_rate,
                start_fraction=float(start_fraction),
                start_sample=int(total_samples * float(start_fraction)),
                crossfade_seconds=float(crossfade),
                duration_seconds=duration,
                metrics=metrics,
            )
            if best is None or candidate.metrics.seam_ratio < best.metrics.seam_ratio:
                best = candidate
    if best is None:
        raise ValueError(f"source is too short for {bars} bars at {bpm:g} BPM plus the requested crossfades")
    return best


def bridge_intro_to_loop(
    intro: np.ndarray,
    loop: np.ndarray,
    sample_rate: int,
    *,
    bridge_seconds: float = 0.09,
    sample_axis: int = -1,
) -> np.ndarray:
    intro_original = np.asarray(intro)
    intro_channels, axis = _samples_last(intro_original, sample_axis)
    loop_channels, _ = _samples_last(loop, sample_axis)
    if intro_channels.shape[0] != loop_channels.shape[0]:
        raise ValueError("intro and loop must have the same channel count")
    bridge = min(int(round(bridge_seconds * sample_rate)), intro_channels.shape[-1], loop_channels.shape[-1])
    if bridge <= 0:
        return intro_original.copy()
    result = intro_channels.copy()
    blend = np.sin(np.linspace(0, np.pi / 2, bridge, dtype=np.float32)) ** 2
    result[:, -bridge:] = result[:, -bridge:] * (1.0 - blend) + loop_channels[:, -bridge:] * blend
    return _restore_axis(result, intro_original, axis)


def smooth_join_target(
    source: np.ndarray,
    target: np.ndarray,
    sample_rate: int,
    *,
    settle_seconds: float = 0.02,
    sample_axis: int = -1,
) -> np.ndarray:
    """Remove a PCM boundary step while preserving target length and musical context."""
    source_channels, _ = _samples_last(np.asarray(source), sample_axis)
    target_original = np.asarray(target)
    target_channels, axis = _samples_last(target_original, sample_axis)
    if source_channels.shape[0] != target_channels.shape[0]:
        raise ValueError("source and target must have the same channel count")
    settle = min(int(round(settle_seconds * sample_rate)), target_channels.shape[-1])
    if settle <= 0 or source_channels.shape[-1] == 0:
        return target_original.copy()
    result = target_channels.copy()
    blend = np.sin(np.linspace(0, np.pi / 2, settle, dtype=np.float32)) ** 2
    result[:, :settle] = source_channels[:, -1:] * (1.0 - blend) + result[:, :settle] * blend
    return _restore_axis(result, target_original, axis)


def trim_to_loudest_energy(
    audio: np.ndarray,
    sample_rate: int,
    keep_seconds: float,
    *,
    energy_window_ms: float = 60.0,
    pre_roll_ms: float = 35.0,
    fade_out_ms: float = 30.0,
    sample_axis: int = -1,
) -> np.ndarray:
    original = np.asarray(audio)
    channels, axis = _samples_last(original, sample_axis)
    mono = np.abs(channels).mean(axis=0)
    keep = min(int(round(keep_seconds * sample_rate)), channels.shape[-1])
    if mono.size == 0 or float(mono.max()) <= 0:
        return original.copy()
    window = max(1, min(int(round(energy_window_ms / 1000.0 * sample_rate)), mono.size))
    cumulative = np.concatenate(([0.0], np.cumsum(mono.astype(np.float64) ** 2)))
    energy = cumulative[window:] - cumulative[:-window]
    loudest = int(np.argmax(energy))
    start = max(0, loudest - int(round(pre_roll_ms / 1000.0 * sample_rate)))
    start = min(start, max(0, channels.shape[-1] - keep))
    clip = channels[:, start : start + keep].copy()
    fade = min(int(round(fade_out_ms / 1000.0 * sample_rate)), clip.shape[-1] // 4)
    if fade > 0:
        clip[:, -fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    return _restore_axis(clip, original, axis)


def match_rms_peak(
    audio: np.ndarray,
    *,
    target_rms: float,
    peak_ceiling: float,
) -> np.ndarray:
    if target_rms <= 0 or not 0 < peak_ceiling <= 1:
        raise ValueError("target_rms must be positive and peak_ceiling must be in (0, 1]")
    array = np.asarray(audio, dtype=np.float32)
    rms = float(np.sqrt(np.mean(array.astype(np.float64) ** 2)))
    if rms <= 0:
        return array.copy()
    peak = float(np.abs(array).max())
    gain = target_rms / rms
    if peak > 0 and peak * gain > peak_ceiling:
        gain = peak_ceiling / peak
    return (array * gain).astype(np.float32)

