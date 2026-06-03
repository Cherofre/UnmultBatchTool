## Now

1. Let the user verify the GitHub release: `https://github.com/Cherofre/UnmultBatchTool/releases/tag/v1.0.0`.
2. Let the user download and run `UnmultBatchTool.exe` from the release asset.
3. Ask the user to re-check file-list clicking, `G:\SU_Master\asset\client\gfx\texture\0mmf\111.png`, and the About-window "检查更新" button in the packaged exe.
4. If more packaging polish is needed, plan it as a follow-up release.

## Handoff Notes

Start here: `unmult_tool.py`, especially `UnmultApp._build_ui`.

Do not redo:
- Source reconstruction from `UnmultBatchTool.exe`.
- Drag-and-drop support wiring.
- Preview debouncing/downsampling fix.
- Professional light UI style foundation and main layout restyle on branch `codex/ui-restyle`.
- User-feedback polish replacing old `LabelFrame` groups and default buttons with flat card sections and Canvas rounded buttons.
- Red-box layout correction removing the big title header and moving export/settings around the preview.
- Slider visibility polish replacing low-contrast system scales with custom Canvas sliders.
- Hold-to-compare preview button that shows the original image while pressed and restores the processed preview on release.
- Batch safety fixes for duplicate launch prevention and per-file failure continuation.
- Output path safety preventing overwrite mode from replacing current batch inputs or same-stem batch outputs.
- Preview state cleanup for failed preview loads and file-list selection preservation during refresh.
- Processed-preview caching for compare restore, plus Enter-key compare and slider focus polish.
- Subagent review fixes for numbered output fallback files and removed-list-selection preview clearing.
- 16-bit grayscale PNG handling and lighter scheduled preview generation for file-list clicks.
- About-window update check and public GitHub source release `v1.0.0`.
- Fresh PyInstaller `UnmultBatchTool.exe` uploaded to `v1.0.0`; old tracked exe removed from git and remote branch.
- README/.gitignore cleanup for source-only delivery and generated artifacts.

Verify next:
- Run `python -m unittest tests.test_unmult_tool`.
- Run `python -m py_compile unmult_tool.py`.
- Run a GUI smoke check after UI changes.
- Current final verification already passed with 21 unit tests, py_compile, GUI smoke, CLI smoke, and read-only subagent review.
- Latest verification passed with 25 unit tests, py_compile, GUI smoke, and real-file smoke for `111.png`.
- Release verification passed with `gh release view v1.0.0` and runtime `check_update_status()`.
- Packaged exe verification passed with CLI PNG smoke and GUI startup smoke.
- DDS is intentionally deferred; do not add it unless the user asks to resume that work.

Do not claim:
- UI restyle is accepted by the user, until they visually review the source UI.
