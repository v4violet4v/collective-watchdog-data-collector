import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from normalize import normalize_events, public_image_url
from summaries import lightweight_events


class EventImageTests(unittest.TestCase):
    def test_images_survive_summary_export(self):
        events, _ = normalize_events([{
            "title": "Fed Decision in October", "slug": "fed-october",
            "image": " https://images.example/fed.jpg ",
            "icon": "https://images.example/fed-icon.png", "markets": [],
        }], "2026-09-27T00:00:00Z")
        summary = lightweight_events(events)[0]
        self.assertEqual(summary["image_url"], "https://images.example/fed.jpg")
        self.assertEqual(summary["icon_url"], "https://images.example/fed-icon.png")

    def test_missing_and_unsafe_urls(self):
        for value in (None, {}, "", "javascript:alert(1)", "data:image/png;base64,x",
                      "http://images.example/a.png", "https://user:pass@example.com/a", "https://[bad"):
            self.assertIsNone(public_image_url(value))
        events, _ = normalize_events([{"title": "Legacy event"}], "now")
        self.assertIsNone(events[0]["image_url"])


if __name__ == "__main__":
    unittest.main()
