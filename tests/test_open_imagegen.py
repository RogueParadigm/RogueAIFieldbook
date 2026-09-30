from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / ".agents"
    / "skills"
    / "open-imagegen"
    / "scripts"
    / "open_imagegen.py"
)
SPEC = importlib.util.spec_from_file_location("open_imagegen", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class OpenImageGenTests(unittest.TestCase):
    def test_parse_size(self) -> None:
        self.assertEqual(MODULE.parse_size("1024x768"), (1024, 768))

    def test_parse_size_rejects_non_multiple_of_16(self) -> None:
        with self.assertRaises(SystemExit):
            MODULE.parse_size("1023x768")

    def test_parse_region(self) -> None:
        self.assertEqual(MODULE.parse_region("51,299,272,362"), (51, 299, 272, 362))

    def test_prompt_augmentation_preserves_requested_text(self) -> None:
        prompt = MODULE.augment_prompt(
            "A neon storefront",
            {"use_case": "ads-marketing", "text": "ROGUE", "constraints": "exactly once"},
            True,
        )
        self.assertIn("Primary request: A neon storefront", prompt)
        self.assertIn('Text (verbatim): "ROGUE"', prompt)

    def test_default_supports_generation_and_editing(self) -> None:
        spec = MODULE.model_spec("auto")
        self.assertEqual(spec.alias, "flux2-klein-4b")
        self.assertEqual(set(spec.modes), {"generate", "edit"})
        self.assertEqual(spec.license, "Apache-2.0")

    def test_sensenova_quality_profile_is_unified_and_quantized(self) -> None:
        spec = MODULE.model_spec("sensenova-u1.5-q8")
        self.assertEqual(set(spec.modes), {"generate", "edit"})
        self.assertEqual(spec.runtime, "sensenova")
        self.assertEqual(spec.gguf_filename, "SenseNova-U1.5-8B-MoT-Q8_0.gguf")
        self.assertTrue(spec.tested_here)

    def test_sensenova_parser_exposes_reference_budget(self) -> None:
        args = MODULE.build_parser().parse_args(
            [
                "compose",
                "--model",
                "sensenova-u1.5-q8",
                "--image",
                "identity.png",
                "--prompt",
                "Create a new scene",
                "--input-max-pixels",
                "1048576",
            ]
        )
        self.assertEqual(args.input_max_pixels, 1_048_576)

    def test_output_paths_are_non_destructive_variants(self) -> None:
        paths = MODULE.output_paths("result.png", None, 3, "png")
        self.assertEqual([path.name for path in paths], ["result-1.png", "result-2.png", "result-3.png"])

    def test_raw_edit_path_is_a_distinct_sibling(self) -> None:
        self.assertEqual(
            MODULE.raw_edit_path(Path("panel.png")), Path("panel.raw-edit.png")
        )

    def test_portable_path_uses_repo_relative_paths(self) -> None:
        absolute = SCRIPT.parents[4] / "output" / "example.png"
        self.assertEqual(MODULE.portable_path(absolute), "output/example.png")

    def test_portable_path_redacts_external_directories(self) -> None:
        external = Path("Z:/private-project/references/identity.png")
        self.assertEqual(
            MODULE.portable_path(external), "external/references/identity.png"
        )

    def test_compose_command_and_reference_roles(self) -> None:
        args = MODULE.build_parser().parse_args(
            [
                "compose",
                "--image",
                "identity.png",
                "--image-role",
                "absolute identity",
                "--prompt",
                "Create a new scene",
            ]
        )
        self.assertEqual(args.command, "compose")
        self.assertEqual(args.image_role, ["absolute identity"])

    def test_protection_mask_preserves_white_pixels(self) -> None:
        from PIL import Image

        original = Image.new("RGB", (2, 1), "red")
        edited = Image.new("RGB", (2, 1), "blue")
        with tempfile.TemporaryDirectory() as directory:
            mask_path = Path(directory) / "mask.png"
            mask = Image.new("L", (2, 1))
            mask.putdata([255, 0])
            mask.save(mask_path)
            result = MODULE.apply_mask(
                original, edited, mask_path, 0, "preserve-white"
            ).convert("RGB")
        self.assertEqual(result.getpixel((0, 0)), (255, 0, 0))
        self.assertEqual(result.getpixel((1, 0)), (0, 0, 255))

    def test_mask_metrics_report_edit_and_protection_regions(self) -> None:
        from PIL import Image

        original = Image.new("RGB", (2, 1), "red")
        result = original.copy()
        result.putpixel((0, 0), (0, 0, 255))
        with tempfile.TemporaryDirectory() as directory:
            mask_path = Path(directory) / "mask.png"
            mask = Image.new("L", (2, 1))
            mask.putdata([255, 0])
            mask.save(mask_path)
            metrics = MODULE.mask_edit_metrics(original, result, mask_path)
        self.assertEqual(metrics["editable_changed_pct"], 100.0)
        self.assertEqual(metrics["protected_exact_pct"], 100.0)
        self.assertEqual(metrics["whole_changed_pct"], 50.0)

    def test_focus_box_expands_editable_mask(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            mask_path = Path(directory) / "mask.png"
            mask = Image.new("L", (10, 10), 0)
            for y in range(4, 6):
                for x in range(4, 6):
                    mask.putpixel((x, y), 255)
            mask.save(mask_path)
            box = MODULE.focus_box_from_mask(
                mask_path, (10, 10), "edit-white", 2
            )
        self.assertEqual(box, (2, 2, 8, 8))


if __name__ == "__main__":
    unittest.main()
