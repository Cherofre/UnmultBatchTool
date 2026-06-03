## Current Snapshot

Last Updated: 2026-06-03

Project: UnmultBatchTool
Phase: 1.0.0 executable release published

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
- Added processed-preview caching and keyboard polish: restoring from compare no longer recomputes the same preview, Enter now behaves like a momentary compare key, and clicking a custom slider focuses it for arrow-key nudging.
- Closed subagent review findings: numbered fallback output paths now avoid existing files, and list refresh clears preview if the previously selected file was removed.
- Fixed 16-bit grayscale PNG handling: `I;16` images are scaled down to 8-bit before RGBA conversion so files like `G:\SU_Master\asset\client\gfx\texture\0mmf\111.png` do not preview/process as a white image.
- Reduced file-list selection lag: list selection now schedules preview processing instead of running it inside the click callback, and default preview size is capped at 512px for lighter main-thread preview work.
- Added source version `1.0.0` and a "检查更新" action in the About window, backed by GitHub Releases version checks.
- Published public GitHub repository `Cherofre/UnmultBatchTool` and release `v1.0.0`.
- Removed the old tracked `UnmultBatchTool.exe` from git and the remote branch, and ignored root-level exe artifacts to avoid re-committing binaries.
- Packaged a fresh Windows `UnmultBatchTool.exe` with PyInstaller and uploaded it as the `v1.0.0` release asset.
- Updated README and `.gitignore` to match the release state, document supported input formats, and ignore common export/build artifacts.

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
- Preview cache and keyboard polish: `python -m unittest tests.test_unmult_tool` ran 19 tests and passed; `python -m py_compile unmult_tool.py` passed; GUI smoke confirmed `UnmultApp` initializes with drag/drop token, compare button, and 3 custom sliders.
- Subagent review fixes: `python -m unittest tests.test_unmult_tool` ran 21 tests and passed; `python -m py_compile unmult_tool.py` passed; GUI smoke confirmed `UnmultApp` initializes with drag/drop token, compare button, and preview position `0 / 0`.
- Final local verification: `python -m unittest tests.test_unmult_tool` ran 21 tests and passed; `python -m py_compile unmult_tool.py` passed; GUI smoke confirmed drag/drop token, compare button, 3 custom sliders, preview position `0 / 0`, and `is_processing` false; CLI smoke processed 1 generated PNG.
- Final subagent review: read-only review found no Critical or Important blockers, and independently ran `python -B -m unittest -v tests.test_unmult_tool` with 21 tests passing plus Space compare and output fallback spot checks.
- 16-bit PNG fix: `python -m unittest tests.test_unmult_tool` ran 23 tests and passed; `python -m py_compile unmult_tool.py` passed; real-file smoke on `111.png` showed preview extrema `(4, 255)` and processed alpha extrema `(4, 255)`.
- File-list lag fix: `python -m unittest tests.test_unmult_tool` ran 25 tests and passed; `python -m py_compile unmult_tool.py` passed; GUI smoke confirmed preview max edge 512; real-file GUI selection smoke on `111.png` took about 0.17s and scheduled preview generation.
- About update check: `python -m unittest tests.test_unmult_tool` ran 30 tests and passed; `python -m py_compile unmult_tool.py` passed; GUI smoke confirmed the About window shows version `1.0.0`, exposes the update button, and reports `已是最新版本` for tag `v1.0.0`.
- Release verification: `gh release view v1.0.0 --repo Cherofre/UnmultBatchTool` returned non-draft, non-prerelease release URL `https://github.com/Cherofre/UnmultBatchTool/releases/tag/v1.0.0`; runtime `check_update_status()` returned `已是最新版本` for `v1.0.0`.
- Old exe removal: `python -m unittest tests.test_unmult_tool` ran 30 tests and passed; `python -m py_compile unmult_tool.py` passed; commit `9446c78` deleted tracked `UnmultBatchTool.exe` and was pushed to `origin/master`.
- PyInstaller package: `python -m PyInstaller --noconfirm --clean --onefile --windowed --name UnmultBatchTool --hidden-import tkinterdnd2 --collect-all tkinterdnd2 unmult_tool.py` produced `dist\UnmultBatchTool.exe` size 17,977,341 bytes.
- Executable smoke: windowed exe CLI processing via `Start-Process -Wait` exited 0 and wrote PNG output; GUI startup smoke kept the process running after launch and then closed it.
- Release asset verification: `gh release view v1.0.0 --repo Cherofre/UnmultBatchTool` shows asset `UnmultBatchTool.exe`, size 17,977,341 bytes, SHA-256 digest `d83f6fe46eae08858b30cfc596e6553fc4072d5621f3dc85aaee736d38d88021`.

Dirty state:
- Work is now on branch `master`, tracking `origin/master`.
- Release tag `v1.0.0` points at commit `9446c78`, after the old tracked exe was removed.

Known risks:
- DDS support is intentionally deferred and is not in the current supported input list.
- Preview processing can still be heavy for large images because unmult preview computation runs in the Tk main thread.
- Full visual/manual review by the user is still needed because automated checks cannot judge final polish.
