## Current Snapshot

Last Updated: 2026-06-03

Project: UnmultBatchTool
Phase: Batch safety and handoff cleanup

Current state:
- Reconstructed editable Python source from the original PyInstaller executable.
- Added source launcher, dependency file, README updates, and focused unittest coverage.
- Added first interaction fixes: optional drag-and-drop via `tkinterdnd2`, debounced preview updates, preview downsampling, and a more usable export panel placement.
- Restyled the source UI as a professional light Tkinter tool: centralized style tokens, header/content/status layout, left workflow sidebar, right preview surface, accent primary export button, clearer list and preview empty states.
- Applied user feedback that the first restyle still looked too close to old system controls: replaced `ttk.LabelFrame` sidebar groups with flat white card sections, moved key labels/buttons to custom light surfaces, and replaced default buttons with Canvas-drawn rounded buttons.
- Applied the user's marked reference layout: removed the large in-window title, added a top action toolbar, kept upload/list/settings on the left, moved preview background controls to the preview header, and moved export settings below the preview so the default window shows the full export workflow.
- Applied user feedback that the adjustment sliders were too low-contrast: replaced the left settings `tk.Scale` controls with custom Canvas sliders using visible blue fill, clear gray tracks, and white handles with blue outlines.
- Added a right-side preview "对比" button: pressing or holding it shows the original image, and releasing it restores the processed preview.
- Added batch safety fixes: duplicate batch launches are ignored while processing, and individual failed images no longer stop the rest of the GUI batch.
- Added output path safety: overwrite mode can replace old output files, but it now avoids overwriting any current batch input and keeps same-stem batch outputs unique with numbered fallbacks.
- Tightened preview state handling: failed image preview loads now clear stale preview content, and file-list refresh preserves the current selection when that file remains in the list.
- Updated README and `.gitignore` to match the source UI state, mark the old exe as not ready for distribution, document supported input formats, and ignore common export/build artifacts.

Verification evidence:
- Stage 1 style foundation: `python -m unittest tests.test_unmult_tool`, `python -m py_compile unmult_tool.py`, and GUI smoke passed.
- Stage 2 layout restyle: `python -m unittest tests.test_unmult_tool`, `python -m py_compile unmult_tool.py`, and GUI smoke passed.
- Stage 3 detail polish: `python -m unittest tests.test_unmult_tool`, `python -m py_compile unmult_tool.py`, and GUI smoke passed.
- UI polish correction: `python -m unittest tests.test_unmult_tool`, `python -m py_compile unmult_tool.py`, GUI smoke, and local screenshot review passed.
- Red-box layout correction: `python -m unittest tests.test_unmult_tool`, `python -m py_compile unmult_tool.py`, GUI smoke, and default-window screenshot review passed.
- Slider visibility polish: `python -m unittest tests.test_unmult_tool`, `python -m py_compile unmult_tool.py`, GUI smoke, and screenshot review passed.
- Hold-to-compare interaction: `python -m unittest tests.test_unmult_tool`, `python -m py_compile unmult_tool.py`, GUI smoke, and screenshot review passed.
- Batch duplicate-launch guard: `python -m unittest tests.test_unmult_tool`, `python -m py_compile unmult_tool.py`, and GUI smoke passed.
- Batch per-file failure continuation: `python -m unittest tests.test_unmult_tool`, `python -m py_compile unmult_tool.py`, and GUI smoke passed.
- Documentation and ignore cleanup: `python -m unittest tests.test_unmult_tool`, `python -m py_compile unmult_tool.py`, GUI smoke, and `git diff --check` passed.
- Output path safety: `python -m unittest tests.test_unmult_tool` ran 14 tests and passed; `python -m py_compile unmult_tool.py` passed; GUI smoke confirmed `UnmultApp` initializes, drag/drop token is present, compare button exists, and `is_processing` starts false.
- Preview state cleanup: `python -m unittest tests.test_unmult_tool` ran 16 tests and passed; `python -m py_compile unmult_tool.py` passed; GUI smoke confirmed empty preview text renders on initialization.

Dirty state:
- Work is on branch `codex/ui-restyle`.
- UI restyle and safety work has multiple phase checkpoints on `codex/ui-restyle`, including batch safety and documentation cleanup.
- Next action is user visual review of the updated source UI.

Known risks:
- `UnmultBatchTool.exe` is the old binary and has not been rebuilt from the reconstructed source.
- DDS support is intentionally deferred and is not in the current supported input list.
- Preview processing can still be heavy for large images because unmult preview computation runs in the Tk main thread.
- Full visual/manual review by the user is still needed because automated checks cannot judge final polish.
