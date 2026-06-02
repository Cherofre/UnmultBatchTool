import unittest
from pathlib import Path

from PIL import Image

from unmult_tool import make_preview_source, parse_dropped_paths


class UnmultToolTests(unittest.TestCase):
    def test_parse_dropped_paths_handles_multiple_tk_paths(self):
        def splitlist(data):
            self.assertEqual(data, "{D:/素材/a b.png} D:/素材/c.png")
            return ("D:/素材/a b.png", "D:/素材/c.png")

        paths = parse_dropped_paths("{D:/素材/a b.png} D:/素材/c.png", splitlist)

        self.assertEqual(paths, [Path("D:/素材/a b.png"), Path("D:/素材/c.png")])

    def test_make_preview_source_downsamples_large_images_without_mutating_original(self):
        image = Image.new("RGBA", (3000, 1200), (128, 64, 32, 255))

        preview = make_preview_source(image, max_edge=900)

        self.assertEqual(image.size, (3000, 1200))
        self.assertEqual(max(preview.size), 900)
        self.assertEqual(preview.mode, "RGBA")


if __name__ == "__main__":
    unittest.main()
