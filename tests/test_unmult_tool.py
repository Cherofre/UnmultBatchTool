import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

from unmult_tool import (
    PREVIEW_EMPTY_TEXT,
    UI_COLORS,
    UnmultApp,
    make_preview_source,
    parse_dropped_paths,
)


class UnmultToolTests(unittest.TestCase):
    def destroy_app(self, app):
        if app.worker_poll_job is not None:
            app.root.after_cancel(app.worker_poll_job)
        app.root.destroy()

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
            self.destroy_app(app)

    def test_layout_places_export_below_preview_and_settings_in_sidebar(self):
        app = UnmultApp()
        try:
            app.root.update_idletasks()
            preview_row = int(app.preview_frame.grid_info()["row"])
            export_row = int(app.export_section.grid_info()["row"])
            import_row = int(app.import_section.grid_info()["row"])
            list_row = int(app.file_list_section.grid_info()["row"])
            settings_row = int(app.settings_section.grid_info()["row"])

            self.assertLess(preview_row, export_row)
            self.assertLess(import_row, list_row)
            self.assertLess(list_row, settings_row)
            self.assertEqual(app.export_section.master, app.preview_column)
        finally:
            self.destroy_app(app)

    def test_sidebar_sections_use_flat_card_frames(self):
        app = UnmultApp()
        try:
            app.root.update_idletasks()

            self.assertEqual(app.import_section.winfo_class(), "Frame")
            self.assertEqual(app.export_section.cget("background"), UI_COLORS["card_bg"])
            self.assertEqual(app.file_list.cget("background"), UI_COLORS["surface"])
        finally:
            self.destroy_app(app)

    def test_top_toolbar_replaces_large_header(self):
        app = UnmultApp()
        try:
            app.root.update_idletasks()

            self.assertTrue(hasattr(app, "toolbar"))
            self.assertFalse(hasattr(app, "header"))
            self.assertEqual(int(app.toolbar.grid_info()["row"]), 0)
        finally:
            self.destroy_app(app)

    def test_default_layout_keeps_export_controls_visible(self):
        app = UnmultApp()
        try:
            app.root.update()
            export_bottom = app.export_section.winfo_rooty() + app.export_section.winfo_height()
            status_top = app.status_bar.winfo_rooty()

            self.assertLess(export_bottom, status_top)
        finally:
            self.destroy_app(app)

    def test_settings_sliders_use_visible_custom_canvas_tracks(self):
        app = UnmultApp()
        try:
            app.root.update_idletasks()

            self.assertEqual(len(app.slider_canvases), 3)
            fills = {
                app.slider_canvases[0].itemcget(item, "fill")
                for item in app.slider_canvases[0].find_all()
            }
            self.assertIn(UI_COLORS["slider_track"], fills)
            self.assertIn(UI_COLORS["slider_fill"], fills)
        finally:
            self.destroy_app(app)

    def test_preview_compare_button_shows_original_until_release(self):
        app = UnmultApp()
        try:
            app.preview_source = Image.new("RGBA", (8, 8), (50, 0, 0, 255))
            app.preview_bg.set("white")
            app.root.update()
            app.update_preview()
            processed_pixel = app.preview_photo._PhotoImage__photo.get(0, 0)

            app.compare_button.event_generate("<ButtonPress-1>", x=10, y=10)
            app.root.update()
            original_pixel = app.preview_photo._PhotoImage__photo.get(0, 0)

            app.compare_button.event_generate("<ButtonRelease-1>", x=10, y=10)
            app.root.update()
            restored_pixel = app.preview_photo._PhotoImage__photo.get(0, 0)

            self.assertNotEqual(processed_pixel, (50, 0, 0))
            self.assertEqual(original_pixel, (50, 0, 0))
            self.assertEqual(restored_pixel, processed_pixel)
        finally:
            self.destroy_app(app)

    def test_start_batch_ignores_duplicate_launch_while_processing(self):
        app = UnmultApp()
        try:
            app.files = [Path("demo.png")]
            with patch("unmult_tool.threading.Thread") as thread_cls:
                thread = Mock()
                thread_cls.return_value = thread

                app.start_batch()
                app.start_batch()

            self.assertEqual(thread_cls.call_count, 1)
            self.assertEqual(thread.start.call_count, 1)
        finally:
            self.destroy_app(app)

    def test_clear_files_restores_preview_empty_state(self):
        app = UnmultApp()
        try:
            app.preview_label.configure(text="预览：demo.png")
            app.clear_files()
            self.assertEqual(app.preview_label.cget("text"), PREVIEW_EMPTY_TEXT)
        finally:
            self.destroy_app(app)


if __name__ == "__main__":
    unittest.main()
