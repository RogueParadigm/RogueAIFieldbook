from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rogue_ai_fieldbook.audio import (  # noqa: E402
    bars_to_seconds,
    bridge_intro_to_loop,
    build_crossfaded_loop,
    match_rms_peak,
    measure_audio,
    search_best_loop,
    smooth_join_target,
    trim_to_loudest_energy,
)
from rogue_ai_fieldbook.core import file_sha256, portable_path, stable_seed, write_metadata  # noqa: E402


class CoreTests(unittest.TestCase):
    def test_stable_seed(self) -> None:
        self.assertEqual(stable_seed("SFX_Shot"), stable_seed("SFX_Shot"))
        self.assertNotEqual(stable_seed("SFX_Shot"), stable_seed("SFX_Impact"))

    def test_sidecar_and_portable_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "tone.wav"
            artifact.write_bytes(b"tone")
            sidecar = write_metadata(artifact, {"sha256": file_sha256(artifact)})
            self.assertEqual(sidecar.name, "tone.wav.json")
            self.assertEqual(portable_path(artifact, root), "tone.wav")


class AudioTests(unittest.TestCase):
    def test_bars_to_seconds(self) -> None:
        self.assertEqual(bars_to_seconds(120, 8), 16.0)

    def test_crossfade_preserves_exact_bar_length(self) -> None:
        rate = 100
        source = np.linspace(-1, 1, 4000, dtype=np.float32)[None, :]
        loop = build_crossfaded_loop(source, rate, 8.0, 1.0, 0.25)
        self.assertIsNotNone(loop)
        self.assertEqual(loop.shape, (1, 800))

    def test_search_returns_measured_candidate(self) -> None:
        rate = 100
        time = np.arange(5000) / rate
        source = np.sin(2 * np.pi * 2 * time).astype(np.float32)[None, :]
        candidate = search_best_loop(source, rate, bpm=120, bars=2, crossfades=(0.5, 1.0), start_fractions=(0.1, 0.2))
        self.assertEqual(candidate.audio.shape[-1], 400)
        self.assertGreaterEqual(candidate.metrics.seam_ratio, 0)

    def test_bridge_makes_intro_transition_equal_loop_transition(self) -> None:
        intro = np.zeros((2, 200), dtype=np.float32)
        loop = np.linspace(-0.5, 0.5, 200, dtype=np.float32)[None, :].repeat(2, axis=0)
        bridged = bridge_intro_to_loop(intro, loop, 100, bridge_seconds=0.2)
        self.assertTrue(np.allclose(bridged[:, -1], loop[:, -1]))

    def test_smooth_join_target_removes_boundary_step_without_changing_length(self) -> None:
        source = np.linspace(-0.5, 0.75, 100, dtype=np.float32)[None, :]
        target = np.linspace(-0.75, 0.25, 100, dtype=np.float32)[None, :]
        smoothed = smooth_join_target(source, target, 100, settle_seconds=0.2)
        self.assertEqual(smoothed.shape, target.shape)
        self.assertTrue(np.allclose(smoothed[:, 0], source[:, -1]))
        self.assertTrue(np.allclose(smoothed[:, 20:], target[:, 20:]))

    def test_energy_trim_keeps_full_requested_duration_near_source_end(self) -> None:
        source = np.zeros((1, 1000), dtype=np.float32)
        source[:, 950:970] = 1
        clip = trim_to_loudest_energy(source, 100, 2.0)
        self.assertEqual(clip.shape[-1], 200)

    def test_level_match_obeys_peak_ceiling(self) -> None:
        source = np.array([0.01, 0.02, 1.0], dtype=np.float32)
        matched = match_rms_peak(source, target_rms=0.5, peak_ceiling=0.8)
        self.assertLessEqual(float(np.abs(matched).max()), 0.800001)
        self.assertGreater(measure_audio(np.tile(matched, 2)).rms, 0)


if __name__ == "__main__":
    unittest.main()

