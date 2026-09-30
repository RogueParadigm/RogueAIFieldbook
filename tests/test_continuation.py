from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rogue_ai_fieldbook.continuation import (  # noqa: E402
    LoopBankPlan,
    assemble_incremental_segment,
    build_transition_costs,
    extension_health_report,
    ranked_successors,
    schedule_variants,
    slice_seconds,
    split_extended_generation,
    standalone_audio_health_report,
)


class ContinuationTests(unittest.TestCase):
    def test_default_contract_matches_long_context_bank(self) -> None:
        plan = LoopBankPlan()
        self.assertEqual(plan.intro_seconds, 30)
        self.assertEqual(plan.context_seconds, 30)
        self.assertEqual(plan.segment_seconds, 120)
        self.assertEqual(plan.variant_count, 10)
        self.assertEqual(plan.fresh_seconds, 90)
        self.assertEqual(plan.extended_seconds, 120)

    def test_split_preserves_prior_and_uses_first_seconds_after_it_as_next_context(self) -> None:
        rate = 10
        extended = np.arange(120 * rate, dtype=np.float32)[None, :]
        segment, context = split_extended_generation(
            extended,
            rate,
            context_seconds=30,
            segment_seconds=120,
        )
        self.assertEqual(segment.shape[-1], 120 * rate)
        self.assertEqual(context.shape[-1], 30 * rate)
        self.assertEqual(float(segment[0, 0]), 0)
        self.assertTrue(np.array_equal(context, segment[:, 30 * rate : 60 * rate]))

    def test_slice_rejects_short_source_unless_padding_is_explicit(self) -> None:
        source = np.zeros((2, 100), dtype=np.float32)
        with self.assertRaises(ValueError):
            slice_seconds(source, 10, 8, 4)
        self.assertEqual(slice_seconds(source, 10, 8, 4, pad=True).shape, (2, 40))

    def test_incremental_segment_uses_first_fresh_chunk_for_next_context(self) -> None:
        rate = 10
        prior = np.full((1, 300), 1, dtype=np.float32)
        chunks = [np.full((1, 300), value, dtype=np.float32) for value in (2, 3, 4)]
        segment, next_context = assemble_incremental_segment(
            prior, chunks, rate, context_seconds=30, segment_seconds=120
        )
        self.assertEqual(segment.shape[-1], 1200)
        self.assertTrue(np.all(next_context == 2))

    def test_health_report_rejects_stationary_high_frequency_noise(self) -> None:
        rate = 48000
        time = np.arange(rate, dtype=np.float32) / rate
        context = (0.2 * np.sin(2 * np.pi * 400 * time))[None, :]
        rng = np.random.default_rng(7)
        buzzing = rng.normal(0, 0.1, rate).astype(np.float32)[None, :]
        report = extension_health_report(context, buzzing, rate)
        self.assertFalse(report["accepted"])
        self.assertEqual(report["reason"], "stationary-high-frequency-noise")

    def test_standalone_health_report_accepts_tonal_music_and_rejects_noise(self) -> None:
        rate = 48000
        time = np.arange(rate, dtype=np.float32) / rate
        music = (0.2 * np.sin(2 * np.pi * 330 * time) * (0.6 + 0.4 * time))[None, :]
        noise = np.random.default_rng(11).normal(0, 0.1, rate).astype(np.float32)[None, :]
        self.assertTrue(standalone_audio_health_report(music, rate)["accepted"])
        self.assertFalse(standalone_audio_health_report(noise, rate)["accepted"])

    def test_transition_scheduler_is_reproducible_and_avoids_immediate_repeats(self) -> None:
        costs = [
            [0.0, 0.1, 0.2, 0.3],
            [0.1, 0.0, 0.2, 0.3],
            [0.2, 0.1, 0.0, 0.3],
            [0.3, 0.2, 0.1, 0.0],
        ]
        first = schedule_variants(costs, 30, seed=81, avoid_recent=2)
        second = schedule_variants(costs, 30, seed=81, avoid_recent=2)
        self.assertEqual(first, second)
        self.assertTrue(all(left != right for left, right in zip(first, first[1:])))

    def test_cost_matrix_is_square(self) -> None:
        rate = 100
        time = np.arange(500) / rate
        segments = [
            np.sin(2 * np.pi * frequency * time).astype(np.float32)[None, :]
            for frequency in (2, 3, 4)
        ]
        matrix = build_transition_costs(segments, rate, window_seconds=1)
        self.assertEqual((len(matrix), len(matrix[0])), (3, 3))

    def test_ranked_successors_excludes_self_and_uses_index_as_tie_breaker(self) -> None:
        costs = [
            [0.0, 0.2, 0.1, 0.1],
            [0.2, 0.0, 0.3, 0.4],
            [0.1, 0.3, 0.0, 0.2],
            [0.1, 0.4, 0.2, 0.0],
        ]
        self.assertEqual(ranked_successors(costs, 0), [2, 3, 1])


if __name__ == "__main__":
    unittest.main()
