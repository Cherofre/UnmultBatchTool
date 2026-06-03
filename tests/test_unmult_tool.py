import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

from unmult_tool import (
    APP_VERSION,
    PREVIEW_EMPTY_TEXT,
    PREVIEW_MAX_EDGE,
    UI_COLORS,
    UnmultSettings,
    UnmultApp,
    check_update_status,
    is_newer_version,
    make_preview_source,
    parse_dropped_paths,
    process_images,
    unmult_image,
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

    def test_app_version_is_release_version(self):
        self.assertEqual(APP_VERSION, "1.0.0")

    def test_is_newer_version_normalizes_release_tags(self):
        self.assertTrue(is_newer_version("v1.0.1", "1.0.0"))
        self.assertFalse(is_newer_version("v1.0.0", "1.0.0"))

    def test_check_update_status_reports_available_release(self):
        title, message = check_update_status(
            "1.0.0",
            lambda: {
                "tag_name": "v1.0.1",
                "html_url": "https://example.test/releases/v1.0.1",
            },
        )

        self.assertEqual(title, "发现新版本")
        self.assertIn("1.0.1", message)
        self.assertIn("https://example.test/releases/v1.0.1", message)

    def test_check_update_status_reports_current_release(self):
        title, message = check_update_status(
            "1.0.0",
            lambda: {"tag_name": "v1.0.0"},
        )

        self.assertEqual(title, "已是最新版本")
        self.assertIn("1.0.0", message)

    def test_make_preview_source_downsamples_large_images_without_mutating_original(self):
        image = Image.new("RGBA", (3000, 1200), (128, 64, 32, 255))

        preview = make_preview_source(image, max_edge=900)

        self.assertEqual(image.size, (3000, 1200))
        self.assertEqual(max(preview.size), 900)
        self.assertEqual(preview.mode, "RGBA")

    def test_make_preview_source_default_keeps_click_preview_lightweight(self):
        image = Image.new("RGBA", (3000, 1200), (128, 64, 32, 255))

        preview = make_preview_source(image)

        self.assertLessEqual(max(preview.size), PREVIEW_MAX_EDGE)
        self.assertEqual(PREVIEW_MAX_EDGE, 512)

    def test_make_preview_source_scales_16_bit_grayscale_png_to_8_bit(self):
        image = Image.new("I;16", (3, 1))
        image.putpixel((0, 0), 0)
        image.putpixel((1, 0), 32768)
        image.putpixel((2, 0), 65535)

        preview = make_preview_source(image, max_edge=900)

        self.assertEqual(preview.mode, "RGBA")
        self.assertEqual(preview.getpixel((0, 0)), (0, 0, 0, 255))
        self.assertEqual(preview.getpixel((1, 0)), (128, 128, 128, 255))
        self.assertEqual(preview.getpixel((2, 0)), (255, 255, 255, 255))

    def test_unmult_image_scales_16_bit_grayscale_before_alpha_estimate(self):
        image = Image.new("I;16", (1, 1))
        image.putpixel((0, 0), 32768)

        output = unmult_image(image, UnmultSettings())

        self.assertEqual(output.getpixel((0, 0)), (255, 255, 255, 128))

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

    def test_about_window_exposes_check_update_button(self):
        app = UnmultApp()
        try:
            app.show_about()
            app.root.update_idletasks()

            self.assertTrue(hasattr(app, "about_update_button"))
            self.assertTrue(hasattr(app, "about_version_label"))
            self.assertIn(APP_VERSION, app.about_version_label.cget("text"))
        finally:
            if hasattr(app, "about_window") and app.about_window.winfo_exists():
                app.about_window.destroy()
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

    def test_slider_click_moves_keyboard_focus_to_slider(self):
        app = UnmultApp()
        try:
            app.root.update()
            slider = app.slider_canvases[0]
            slider.focus_set = Mock()

            slider.event_generate("<Button-1>", x=24, y=14)
            app.root.update()

            slider.focus_set.assert_called_once()
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

    def test_preview_restore_reuses_cached_processed_image(self):
        app = UnmultApp()
        try:
            app.preview_source = Image.new("RGBA", (8, 8), (50, 0, 0, 255))
            processed = Image.new("RGBA", (8, 8), (255, 0, 0, 128))

            with patch("unmult_tool.unmult_image", return_value=processed) as unmult:
                app.update_preview()
                app.show_original_preview()
                app.restore_processed_preview()

            self.assertEqual(unmult.call_count, 1)
        finally:
            self.destroy_app(app)

    def test_compare_button_enter_key_is_momentary_like_mouse_hold(self):
        app = UnmultApp()
        try:
            app.preview_source = Image.new("RGBA", (8, 8), (50, 0, 0, 255))
            app.preview_bg.set("white")
            app.root.update()
            app.update_preview()
            processed_pixel = app.preview_photo._PhotoImage__photo.get(0, 0)

            app.compare_button.focus_force()
            app.root.update()
            app.compare_button.event_generate("<KeyPress-Return>")
            app.root.update()
            original_pixel = app.preview_photo._PhotoImage__photo.get(0, 0)

            app.compare_button.event_generate("<KeyRelease-Return>")
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

    def test_start_batch_continues_after_failed_image(self):
        class ImmediateThread:
            def __init__(self, target, daemon):
                self.target = target

            def start(self):
                self.target()

        app = UnmultApp()
        try:
            app.files = [Path("bad.png"), Path("good.png")]
            with patch("unmult_tool.threading.Thread", ImmediateThread), patch(
                "unmult_tool.process_images",
                side_effect=[OSError("bad image"), [Path("good_unmult.png")]],
            ) as process:
                app.start_batch()

            messages = []
            while not app.worker_queue.empty():
                messages.append(app.worker_queue.get_nowait())

            self.assertEqual(process.call_count, 2)
            self.assertEqual(messages[-1][0], "done")
            self.assertIn("成功 1", messages[-1][1])
            self.assertIn("失败 1", messages[-1][1])
        finally:
            self.destroy_app(app)

    def test_overwrite_mode_keeps_same_stem_batch_outputs_unique(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_dir = root / "first"
            second_dir = root / "second"
            output_dir = root / "out"
            first_dir.mkdir()
            second_dir.mkdir()
            output_dir.mkdir()
            first = first_dir / "same.jpg"
            second = second_dir / "same.jpg"
            Image.new("RGB", (2, 2), (50, 0, 0)).save(first)
            Image.new("RGB", (2, 2), (100, 0, 0)).save(second)

            written = process_images(
                [first, second],
                output_dir,
                UnmultSettings(),
                overwrite=True,
            )

            self.assertEqual(len(written), 2)
            self.assertEqual(len(set(written)), 2)
            self.assertTrue(all(path.exists() for path in written))

    def test_overwrite_mode_does_not_replace_input_png(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            Image.new("RGBA", (2, 2), (25, 0, 0, 255)).save(source)

            written = process_images(
                [source],
                root,
                UnmultSettings(),
                overwrite=True,
            )

            self.assertNotEqual(source.resolve(), written[0].resolve())
            self.assertTrue(written[0].exists())
            with Image.open(source) as image:
                self.assertEqual(image.getpixel((0, 0)), (25, 0, 0, 255))

    def test_overwrite_mode_does_not_replace_existing_numbered_fallback(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            existing_fallback = root / "source_2.png"
            Image.new("RGBA", (2, 2), (25, 0, 0, 255)).save(source)
            Image.new("RGBA", (2, 2), (10, 20, 30, 255)).save(existing_fallback)

            written = process_images(
                [source],
                root,
                UnmultSettings(),
                overwrite=True,
            )

            self.assertEqual(written[0], root / "source_3.png")
            with Image.open(existing_fallback) as image:
                self.assertEqual(image.getpixel((0, 0)), (10, 20, 30, 255))

    def test_load_selected_preview_clears_stale_preview_on_open_error(self):
        app = UnmultApp()
        try:
            app.files = [Path("broken.png")]
            app.preview_source = Image.new("RGBA", (4, 4), (50, 0, 0, 255))
            app.preview_label.configure(text="预览：old.png")
            app.messagebox.showerror = Mock()

            with patch("unmult_tool.Image.open", side_effect=OSError("broken image")):
                app.load_selected_preview()

            self.assertIsNone(app.preview_source)
            self.assertIsNone(app.preview_photo)
            self.assertEqual(app.preview_label.cget("text"), PREVIEW_EMPTY_TEXT)
            self.assertIn("预览失败", app.status.get())
            app.messagebox.showerror.assert_called_once()
        finally:
            self.destroy_app(app)

    def test_load_selected_preview_schedules_processing_instead_of_blocking_click(self):
        with TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "demo.png"
            Image.new("RGBA", (4, 4), (50, 0, 0, 255)).save(image_path)

            app = UnmultApp()
            try:
                app.files = [image_path]
                app.update_preview = Mock()
                app.schedule_preview_update = Mock()

                app.load_selected_preview()

                app.update_preview.assert_not_called()
                app.schedule_preview_update.assert_called_once()
            finally:
                self.destroy_app(app)

    def test_refresh_file_list_preserves_current_selection(self):
        app = UnmultApp()
        try:
            first = Path("first.png")
            second = Path("second.png")
            third = Path("third.png")
            app.files = [first, second]
            app.refresh_file_list()
            app.file_list.selection_set(1)
            app.file_list.activate(1)

            app.files.append(third)
            app.refresh_file_list()

            self.assertEqual(app.file_list.curselection(), (1,))
            self.assertEqual(app.preview_position.get(), "2 / 3")
        finally:
            self.destroy_app(app)

    def test_refresh_file_list_clears_preview_when_selected_file_is_removed(self):
        app = UnmultApp()
        try:
            first = Path("first.png")
            second = Path("second.png")
            app.files = [first, second]
            app.refresh_file_list()
            app.file_list.selection_set(1)
            app.file_list.activate(1)
            app.preview_source = Image.new("RGBA", (4, 4), (50, 0, 0, 255))
            app.preview_label.configure(text="预览：second.png")

            app.files = [first]
            app.refresh_file_list()

            self.assertEqual(app.file_list.curselection(), ())
            self.assertIsNone(app.preview_source)
            self.assertIsNone(app.preview_photo)
            self.assertEqual(app.preview_label.cget("text"), PREVIEW_EMPTY_TEXT)
            self.assertEqual(app.preview_position.get(), "0 / 1")
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
