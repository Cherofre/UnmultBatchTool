## Now

1. Commit the current checkpoint.
2. Agree on the UI style direction for the whole desktop tool.
3. Write a small UI restyle plan before implementation.
4. Implement the UI restyle in stages with git commits at stable checkpoints.
5. Verify each stage with unit tests, syntax check, GUI smoke check, and any practical manual UI check.

## Handoff Notes

Start here: `unmult_tool.py`, especially `UnmultApp._build_ui`.

Do not redo:
- Source reconstruction from `UnmultBatchTool.exe`.
- Drag-and-drop support wiring.
- Preview debouncing/downsampling fix.

Verify next:
- Run `python -m unittest tests.test_unmult_tool`.
- Run `python -m py_compile unmult_tool.py`.
- Run a GUI smoke check after UI changes.

Do not claim:
- The exe is updated, until a fresh package is built.
- UI restyle is complete, until the user approves the design and verifies the new look.
