from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class LoopBankPlan:
    """Durations and playback rules for a recursively conditioned loop bank."""

    intro_seconds: float = 30.0
    context_seconds: float = 30.0
    segment_seconds: float = 120.0
    variant_count: int = 10
    transition_seconds: float = 4.0
    outro_seconds: float = 30.0
    compatible_choices: int = 3
    avoid_recent: int = 2

    def __post_init__(self) -> None:
        durations = (self.intro_seconds, self.context_seconds, self.segment_seconds, self.transition_seconds, self.outro_seconds)
        if any(value <= 0 for value in durations):
            raise ValueError("all durations must be positive")
        if self.variant_count < 1:
            raise ValueError("variant_count must be positive")
        if self.context_seconds >= self.segment_seconds:
            raise ValueError("context_seconds must be shorter than segment_seconds")
        if self.transition_seconds >= self.segment_seconds / 2:
            raise ValueError("transition_seconds must be shorter than half a segment")
        if self.compatible_choices < 1 or self.avoid_recent < 0:
            raise ValueError("compatible_choices must be positive and avoid_recent non-negative")

    @property
    def source_seconds(self) -> float:
        return max(self.segment_seconds, self.intro_seconds + self.context_seconds)

    @property
    def extended_seconds(self) -> float:
        return self.segment_seconds

    @property
    def fresh_seconds(self) -> float:
        return self.segment_seconds - self.context_seconds

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            **asdict(self),
            "source_seconds": self.source_seconds,
            "extended_seconds": self.extended_seconds,
            "fresh_seconds": self.fresh_seconds,
            "context_policy": "preserve prior as prefix, then use the first context_seconds after it as the next prior",
        }


def slice_seconds(
    audio: np.ndarray,
    sample_rate: int,
    start_seconds: float,
    duration_seconds: float,
    *,
    sample_axis: int = -1,
    pad: bool = False,
) -> np.ndarray:
    """Return a duration-exact audio slice without changing channel orientation."""

    if sample_rate <= 0 or start_seconds < 0 or duration_seconds <= 0:
        raise ValueError("sample_rate and duration must be positive; start must be non-negative")
    array = np.asarray(audio)
    if array.ndim < 1:
        raise ValueError("audio must have at least one dimension")
    axis = sample_axis % array.ndim
    start = int(round(start_seconds * sample_rate))
    wanted = int(round(duration_seconds * sample_rate))
    stop = start + wanted
    selectors = [slice(None)] * array.ndim
    selectors[axis] = slice(start, min(stop, array.shape[axis]))
    result = array[tuple(selectors)].copy()
    missing = wanted - result.shape[axis]
    if missing <= 0:
        return result
    if not pad:
        raise ValueError(
            f"source has only {result.shape[axis] / sample_rate:.3f}s after the requested start; "
            f"{duration_seconds:.3f}s required"
        )
    padding = [(0, 0)] * result.ndim
    padding[axis] = (0, missing)
    return np.pad(result, padding)


def split_extended_generation(
    extended_audio: np.ndarray,
    sample_rate: int,
    *,
    context_seconds: float,
    segment_seconds: float,
    sample_axis: int = -1,
) -> tuple[np.ndarray, np.ndarray]:
    """Keep the prior-prefixed segment and take the first window after that prior for recursion."""

    segment = slice_seconds(
        extended_audio,
        sample_rate,
        0.0,
        segment_seconds,
        sample_axis=sample_axis,
    )
    next_context = slice_seconds(
        segment,
        sample_rate,
        context_seconds,
        context_seconds,
        sample_axis=sample_axis,
    )
    return segment, next_context


@dataclass(frozen=True)
class AudioHealthSignature:
    """Small dependency-free signature used to reject stationary HF failures."""

    rms: float
    rms_cv: float
    spectral_centroid_hz: float
    normalized_centroid: float
    spectral_flatness: float
    spectral_flux: float


def audio_health_signature(audio: np.ndarray, sample_rate: int) -> AudioHealthSignature:
    """Measure broad dynamics and spectrum without requiring scipy or librosa."""

    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    array = np.asarray(audio, dtype=np.float32)
    if array.ndim == 2:
        array = array.mean(axis=0)
    elif array.ndim != 1:
        raise ValueError("audio must be mono or channels-first stereo")
    if array.size < 64:
        raise ValueError("audio is too short to analyze")

    frame_size = min(4096, 1 << int(np.floor(np.log2(array.size))))
    frame_size = max(64, frame_size)
    hop = max(1, frame_size // 2)
    window = np.hanning(frame_size).astype(np.float32)
    frames: list[np.ndarray] = []
    for start in range(0, max(1, array.size - frame_size + 1), hop):
        frame = array[start : start + frame_size]
        if frame.size < frame_size:
            frame = np.pad(frame, (0, frame_size - frame.size))
        frames.append(np.abs(np.fft.rfft(frame * window)).astype(np.float64) + 1e-12)
    magnitudes = np.asarray(frames)
    frequencies = np.fft.rfftfreq(frame_size, 1.0 / sample_rate)
    centroids = np.sum(magnitudes * frequencies, axis=1) / np.sum(magnitudes, axis=1)
    flatness = np.exp(np.mean(np.log(magnitudes), axis=1)) / np.mean(magnitudes, axis=1)
    normalized = magnitudes / (np.linalg.norm(magnitudes, axis=1, keepdims=True) + 1e-12)
    flux = float(np.mean(np.linalg.norm(np.diff(normalized, axis=0), axis=1))) if len(frames) > 1 else 0.0

    rms_blocks = [
        float(np.sqrt(np.mean(block.astype(np.float64) ** 2)))
        for block in np.array_split(array, min(30, max(1, array.size // frame_size)))
        if block.size
    ]
    rms = float(np.sqrt(np.mean(array.astype(np.float64) ** 2)))
    rms_mean = float(np.mean(rms_blocks)) if rms_blocks else 0.0
    rms_cv = float(np.std(rms_blocks) / (rms_mean + 1e-12))
    centroid = float(np.median(centroids))
    return AudioHealthSignature(
        rms=rms,
        rms_cv=rms_cv,
        spectral_centroid_hz=centroid,
        normalized_centroid=centroid / (sample_rate / 2.0),
        spectral_flatness=float(np.median(flatness)),
        spectral_flux=flux,
    )


def extension_health_report(
    context: np.ndarray,
    fresh_audio: np.ndarray,
    sample_rate: int,
) -> dict[str, object]:
    """Detect the stationary high-frequency noise failure seen in long AI extensions."""

    context_signature = audio_health_signature(context, sample_rate)
    fresh_signature = audio_health_signature(fresh_audio, sample_rate)
    centroid_ratio = fresh_signature.spectral_centroid_hz / max(context_signature.spectral_centroid_hz, 1.0)
    buzzing = bool(
        fresh_signature.normalized_centroid >= 0.28
        and fresh_signature.spectral_flatness >= 0.25
        and fresh_signature.rms_cv <= 0.15
        and centroid_ratio >= 1.6
    )
    return {
        "accepted": not buzzing,
        "reason": "stationary-high-frequency-noise" if buzzing else "ok",
        "centroid_ratio": round(centroid_ratio, 6),
        "context": asdict(context_signature),
        "fresh": asdict(fresh_signature),
    }


def standalone_audio_health_report(audio: np.ndarray, sample_rate: int) -> dict[str, object]:
    """Reject a complete render that collapsed into stationary high-frequency noise."""

    signature = audio_health_signature(audio, sample_rate)
    buzzing = bool(
        signature.normalized_centroid >= 0.28
        and signature.spectral_flatness >= 0.25
        and signature.rms_cv <= 0.15
    )
    return {
        "accepted": not buzzing,
        "reason": "stationary-high-frequency-noise" if buzzing else "ok",
        "audio": asdict(signature),
    }


def assemble_incremental_segment(    prior: np.ndarray,
    fresh_chunks: Sequence[np.ndarray],
    sample_rate: int,
    *,
    context_seconds: float,
    segment_seconds: float,
    sample_axis: int = -1,
) -> tuple[np.ndarray, np.ndarray]:
    """Assemble a long segment from short conditioned generations."""

    if not fresh_chunks:
        raise ValueError("at least one fresh chunk is required")
    initial = slice_seconds(prior, sample_rate, 0, context_seconds, sample_axis=sample_axis)
    chunks = [initial]
    for fresh in fresh_chunks:
        chunks.append(slice_seconds(fresh, sample_rate, 0, context_seconds, sample_axis=sample_axis))
    segment = np.concatenate(chunks, axis=sample_axis)
    segment = slice_seconds(segment, sample_rate, 0, segment_seconds, sample_axis=sample_axis)
    next_context = slice_seconds(segment, sample_rate, context_seconds, context_seconds, sample_axis=sample_axis)
    return segment, next_context


def _mono_window(audio: np.ndarray, sample_rate: int, seconds: float, *, at_end: bool) -> np.ndarray:
    array = np.asarray(audio, dtype=np.float32)
    if array.ndim == 2:
        array = array.mean(axis=0)
    elif array.ndim != 1:
        raise ValueError("audio must be mono or channels-first stereo")
    count = min(array.size, max(32, int(round(seconds * sample_rate))))
    return array[-count:] if at_end else array[:count]


def _transition_signature(window: np.ndarray) -> np.ndarray:
    if window.size < 32:
        raise ValueError("transition window is too short")
    windowed = window * np.hanning(window.size)
    spectrum = np.abs(np.fft.rfft(windowed)).astype(np.float64) + 1e-12
    buckets = np.array_split(spectrum, 12)
    bands = np.array([float(np.log(np.mean(bucket))) for bucket in buckets])
    rms_db = 20.0 * np.log10(float(np.sqrt(np.mean(window.astype(np.float64) ** 2))) + 1e-9)
    mean = float(np.mean(window))
    return np.concatenate(([rms_db / 24.0, mean * 4.0], bands / 8.0))


def transition_cost(
    source: np.ndarray,
    target: np.ndarray,
    sample_rate: int,
    *,
    window_seconds: float = 4.0,
) -> float:
    """Estimate how unobtrusive a source-end to target-start transition should sound."""

    source_signature = _transition_signature(_mono_window(source, sample_rate, window_seconds, at_end=True))
    target_signature = _transition_signature(_mono_window(target, sample_rate, window_seconds, at_end=False))
    return float(np.sqrt(np.mean((source_signature - target_signature) ** 2)))


def build_transition_costs(
    segments: Sequence[np.ndarray],
    sample_rate: int,
    *,
    window_seconds: float = 4.0,
) -> list[list[float]]:
    if not segments:
        raise ValueError("at least one segment is required")
    return [
        [round(transition_cost(source, target, sample_rate, window_seconds=window_seconds), 8) for target in segments]
        for source in segments
    ]


def ranked_successors(
    transition_costs: Sequence[Sequence[float]],
    source_index: int,
    *,
    include_self: bool = False,
) -> list[int]:
    """Return deterministic best-to-worst successors for one source segment."""

    size = len(transition_costs)
    if size == 0 or any(len(row) != size for row in transition_costs):
        raise ValueError("transition_costs must be a non-empty square matrix")
    if not 0 <= source_index < size:
        raise ValueError("source_index must reference the transition matrix")
    candidates = range(size) if include_self else (index for index in range(size) if index != source_index)
    return sorted(candidates, key=lambda index: (float(transition_costs[source_index][index]), index))


def schedule_variants(
    transition_costs: Sequence[Sequence[float]],
    length: int,
    *,
    seed: int,
    start_index: int = 0,
    compatible_choices: int = 3,
    avoid_recent: int = 2,
) -> list[int]:
    """Create a reproducible varied route, sampling among the best compatible successors."""

    size = len(transition_costs)
    if size == 0 or any(len(row) != size for row in transition_costs):
        raise ValueError("transition_costs must be a non-empty square matrix")
    if length < 1 or not 0 <= start_index < size:
        raise ValueError("length must be positive and start_index valid")
    rng = random.Random(seed)
    route = [start_index]
    while len(route) < length:
        current = route[-1]
        blocked = set(route[-avoid_recent:]) if avoid_recent else set()
        allowed = [index for index in range(size) if index not in blocked]
        if not allowed:
            allowed = [index for index in range(size) if index != current] or [current]
        ranked = sorted(allowed, key=lambda index: (transition_costs[current][index], index))
        pool = ranked[: min(compatible_choices, len(ranked))]
        weights = [1.0 / (float(transition_costs[current][index]) + 0.05) for index in pool]
        route.append(rng.choices(pool, weights=weights, k=1)[0])
    return route


def program_duration_seconds(plan: LoopBankPlan, loop_count: int) -> float:
    """Exact timeline duration when only loop-to-loop transitions overlap."""

    if loop_count < 1:
        raise ValueError("loop_count must be positive")
    overlaps = max(0, loop_count - 1) * plan.transition_seconds
    return plan.intro_seconds + loop_count * plan.segment_seconds + plan.outro_seconds - overlaps


def closest_loop_count(plan: LoopBankPlan, target_seconds: float) -> tuple[int, float]:
    """Return the positive loop count whose realizable program duration is closest."""

    if target_seconds <= 0:
        raise ValueError("target_seconds must be positive")
    advance = plan.segment_seconds - plan.transition_seconds
    estimate = max(1, round((target_seconds - plan.intro_seconds - plan.outro_seconds - plan.transition_seconds) / advance))
    candidates = {max(1, estimate - 1), estimate, estimate + 1}
    count = min(candidates, key=lambda value: (abs(program_duration_seconds(plan, value) - target_seconds), value))
    return count, program_duration_seconds(plan, count)