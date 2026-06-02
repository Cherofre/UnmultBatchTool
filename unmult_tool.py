from __future__ import annotations

import argparse
import math
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence
from urllib.parse import unquote, urlparse

from PIL import Image, ImageTk


SUPPORTED_EXTENSIONS = {
    ".bmp",
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}

PREVIEW_MAX_EDGE = 900


def _path_from_drop_item(item: str) -> Path:
    if item.startswith("file://"):
        parsed = urlparse(item)
        path = unquote(parsed.path)
        if len(path) >= 3 and path[0] == "/" and path[2] == ":":
            path = path[1:]
        return Path(path)
    return Path(item)


def parse_dropped_paths(
    data: str,
    splitlist: Callable[[str], Sequence[str]],
) -> list[Path]:
    if not data.strip():
        return []
    return [_path_from_drop_item(item) for item in splitlist(data) if item]


def make_preview_source(
    image: Image.Image,
    max_edge: int = PREVIEW_MAX_EDGE,
) -> Image.Image:
    preview = image.convert("RGBA")
    if max(preview.size) > max_edge:
        preview = preview.copy()
        preview.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    return preview


@dataclass(frozen=True)
class UnmultSettings:
    black_point: int = 0
    white_point: int = 255
    gamma: float = 1.0
    mode: str = "max"
    premultiplied_output: bool = False


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _luminance(r: int, g: int, b: int, mode: str) -> float:
    if mode == "luma":
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    if mode == "average":
        return (r + g + b) / 3
    return max(r, g, b)


def unmult_image(image: Image.Image, settings: UnmultSettings) -> Image.Image:
    """Remove a black matte by estimating alpha and un-premultiplying RGB."""
    source = image.convert("RGBA")
    pixels = source.load()
    width, height = source.size
    output = Image.new("RGBA", source.size)
    out_pixels = output.load()

    black = _clamp(settings.black_point, 0, 254)
    white = _clamp(settings.white_point, black + 1, 255)
    scale = 255 / (white - black)
    gamma = max(0.05, settings.gamma)

    for y in range(height):
        for x in range(width):
            r, g, b, existing_alpha = pixels[x, y]
            brightness = _luminance(r, g, b, settings.mode)
            alpha_float = _clamp((brightness - black) * scale / 255, 0, 1)
            if gamma != 1:
                alpha_float = math.pow(alpha_float, gamma)
            alpha_float *= existing_alpha / 255
            alpha = int(round(alpha_float * 255))

            if alpha <= 0:
                out_pixels[x, y] = (0, 0, 0, 0)
                continue

            if settings.premultiplied_output:
                out_pixels[x, y] = (r, g, b, alpha)
                continue

            inv_alpha = 255 / alpha
            out_r = int(round(_clamp(r * inv_alpha, 0, 255)))
            out_g = int(round(_clamp(g * inv_alpha, 0, 255)))
            out_b = int(round(_clamp(b * inv_alpha, 0, 255)))
            out_pixels[x, y] = (out_r, out_g, out_b, alpha)

    return output


def collect_images(paths: Sequence[Path], recursive: bool = False) -> list[Path]:
    images: list[Path] = []
    for path in paths:
        if path.is_dir():
            iterator = path.rglob("*") if recursive else path.iterdir()
            images.extend(
                item
                for item in iterator
                if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS
            )
            continue

        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            images.append(path)

    return sorted(dict.fromkeys(images))


def output_path_for(
    input_path: Path,
    output_dir: Path,
    suffix: str,
    overwrite: bool,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    if overwrite:
        return output_dir / f"{input_path.stem}.png"

    candidate = output_dir / f"{input_path.stem}{suffix}.png"
    if not candidate.exists():
        return candidate

    index = 2
    while True:
        numbered = output_dir / f"{input_path.stem}{suffix}_{index}.png"
        if not numbered.exists():
            return numbered
        index += 1


def process_images(
    image_paths: Iterable[Path],
    output_dir: Path,
    settings: UnmultSettings,
    suffix: str = "_unmult",
    overwrite: bool = False,
) -> list[Path]:
    written: list[Path] = []
    for image_path in image_paths:
        with Image.open(image_path) as image:
            output = unmult_image(image, settings)
        destination = output_path_for(image_path, output_dir, suffix, overwrite)
        output.save(destination, "PNG")
        written.append(destination)
    return written


def checkerboard(size: tuple[int, int], cell: int = 16) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, "#d9d9d9")
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            if (x // cell + y // cell) % 2:
                pixels[x, y] = (245, 245, 245)
    return image


def composite_preview(image: Image.Image, background: str = "checker") -> Image.Image:
    rgba = image.convert("RGBA")
    if background == "black":
        base = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
    elif background == "white":
        base = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    else:
        base = checkerboard(rgba.size).convert("RGBA")
    base.alpha_composite(rgba)
    return base.convert("RGB")


class UnmultApp:
    def __init__(self) -> None:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk

        try:
            from tkinterdnd2 import DND_FILES, TkinterDnD
        except ImportError:
            DND_FILES = None
            TkinterDnD = None

        self.tk = tk
        self.ttk = ttk
        self.filedialog = filedialog
        self.messagebox = messagebox
        self.drop_file_token = DND_FILES

        self.root = TkinterDnD.Tk() if TkinterDnD is not None else tk.Tk()
        self.root.title("Unmult 去黑批处理工具")
        self.root.geometry("1040x680")
        self.root.minsize(860, 560)

        self.files: list[Path] = []
        self.preview_source: Image.Image | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.preview_job: str | None = None
        self.worker_queue: queue.Queue[tuple[str, str]] = queue.Queue()

        self.black_point = tk.IntVar(value=0)
        self.white_point = tk.IntVar(value=255)
        self.gamma = tk.DoubleVar(value=1.0)
        self.mode = tk.StringVar(value="max")
        self.preview_bg = tk.StringVar(value="checker")
        self.suffix = tk.StringVar(value="_unmult")
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "unmult_output"))
        self.recursive = tk.BooleanVar(value=False)
        self.overwrite = tk.BooleanVar(value=False)
        self.premultiplied_output = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="请选择图片或文件夹。")

        self._build_ui()
        self._enable_drag_and_drop()
        self._poll_worker_queue()

    def run(self) -> None:
        self.root.mainloop()

    def _build_ui(self) -> None:
        tk = self.tk
        ttk = self.ttk
        root = self.root

        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        side = ttk.Frame(root, padding=10)
        side.grid(row=0, column=0, sticky="nsew")
        side.columnconfigure(0, weight=1)
        side.rowconfigure(4, weight=1)

        actions = ttk.Frame(side)
        actions.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.columnconfigure(2, weight=1)

        ttk.Button(actions, text="添加图片", command=self.add_files).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 4),
        )
        ttk.Button(actions, text="添加文件夹", command=self.add_folder).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=4,
        )
        ttk.Button(actions, text="清空", command=self.clear_files).grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(4, 0),
        )

        ttk.Checkbutton(side, text="递归读取子文件夹", variable=self.recursive).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(0, 6),
        )

        output = ttk.LabelFrame(side, text="批量导出", padding=8)
        output.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        output.columnconfigure(0, weight=1)
        ttk.Entry(output, textvariable=self.output_dir).grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 6),
        )
        ttk.Button(output, text="选择输出目录", command=self.pick_output_dir).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 6),
        )
        ttk.Label(output, text="文件后缀").grid(row=2, column=0, sticky="w")
        ttk.Entry(output, textvariable=self.suffix).grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(0, 6),
        )
        ttk.Checkbutton(output, text="覆盖同名 PNG", variable=self.overwrite).grid(
            row=4,
            column=0,
            sticky="w",
            pady=(0, 6),
        )
        ttk.Button(output, text="开始批量处理", command=self.start_batch).grid(
            row=5,
            column=0,
            sticky="ew",
        )

        settings = ttk.LabelFrame(side, text="去黑参数", padding=8)
        settings.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        settings.columnconfigure(1, weight=1)

        self._add_slider(settings, "黑场", self.black_point, 0, 240, 0)
        self._add_slider(settings, "白场", self.white_point, 16, 255, 1)
        self._add_slider(settings, "Alpha Gamma", self.gamma, 0.25, 3, 2)

        ttk.Label(settings, text="亮度算法").grid(row=3, column=0, sticky="w", pady=3)
        mode_box = ttk.Combobox(
            settings,
            textvariable=self.mode,
            state="readonly",
            values=("max", "luma", "average"),
            width=12,
        )
        mode_box.grid(row=3, column=1, sticky="ew", pady=3)
        mode_box.bind("<<ComboboxSelected>>", lambda _event: self.schedule_preview_update())

        ttk.Label(settings, text="预览底色").grid(row=4, column=0, sticky="w", pady=3)
        bg_box = ttk.Combobox(
            settings,
            textvariable=self.preview_bg,
            state="readonly",
            values=("checker", "black", "white"),
            width=12,
        )
        bg_box.grid(row=4, column=1, sticky="ew", pady=3)
        bg_box.bind("<<ComboboxSelected>>", lambda _event: self.schedule_preview_update())

        ttk.Checkbutton(
            settings,
            text="输出保持预乘 RGB",
            variable=self.premultiplied_output,
            command=self.schedule_preview_update,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))

        list_frame = ttk.LabelFrame(side, text="图片列表", padding=8)
        list_frame.grid(row=4, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.file_list = tk.Listbox(list_frame, width=34, height=7)
        list_scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        self.file_list.configure(yscrollcommand=list_scrollbar.set)
        list_scrollbar.configure(command=self.file_list.yview)
        self.file_list.grid(row=0, column=0, sticky="nsew")
        list_scrollbar.grid(row=0, column=1, sticky="ns")
        self.file_list.bind(
            "<<ListboxSelect>>",
            lambda _event: self.load_selected_preview(),
        )

        main = ttk.Frame(root, padding=(0, 10, 10, 10))
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        self.preview_label = ttk.Label(main, anchor="center")
        self.preview_label.grid(row=0, column=0, sticky="nsew")
        self.preview_label.bind(
            "<Configure>",
            lambda _event: self.schedule_preview_update(delay=180),
        )

        ttk.Label(main, textvariable=self.status, anchor="w").grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(10, 0),
        )

    def _add_slider(
        self,
        parent,
        label: str,
        variable,
        low: float,
        high: float,
        row: int,
    ) -> None:
        ttk = self.ttk
        tk = self.tk
        is_integer = variable.__class__.__name__ == "IntVar"

        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        slider = ttk.Scale(
            parent,
            from_=low,
            to=high,
            variable=variable,
            command=lambda _value: self.schedule_preview_update(),
        )
        slider.grid(row=row, column=1, sticky="ew", pady=3)

        value_text = tk.StringVar()
        value_entry = ttk.Entry(
            parent,
            width=7,
            textvariable=value_text,
            justify="right",
        )
        value_entry.grid(row=row, column=2, sticky="e", padx=(6, 0))

        def formatted_value() -> str:
            value = variable.get()
            if is_integer:
                return str(int(round(value)))
            return f"{float(value):.2f}"

        def refresh_entry(*_args) -> None:
            if value_entry.focus_get() == value_entry:
                return
            value_text.set(formatted_value())

        def commit_entry(_event=None) -> str:
            raw_value = value_text.get().strip()
            try:
                parsed = float(raw_value)
            except ValueError:
                self.status.set(f"{label} 请输入数字。")
                value_text.set(formatted_value())
                return "break"

            clamped = _clamp(parsed, low, high)
            if is_integer:
                variable.set(int(round(clamped)))
            else:
                variable.set(round(clamped, 3))
            value_text.set(formatted_value())
            self.update_preview()
            return "break"

        variable.trace_add("write", refresh_entry)
        value_entry.bind("<Return>", commit_entry)
        value_entry.bind("<FocusOut>", commit_entry)
        refresh_entry()

    def _enable_drag_and_drop(self) -> None:
        if self.drop_file_token is None:
            return

        for widget in (self.root, self.file_list, self.preview_label):
            widget.drop_target_register(self.drop_file_token)
            widget.dnd_bind("<<Drop>>", self._handle_drop)

    def _handle_drop(self, event) -> str:
        paths = parse_dropped_paths(event.data, self.root.tk.splitlist)
        self.add_paths(paths)
        return "break"

    def schedule_preview_update(self, delay: int = 120) -> None:
        if self.preview_source is None:
            return
        if self.preview_job is not None:
            self.root.after_cancel(self.preview_job)
        self.preview_job = self.root.after(delay, self._run_scheduled_preview_update)

    def _run_scheduled_preview_update(self) -> None:
        self.preview_job = None
        self.update_preview()

    def settings(self) -> UnmultSettings:
        white_point = max(self.white_point.get(), self.black_point.get() + 1)
        return UnmultSettings(
            black_point=self.black_point.get(),
            white_point=white_point,
            gamma=self.gamma.get(),
            mode=self.mode.get(),
            premultiplied_output=self.premultiplied_output.get(),
        )

    def add_files(self) -> None:
        selected = self.filedialog.askopenfilenames(
            title="选择图片",
            filetypes=(
                ("Image files", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp"),
                ("All files", "*.*"),
            ),
        )
        self.add_paths([Path(item) for item in selected])

    def add_folder(self) -> None:
        selected = self.filedialog.askdirectory(title="选择图片文件夹")
        if selected:
            self.add_paths([Path(selected)])

    def add_paths(self, paths: Sequence[Path]) -> None:
        found = collect_images(paths, recursive=self.recursive.get())
        known = set(self.files)
        self.files.extend(path for path in found if path not in known)
        self.refresh_file_list()

        if self.files and self.preview_source is None:
            self.file_list.selection_set(0)
            self.load_selected_preview()

        self.status.set(f"已载入 {len(self.files)} 张图片。")

    def clear_files(self) -> None:
        self.files.clear()
        self.preview_source = None
        self.file_list.delete(0, self.tk.END)
        self.preview_label.configure(image="", text="")
        self.status.set("列表已清空。")

    def refresh_file_list(self) -> None:
        self.file_list.delete(0, self.tk.END)
        for path in self.files:
            self.file_list.insert(self.tk.END, str(path))

    def selected_file(self) -> Path | None:
        selected = self.file_list.curselection()
        if not selected:
            return self.files[0] if self.files else None
        return self.files[selected[0]]

    def load_selected_preview(self) -> None:
        path = self.selected_file()
        if path is None:
            return

        try:
            with Image.open(path) as image:
                self.preview_source = make_preview_source(image)
            self.update_preview()
            self.status.set(f"预览：{path.name}")
        except OSError as exc:
            self.messagebox.showerror("无法打开图片", f"{path}\n\n{exc}")

    def update_preview(self) -> None:
        if self.preview_source is None:
            return
        if self.preview_job is not None:
            self.root.after_cancel(self.preview_job)
            self.preview_job = None

        label_width = max(320, self.preview_label.winfo_width())
        label_height = max(260, self.preview_label.winfo_height())

        try:
            processed = unmult_image(self.preview_source, self.settings())
            preview = composite_preview(processed, self.preview_bg.get())
            preview.thumbnail(
                (label_width - 20, label_height - 20),
                Image.Resampling.LANCZOS,
            )
            self.preview_photo = ImageTk.PhotoImage(preview)
            self.preview_label.configure(image=self.preview_photo)
        except Exception as exc:
            self.status.set(f"预览失败：{exc}")

    def pick_output_dir(self) -> None:
        selected = self.filedialog.askdirectory(title="选择输出目录")
        if selected:
            self.output_dir.set(selected)

    def start_batch(self) -> None:
        if not self.files:
            self.messagebox.showwarning("没有图片", "请先添加图片或文件夹。")
            return

        output_dir = Path(self.output_dir.get()).expanduser()
        settings = self.settings()
        suffix = self.suffix.get() or "_unmult"
        overwrite = self.overwrite.get()
        files = list(self.files)
        self.status.set(f"正在处理 0 / {len(files)} ...")

        def worker() -> None:
            try:
                written: list[Path] = []
                for index, image_path in enumerate(files, 1):
                    output = process_images(
                        [image_path],
                        output_dir,
                        settings,
                        suffix,
                        overwrite,
                    )
                    written.extend(output)
                    self.worker_queue.put(
                        ("progress", f"正在处理 {index} / {len(files)} ...")
                    )
                self.worker_queue.put(
                    ("done", f"完成：已输出 {len(written)} 个 PNG 到 {output_dir}")
                )
            except Exception as exc:
                self.worker_queue.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_worker_queue(self) -> None:
        try:
            while True:
                kind, message = self.worker_queue.get_nowait()
                self.status.set(message)
                if kind == "done":
                    self.messagebox.showinfo("批处理完成", message)
                elif kind == "error":
                    self.messagebox.showerror("批处理失败", message)
        except queue.Empty:
            pass

        self.root.after(120, self._poll_worker_queue)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unmult-style black matte remover.")
    parser.add_argument(
        "input",
        nargs="*",
        type=Path,
        help="Input image files or folders.",
    )
    parser.add_argument("-o", "--output", type=Path, default=Path("unmult_output"))
    parser.add_argument("--black-point", type=int, default=0)
    parser.add_argument("--white-point", type=int, default=255)
    parser.add_argument("--gamma", type=float, default=1.0)
    parser.add_argument("--mode", choices=("max", "luma", "average"), default="max")
    parser.add_argument("--suffix", default="_unmult")
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--premultiplied-output", action="store_true")
    parser.add_argument("--gui", action="store_true", help="Open the graphical batch tool.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.gui or not args.input:
        UnmultApp().run()
        return 0

    inputs = collect_images(args.input, recursive=args.recursive)
    if not inputs:
        parser.error("No supported images were found.")

    settings = UnmultSettings(
        black_point=args.black_point,
        white_point=args.white_point,
        gamma=args.gamma,
        mode=args.mode,
        premultiplied_output=args.premultiplied_output,
    )
    written = process_images(inputs, args.output, settings, args.suffix, args.overwrite)
    print(f"Processed {len(written)} image(s).")
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
