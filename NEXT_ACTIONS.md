## Now

1. Let the user run the source UI with `python .\unmult_tool.py --gui` or `launch_unmult_tool.bat`.
2. Collect visual feedback on the red-box layout, custom sliders, and the new hold-to-compare original preview button.
3. If the style is accepted, plan a separate packaging stage to rebuild `UnmultBatchTool.exe`.

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

Verify next:
- Run `python -m unittest tests.test_unmult_tool`.
- Run `python -m py_compile unmult_tool.py`.
- Run a GUI smoke check after UI changes.
- For packaging, first create a new plan; do not assume the current old exe is updated.

Do not claim:
- The exe is updated, until a fresh package is built.
- UI restyle is accepted by the user, until they visually review the source UI.
