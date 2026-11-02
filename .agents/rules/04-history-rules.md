---
trigger: always_on
---

## Definition of Done (CRITICAL)

- **History tracking:** whenever you successfully implement a feature, fix a bug, or complete a significant refactor, you MUST update `HISTORY.md`.
- **Placement:** insert the new entry directly below the HTML comment `<!-- AGENT INSTRUCTIONS... -->`, above the previous newest entry. Never append at the bottom, never replace, reorder or delete existing entries.
- **Format:** `## [YYYY-MM-DD] - [Brief Title]`, followed by grouped bullet lists (`- **Obszar**:`) naming concrete technical changes (files, routines, symbols, addresses).
- **Language:** write the entry in **Polish**, matching every existing entry in `HISTORY.md`. Paths, symbols and command names stay in English.
- **Verification line:** close the entry with a `- **Weryfikacja**:` group reporting what actually ran, e.g. ``- `make all`: pomyślna asemblacja `jabberwocky.xex` i walidacja mapy pamięci.`` and ``- `pytest`: N testów zakończonych sukcesem.`` Never invent results; if something failed, say so.
- **Paths in History:** ALWAYS use paths relative to the project root (e.g. `scenes/game.asm` or `[scenes/game.asm](scenes/game.asm)`). NEVER absolute paths or `file:///` URIs.
- **Trigger:** perform this update as the final step before telling the user the task is complete — the `done` skill automates exactly this procedure.
