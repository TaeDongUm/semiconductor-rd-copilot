import unittest
from pathlib import Path

from src.export_static_demo import render_static_demo
from src.ui_data import find_default_demo_run, load_demo_bundle

ROOT = Path(__file__).resolve().parents[1]


class StaticDemoTest(unittest.TestCase):
    def test_static_demo_contains_verified_results(self):
        bundle = load_demo_bundle(find_default_demo_run(ROOT))
        page = render_static_demo(bundle)
        self.assertIn("Semiconductor R&D Copilot", page)
        self.assertIn("HBM 적층 수 증가", page)
        self.assertIn("plugged sidewall", page)
        self.assertIn("Unknowns", page)
        self.assertIn("5", page)


if __name__ == "__main__":
    unittest.main()
