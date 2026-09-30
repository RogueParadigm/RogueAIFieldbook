from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rogue_ai_fieldbook.core import stable_seed  # noqa: E402


class LegacySeedTests(unittest.TestCase):
    def test_sha1_mode_matches_historical_aiaudio_seed(self) -> None:
        name = "SFX_Shot"
        historical = int(hashlib.sha1(name.encode("utf-8")).hexdigest()[:8], 16)
        self.assertEqual(stable_seed(name, algorithm="sha1"), historical)


if __name__ == "__main__":
    unittest.main()

