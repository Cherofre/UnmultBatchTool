## Active Decisions

### 2026-06-02: Use phased local git checkpoints

Status: active

Decision: Treat this as an active build project and commit stable phases locally.

Reason: The tool is being reconstructed and redesigned incrementally; local checkpoints make it easy to roll back.

### 2026-06-02: Keep `AGENTS.md` untouched

Status: active

Decision: Do not create or edit `AGENTS.md` unless the user explicitly asks.

Reason: Project instructions say not to edit `AGENTS.md` again.

### 2026-06-02: Rebuild UI in Tkinter for now

Status: active

Decision: Keep the desktop UI in Tkinter during the next restyle unless the user chooses a larger rewrite.

Reason: Existing source is a compact Tkinter app; staying in Tkinter keeps packaging and iteration simple.

### 2026-06-02: Professional light UI restyle scope

Status: active

Decision: Restyle the source UI with a professional light tool-panel look, without adding new workflow features or rebuilding the exe in this phase.

Reason: The user chose appearance/layout first, pure Tkinter, and source-only delivery for this phase.

### 2026-06-02: Use custom Canvas buttons for polish

Status: active

Decision: Use Canvas-drawn rounded buttons for the main source UI instead of standard `ttk.Button` widgets.

Reason: The user feedback showed the first restyle still looked too close to old Windows controls; Canvas buttons give more control over flat backgrounds, borders, hover states, and the primary action style while staying in pure Tkinter.

### 2026-06-02: Follow red-box reference layout

Status: active

Decision: Use a toolbar-first layout without a large in-window title; keep upload, file list, and adjustment parameters on the left; place preview controls above the preview and export settings below it.

Reason: The user clarified that the generated/reference UI placed key controls around the preview, and the prior left-column-only layout clipped lower controls in the default window.

### 2026-06-03: Use custom Canvas sliders for visibility

Status: active

Decision: Use Canvas-drawn sliders for black point, white point, and Gamma instead of standard `tk.Scale`.

Reason: On Windows the default `tk.Scale` slider handle was too low-contrast against the light panel, making the adjustment controls hard to read.

### 2026-06-03: Original preview compare is momentary

Status: active

Decision: The preview "对比" control is a momentary hold interaction: press shows the original image and release restores the processed preview.

Reason: The user asked for clicking or holding to view the original, with release cancelling the comparison.

### 2026-06-03: Defer DDS support

Status: active

Decision: Keep DDS out of the supported input list for now.

Reason: DDS support depends on the specific compression/container variant, so the user chose to postpone it and work on other safety issues first.

### 2026-06-03: Protect current batch inputs during overwrite export

Status: active

Decision: In overwrite mode, allow replacing old output PNG files but never write to a path that matches any current batch input; use numbered fallback names for same-stem collisions.

Reason: The overwrite checkbox should not risk destroying source artwork or silently replacing another item from the same batch.

### 2026-06-03: Scale 16-bit grayscale PNGs by bit depth

Status: active

Decision: Convert `I;16` grayscale PNGs to 8-bit RGBA by dividing channel values by 256 before previewing or unmult processing.

Reason: Direct Pillow conversion clips most 16-bit values to white; bit-depth scaling preserves predictable texture values without introducing auto-contrast.

### 2026-06-03: Keep source-only delivery until packaging stage

Status: active

Decision: Treat the current UI and behavior changes as source-only until a fresh exe is built.

Reason: The existing `UnmultBatchTool.exe` is an old binary and does not contain the reconstructed source changes.
