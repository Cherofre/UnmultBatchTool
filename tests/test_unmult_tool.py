import unittest
from pathlib import Path

from PIL import Image

from unmult_tool import (
    PREVIEW_EMPTY_TEXT,
    UI_COLORS,
    UnmultApp,
    make_preview_source,
    parse_dropped_paths,
)


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

    def test_app_uses_central_light_palette_for_root_background(self):
        app = UnmultApp()
        try:
            app.root.update_idletasks()
            self.assertEqual(app.root.cget("background"), UI_COLORS["app_bg"])
            self.assertTrue(hasattr(app, "style"))
        finally:
            app.root.destroy()

    def test_export_section_is_above_settings_in_sidebar(self):
        app = UnmultApp()
        try:
            app.root.update_idletasks()
            export_row = int(app.export_section.grid_info()["row"])
            settings_row = int(app.settings_section.grid_info()["row"])
            list_row = int(app.file_list_section.grid_info()["row"])

            self.assertLess(export_row, settings_row)
            self.assertLess(settings_row, list_row)
        finally:
            app.root.destroy()

    def test_sidebar_sections_use_flat_card_frames(self):
        app = UnmultApp()
        try:
            app.root.update_idletasks()

            self.assertEqual(app.import_section.winfo_class(), "Frame")
            self.assertEqual(app.export_section.cget("background"), UI_COLORS["card_bg"])
            self.assertEqual(app.file_list.cget("background"), UI_COLORS["surface"])
        finally:
            app.root.destroy()

    def test_clear_files_restores_preview_empty_state(self):
        app = UnmultApp()
        try:
            app.preview_label.configure(text="预览：demo.png")
            app.clear_files()
            self.assertEqual(app.preview_label.cget("text"), PREVIEW_EMPTY_TEXT)
        finally:
            app.root.destroy()


if __name__ == "__main__":
    unittest.main()
