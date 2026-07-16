# CASPER TUI Autonomous Feature Manifest

**Batch:** 1 of N
**Scope:** `core/terminal/ui` and the live `TerminalIntegration` path
**Evidence rule:** A feature is complete only when its named automated test passes.

| # | Feature | Command / Surface | Verification |
|---|---|---|---|
| 1 | Non-blocking TUI lifecycle | `TerminalUI.start_ui()` returns after scheduling its render loop | `test_non_blocking_lifecycle` |
| 2 | Terminal capability detection | Dynamic width, TTY detection, `NO_COLOR` support | `test_terminal_capability_detection` |
| 3 | Theme selection | `/theme auto|dark|light|mono` | `test_theme_selection` |
| 4 | Persistent preferences | Atomic `settings.json` under the TUI state root | `test_preferences_persist` |
| 5 | Persistent command history | `history.txt`, bounded and de-duplicated | `test_history_persistence` |
| 6 | History search | `/history [query]` | `test_history_search` |
| 7 | Undo/redo pane state | `/undo [pane]`, `/redo [pane]` | `test_undo_redo` |
| 8 | Layout presets | `/layout default|compact|focus-code|focus-tests` | `test_layout_presets` |
| 9 | Pane controls | `/pane NAME show|hide|toggle|height N` | `test_pane_controls` |
| 10 | Autosave and crash recovery | Atomic `recovery.json`, `/recover` | `test_autosave_recovery` |
| 11 | Global output search | `/search QUERY` | `test_global_search` |
| 12 | Command palette | `/commands [query]` | `test_command_palette` |
| 13 | Status notifications | `/notify MESSAGE` and footer status | `test_notifications` |
| 14 | Named sessions | `/session save|load|list NAME` | `test_named_sessions` |
| 15 | Transcript export | `/export text|markdown|json [PATH]` | `test_transcript_export` |
| 16 | Transcript import | `/import PATH` | `test_transcript_import` |
| 17 | Bookmarks | `/bookmark add|list|show NAME` | `test_bookmarks` |
| 18 | Macro recording/replay | `/macro start|stop|play|list NAME` | `test_macros` |
| 19 | Shortcut customization | `/shortcut set|list ACTION KEYS` | `test_shortcut_customization` |
| 20 | Accessibility profiles | `/accessibility standard|high-contrast|plain|reduced-motion` | `test_accessibility_profiles` |

## Next candidates

- Multiple concurrent terminal sessions
- Plugin-provided panes and commands
- Fuzzy file picker
- Mouse-aware pane resizing
- Shell completion generation
- Encrypted cloud backup
- Collaborative shared sessions
- OSC 8 links and OSC 52 clipboard integration with explicit trust controls

## Research basis

- Rich console capability detection and `NO_COLOR` behavior
- prompt-toolkit history, completion, and autosuggestion patterns
- XDG separation of configuration and persistent application state
- Keyboard-first and non-color-only accessibility expectations
