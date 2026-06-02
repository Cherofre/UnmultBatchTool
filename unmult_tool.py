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
PREVIEW_EMPTY_TEXT = "拖入图片或从左侧列表选择素材"

UI_COLORS = {
    "app_bg": "#eef1f5",
    "header_bg": "#f8fafc",
    "panel_bg": "#f5f7fa",
    "card_bg": "#ffffff",
    "surface": "#f9fbfd",
    "surface_hover": "#f1f5f9",
    "field_bg": "#ffffff",
    "preview_bg": "#f7f9fc",
    "border": "#d6dde7",
    "border_soft": "#e6ebf1",
    "border_strong": "#b8c1cf",
    "text": "#18212f",
    "muted": "#667085",
    "muted_soft": "#8a94a3",
    "accent": "#256fb6",
    "accent_hover": "#1f609f",
    "accent_pressed": "#194f84",
    "accent_soft": "#e8f2ff",
    "accent_text": "#ffffff",
    "selection": "#d8eaff",
    "status_bg": "#ffffff",
    "success": "#2c7a57",
}

UI_FONTS = {
    "base": ("Segoe UI", 10),
    "small": ("Segoe UI", 9),
    "title": ("Segoe UI", 15, "bold"),
    "section": ("Segoe UI", 10, "bold"),
    "button": ("Segoe UI", 10),
}


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
        self.style = ttk.Style(self.root)
        self._configure_style()

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

    def _configure_style(self) -> None:
        colors = UI_COLORS
        fonts = UI_FONTS
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")

        self.root.configure(background=colors["app_bg"])
        self.root.option_add("*Font", fonts["base"])
        self.root.option_add("*Listbox.Font", fonts["small"])
        self.root.option_add("*Listbox.Background", colors["card_bg"])
        self.root.option_add("*Listbox.Foreground", colors["text"])
        self.root.option_add("*Listbox.selectBackground", colors["selection"])
        self.root.option_add("*Listbox.selectForeground", colors["text"])
        self.root.option_add("*Listbox.BorderWidth", 0)
        self.root.option_add("*Listbox.Relief", "flat")

        self.style.configure(".", font=fonts["base"])
        self.style.configure("TFrame", background=colors["app_bg"])
        self.style.configure("Panel.TFrame", background=colors["card_bg"])
        self.style.configure("Card.TFrame", background=colors["card_bg"])
        self.style.configure(
            "TLabel",
            background=colors["app_bg"],
            foreground=colors["text"],
        )
        self.style.configure(
            "Muted.TLabel",
            background=colors["app_bg"],
            foreground=colors["muted"],
            font=fonts["small"],
        )
        self.style.configure(
            "Title.TLabel",
            background=colors["app_bg"],
            foreground=colors["text"],
            font=fonts["title"],
        )
        self.style.configure(
            "TButton",
            background=colors["surface"],
            bordercolor=colors["border"],
            focusthickness=2,
            focuscolor=colors["accent"],
            font=fonts["button"],
            padding=(10, 7),
            relief="flat",
        )
        self.style.map(
            "TButton",
            background=[
                ("pressed", colors["border"]),
                ("active", "#eef2f6"),
            ],
            bordercolor=[("focus", colors["accent"])],
        )
        self.style.configure(
            "Accent.TButton",
            background=colors["accent"],
            foreground=colors["accent_text"],
            bordercolor=colors["accent"],
            font=fonts["button"],
            padding=(12, 8),
        )
        self.style.map(
            "Accent.TButton",
            background=[
                ("pressed", colors["accent_pressed"]),
                ("active", colors["accent_hover"]),
            ],
            foreground=[("disabled", colors["surface"])],
        )
        self.style.configure(
            "TLabelFrame",
            background=colors["panel_bg"],
            bordercolor=colors["border"],
            lightcolor=colors["border"],
            darkcolor=colors["border"],
            relief="solid",
            padding=8,
        )
        self.style.configure(
            "TLabelFrame.Label",
            background=colors["panel_bg"],
            foreground=colors["text"],
            font=fonts["section"],
        )
        self.style.configure(
            "TEntry",
            fieldbackground=colors["field_bg"],
            foreground=colors["text"],
            bordercolor=colors["border"],
            lightcolor=colors["border"],
            darkcolor=colors["border"],
            insertcolor=colors["text"],
            padding=(7, 6),
        )
        self.style.configure(
            "TCombobox",
            fieldbackground=colors["field_bg"],
            background=colors["field_bg"],
            foreground=colors["text"],
            bordercolor=colors["border"],
            arrowcolor=colors["muted"],
            padding=(6, 5),
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", colors["field_bg"])],
            selectbackground=[("readonly", colors["selection"])],
            selectforeground=[("readonly", colors["text"])],
        )
        self.style.configure(
            "TScale",
            background=colors["card_bg"],
            troughcolor="#dde5ee",
            bordercolor=colors["border"],
            lightcolor=colors["border"],
            darkcolor=colors["border"],
        )
        self.style.configure(
            "TCheckbutton",
            background=colors["card_bg"],
            foreground=colors["text"],
            focuscolor=colors["accent"],
        )
        self.style.map(
            "TCheckbutton",
            background=[("active", colors["card_bg"])],
            foreground=[("disabled", colors["muted"])],
        )
        self.style.configure("Header.TFrame", background=colors["header_bg"])
        self.style.configure("Sidebar.TFrame", background=colors["panel_bg"])
        self.style.configure(
            "Preview.TFrame",
            background=colors["preview_bg"],
            bordercolor=colors["border"],
            relief="solid",
        )
        self.style.configure(
            "Preview.TLabel",
            background=colors["preview_bg"],
            foreground=colors["muted"],
            font=fonts["base"],
        )
        self.style.configure(
            "Status.TLabel",
            background=colors["status_bg"],
            foreground=colors["muted"],
            font=fonts["small"],
            padding=(12, 7),
        )

    def _build_ui(self) -> None:
        root = self.root

        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        self._build_header(root)

        content = self.ttk.Frame(root, style="TFrame")
        content.grid(row=1, column=0, sticky="nsew", padx=12, pady=(12, 10))
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        side = self.ttk.Frame(content, style="Sidebar.TFrame", padding=10, width=340)
        side.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        side.grid_propagate(False)
        side.columnconfigure(0, weight=1)
        side.rowconfigure(3, weight=1)
        self.sidebar = side

        self._build_import_section(side, row=0)
        self._build_export_section(side, row=1)
        self._build_settings_section(side, row=2)
        self._build_file_list_section(side, row=3)
        self._build_preview_area(content)
        self._build_status_bar(root)

    def _build_header(self, parent) -> None:
        tk = self.tk
        colors = UI_COLORS
        fonts = UI_FONTS
        header = tk.Frame(
            parent,
            bg=colors["header_bg"],
            highlightthickness=1,
            highlightbackground=colors["border_soft"],
            bd=0,
            padx=16,
            pady=11,
        )
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        self.header = header

        tk.Label(
            header,
            text="Unmult 去黑批处理工具",
            bg=colors["header_bg"],
            fg=colors["text"],
            font=fonts["title"],
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )
        tk.Label(
            header,
            text="批量移除黑底素材，生成透明 PNG",
            bg=colors["header_bg"],
            fg=colors["muted"],
            font=fonts["small"],
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

    def _create_section(self, parent, title: str, row: int, sticky: str = "ew"):
        tk = self.tk
        colors = UI_COLORS
        fonts = UI_FONTS
        section = tk.Frame(
            parent,
            bg=colors["card_bg"],
            highlightthickness=1,
            highlightbackground=colors["border"],
            bd=0,
        )
        section.grid(row=row, column=0, sticky=sticky, pady=(0, 10))
        section.columnconfigure(0, weight=1)

        tk.Label(
            section,
            text=title,
            bg=colors["card_bg"],
            fg=colors["text"],
            font=fonts["section"],
            anchor="w",
            padx=12,
            pady=8,
        ).grid(row=0, column=0, sticky="ew")

        body = tk.Frame(section, bg=colors["card_bg"], padx=12, pady=0)
        body.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        body.columnconfigure(0, weight=1)
        return section, body

    def _create_label(self, parent, text: str, *, muted: bool = False):
        colors = UI_COLORS
        fonts = UI_FONTS
        return self.tk.Label(
            parent,
            text=text,
            bg=colors["card_bg"],
            fg=colors["muted"] if muted else colors["text"],
            font=fonts["small"],
            anchor="w",
        )

    def _button_palette(self, variant: str) -> dict[str, str]:
        colors = UI_COLORS
        if variant == "primary":
            return {
                "bg": colors["accent"],
                "fg": colors["accent_text"],
                "hover": colors["accent_hover"],
                "pressed": colors["accent_pressed"],
                "border": colors["accent"],
            }
        return {
            "bg": colors["surface"],
            "fg": colors["text"],
            "hover": colors["surface_hover"],
            "pressed": colors["border_soft"],
            "border": colors["border"],
        }

    def _create_button(self, parent, text: str, command, *, variant: str = "secondary"):
        tk = self.tk
        colors = UI_COLORS
        palette = self._button_palette(variant)
        height = 40 if variant == "primary" else 38
        radius = 6
        button = tk.Canvas(
            parent,
            height=height,
            bg=colors["card_bg"],
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            takefocus=True,
        )
        state = {"bg": palette["bg"], "border": palette["border"]}

        def rounded_rect(
            x1: int,
            y1: int,
            x2: int,
            y2: int,
            r: int,
            **kwargs,
        ) -> None:
            points = [
                x1 + r,
                y1,
                x2 - r,
                y1,
                x2,
                y1,
                x2,
                y1 + r,
                x2,
                y2 - r,
                x2,
                y2,
                x2 - r,
                y2,
                x1 + r,
                y2,
                x1,
                y2,
                x1,
                y2 - r,
                x1,
                y1 + r,
                x1,
                y1,
            ]
            button.create_polygon(points, smooth=True, splinesteps=12, **kwargs)

        def redraw() -> None:
            width = max(button.winfo_width(), 40)
            button.delete("all")
            border = state["border"]
            if button.focus_get() == button:
                border = colors["accent"]
            rounded_rect(
                1,
                1,
                width - 1,
                height - 1,
                radius,
                fill=state["bg"],
                outline=border,
            )
            button.create_text(
                width / 2,
                height / 2,
                text=text,
                fill=palette["fg"],
                font=UI_FONTS["button"],
            )

        def apply_colors(bg: str) -> None:
            state["bg"] = bg
            redraw()

        def activate(_event=None) -> str:
            apply_colors(palette["hover"])
            command()
            return "break"

        button.bind("<Configure>", lambda _event: redraw())
        button.bind("<Enter>", lambda _event: apply_colors(palette["hover"]))
        button.bind("<Leave>", lambda _event: apply_colors(palette["bg"]))
        button.bind("<ButtonPress-1>", lambda _event: apply_colors(palette["pressed"]))
        button.bind("<ButtonRelease-1>", activate)
        button.bind("<FocusIn>", lambda _event: redraw())
        button.bind("<FocusOut>", lambda _event: redraw())
        button.bind("<Return>", activate)
        button.bind("<space>", activate)
        redraw()
        return button

    def _build_import_section(self, parent, row: int) -> None:
        ttk = self.ttk
        self.import_section, body = self._create_section(parent, "导入素材", row)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, weight=1)

        self._create_button(body, "添加图片", self.add_files).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 4),
        )
        self._create_button(body, "添加文件夹", self.add_folder).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=4,
        )
        self._create_button(body, "清空", self.clear_files).grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(4, 0),
        )
        ttk.Checkbutton(
            body,
            text="递归读取子文件夹",
            variable=self.recursive,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))

    def _build_export_section(self, parent, row: int) -> None:
        ttk = self.ttk
        self.export_section, body = self._create_section(parent, "批量导出", row)
        body.columnconfigure(0, weight=1)

        ttk.Entry(body, textvariable=self.output_dir).grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 7),
        )
        self._create_button(body, "选择输出目录", self.pick_output_dir).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 9),
        )
        self._create_label(body, "文件后缀", muted=True).grid(
            row=2,
            column=0,
            sticky="w",
        )
        ttk.Entry(body, textvariable=self.suffix).grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(4, 7),
        )
        ttk.Checkbutton(
            body,
            text="覆盖同名 PNG",
            variable=self.overwrite,
        ).grid(row=4, column=0, sticky="w", pady=(0, 8))
        self._create_button(
            body,
            "开始批量处理",
            self.start_batch,
            variant="primary",
        ).grid(row=5, column=0, sticky="ew")

    def _build_settings_section(self, parent, row: int) -> None:
        ttk = self.ttk
        self.settings_section, body = self._create_section(parent, "去黑参数", row)
        body.columnconfigure(1, weight=1)

        self._add_slider(body, "黑场", self.black_point, 0, 240, 0)
        self._add_slider(body, "白场", self.white_point, 16, 255, 1)
        self._add_slider(
            body,
            "Alpha Gamma",
            self.gamma,
            0.25,
            3,
            2,
        )

        self._create_label(body, "亮度算法").grid(
            row=3,
            column=0,
            sticky="w",
            pady=4,
        )
        mode_box = ttk.Combobox(
            body,
            textvariable=self.mode,
            state="readonly",
            values=("max", "luma", "average"),
            width=12,
        )
        mode_box.grid(row=3, column=1, sticky="ew", pady=4)
        mode_box.bind("<<ComboboxSelected>>", lambda _event: self.schedule_preview_update())

        self._create_label(body, "预览底色").grid(
            row=4,
            column=0,
            sticky="w",
            pady=4,
        )
        bg_box = ttk.Combobox(
            body,
            textvariable=self.preview_bg,
            state="readonly",
            values=("checker", "black", "white"),
            width=12,
        )
        bg_box.grid(row=4, column=1, sticky="ew", pady=4)
        bg_box.bind("<<ComboboxSelected>>", lambda _event: self.schedule_preview_update())

        ttk.Checkbutton(
            body,
            text="输出保持预乘 RGB",
            variable=self.premultiplied_output,
            command=self.schedule_preview_update,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def _build_file_list_section(self, parent, row: int) -> None:
        tk = self.tk
        ttk = self.ttk
        colors = UI_COLORS
        self.file_list_section, body = self._create_section(
            parent,
            "图片列表",
            row,
            sticky="nsew",
        )
        self.file_list_section.rowconfigure(1, weight=1)
        self.file_list_section.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        self.file_list = tk.Listbox(
            body,
            width=34,
            height=7,
            bg=colors["surface"],
            fg=colors["text"],
            selectbackground=colors["selection"],
            selectforeground=colors["text"],
            activestyle="none",
            highlightthickness=1,
            highlightcolor=colors["accent"],
            highlightbackground=colors["border_soft"],
            relief="flat",
            borderwidth=0,
        )
        list_scrollbar = ttk.Scrollbar(body, orient="vertical")
        self.file_list.configure(yscrollcommand=list_scrollbar.set)
        list_scrollbar.configure(command=self.file_list.yview)
        self.file_list.grid(row=0, column=0, sticky="nsew")
        list_scrollbar.grid(row=0, column=1, sticky="ns", padx=(6, 0))
        self.file_list.bind(
            "<<ListboxSelect>>",
            lambda _event: self.load_selected_preview(),
        )

    def _build_preview_area(self, parent) -> None:
        tk = self.tk
        colors = UI_COLORS
        fonts = UI_FONTS
        main = tk.Frame(
            parent,
            bg=colors["preview_bg"],
            highlightthickness=1,
            highlightbackground=colors["border"],
            bd=0,
            padx=14,
            pady=14,
        )
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)
        self.preview_frame = main

        self.preview_label = tk.Label(
            main,
            text=PREVIEW_EMPTY_TEXT,
            anchor="center",
            bg=colors["preview_bg"],
            fg=colors["muted"],
            font=fonts["base"],
            relief="flat",
            bd=0,
        )
        self.preview_label.grid(row=0, column=0, sticky="nsew")
        self.preview_label.bind(
            "<Configure>",
            lambda _event: self.schedule_preview_update(delay=180),
        )

    def _build_status_bar(self, parent) -> None:
        self.status_bar = self.tk.Label(
            parent,
            textvariable=self.status,
            anchor="w",
            bg=UI_COLORS["status_bg"],
            fg=UI_COLORS["muted"],
            font=UI_FONTS["small"],
            highlightthickness=1,
            highlightbackground=UI_COLORS["border_soft"],
            bd=0,
            padx=12,
            pady=7,
        )
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))

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
        colors = UI_COLORS
        is_integer = variable.__class__.__name__ == "IntVar"

        self._create_label(parent, label).grid(row=row, column=0, sticky="w", pady=4)
        slider = tk.Scale(
            parent,
            from_=low,
            to=high,
            variable=variable,
            orient=tk.HORIZONTAL,
            showvalue=False,
            resolution=1 if is_integer else 0.01,
            bg=colors["card_bg"],
            activebackground=colors["accent"],
            troughcolor="#dfe7f0",
            highlightthickness=0,
            bd=0,
            relief="flat",
            sliderrelief="flat",
            width=9,
            sliderlength=16,
            command=lambda _value: self.schedule_preview_update(),
        )
        slider.grid(row=row, column=1, sticky="ew", pady=4)

        value_text = tk.StringVar()
        value_entry = ttk.Entry(
            parent,
            width=7,
            textvariable=value_text,
            justify="right",
        )
        value_entry.grid(row=row, column=2, sticky="e", padx=(8, 0), pady=4)

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
        self.preview_photo = None
        self.preview_label.configure(image="", text=PREVIEW_EMPTY_TEXT)
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
            self.preview_label.configure(image=self.preview_photo, text="")
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
