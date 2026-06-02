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
