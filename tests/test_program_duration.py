from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rogue_ai_fieldbook.continuation import (  # noqa: E402
    LoopBankPlan,
    closest_loop_count,
    program_duration_seconds,
)


class ProgramDurationTests(unittest.TestCase):
    def test_intro_one_loop_and_outro_last_three_minutes(self) -> None:
        plan = LoopBankPlan()
        self.assertEqual(program_duration_seconds(plan, 1), 180)

    def test_loop_crossfades_are_counted_once(self) -> None:
        plan = LoopBankPlan()
        self.assertEqual(program_duration_seconds(plan, 3), 412)

    def test_target_duration_selects_nearest_realisable_loop_count(self) -> None:
        plan = LoopBankPlan()
        count, actual = closest_loop_count(plan, 10 * 60)
        self.assertEqual(count, 5)
        self.assertEqual(actual, 644)


if __name__ == "__main__":
    unittest.main()
