from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rogue_ai_fieldbook.ace_step import AceStepV1Session  # noqa: E402


class FakePipeline:
    def __init__(self) -> None:
        self.arguments = None

    def __call__(self, **kwargs):
        self.arguments = kwargs
        return {"actual_seeds": kwargs["manual_seeds"], "retake_seeds": kwargs.get("retake_seeds")}


class AceStepAdapterTests(unittest.TestCase):
    def test_session_forwards_reproducible_seed_and_instrumental_contract(self) -> None:
        pipeline = FakePipeline()
        session = AceStepV1Session(Path("checkpoints"), pipeline=pipeline)
        with tempfile.TemporaryDirectory() as directory:
            report = session.generate(
                prompt="calm instrumental",
                duration_seconds=30.0,
                output_path=Path(directory) / "candidate.wav",
                seed=12345,
            )
        self.assertEqual(pipeline.arguments["manual_seeds"], [12345])
        self.assertEqual(pipeline.arguments["lyrics"], "[instrumental]")
        self.assertEqual(report["actual_seeds"], [12345])

    def test_extend_right_keeps_context_and_generates_requested_tail(self) -> None:
        pipeline = FakePipeline()
        session = AceStepV1Session(Path("checkpoints"), pipeline=pipeline)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context = root / "prior.wav"
            context.write_bytes(b"context")
            report = session.extend_right(
                context_path=context,
                context_seconds=30,
                extension_seconds=120,
                prompt="continuous calm instrumental",
                output_path=root / "combined.wav",
                seed=42,
            )
        self.assertEqual(pipeline.arguments["task"], "extend")
        self.assertEqual(pipeline.arguments["audio_duration"], 30)
        self.assertEqual(pipeline.arguments["repaint_start"], 0)
        self.assertEqual(pipeline.arguments["repaint_end"], 150)
        self.assertEqual(pipeline.arguments["retake_seeds"], [42])
        self.assertEqual(report["combined_seconds"], 150)

    def test_extend_right_enforces_ace_step_limit(self) -> None:
        pipeline = FakePipeline()
        session = AceStepV1Session(Path("checkpoints"), pipeline=pipeline)
        with tempfile.TemporaryDirectory() as directory:
            context = Path(directory) / "prior.wav"
            context.write_bytes(b"context")
            with self.assertRaises(ValueError):
                session.extend_right(
                    context_path=context,
                    context_seconds=30,
                    extension_seconds=220,
                    prompt="too long",
                    output_path=Path(directory) / "combined.wav",
                    seed=1,
                )


if __name__ == "__main__":
    unittest.main()
