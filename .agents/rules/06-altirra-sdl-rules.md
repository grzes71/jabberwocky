---
trigger: always_on
---

# AltirraSDL Emulation & Verification Rules

## 1. Emulator Policy
- **Proactive verification:** whenever you build or modify `jabberwocky.xex`, verify it runs. Use **AltirraSDL** for scripted/automated checks and `make run` (Altirra 4.40, `C:/Apps/Altirra-4.40/Altirra64.exe`) for a quick manual look.
- **AltirraSDL binary:**
  `C:\Users\grzes\Documents\Projects\AltirraSDL\build\windows-sdl-release\src\AltirraSDL\Release\AltirraSDL.exe`
- **Protocol/SDK reference:** the `altirra-bridge` skill (`.agents/skills/altirra-bridge/SKILL.md`) is the single source of truth for the bridge API, commands and payload shapes. Never guess commands; read the skill or the SDK instead of duplicating them here.

## 2. Interactive Run (visual verification)
```powershell
Start-Process -FilePath "C:\Users\grzes\Documents\Projects\AltirraSDL\build\windows-sdl-release\src\AltirraSDL\Release\AltirraSDL.exe" -ArgumentList "jabberwocky.xex"
```
Launch asynchronously so the shell is never blocked.

## 3. Automated / E2E Testing (AltirraBridge)
1. Start the emulator with the bridge enabled (`AltirraBridgeServer` is the headless alternative, same protocol):
   ```powershell
   Start-Process -FilePath "C:\Users\grzes\Documents\Projects\AltirraSDL\build\windows-sdl-release\src\AltirraSDL\Release\AltirraSDL.exe" -ArgumentList "--bridge"
   ```
2. Read the token file the server writes to `$env:LOCALAPPDATA\Temp\altirra-bridge-*.token` (line 1 = address, line 2 = session token).
3. Make the SDK importable — the `altirra_bridge` package is **not** installed in `.venv`:
   ```powershell
   $env:PYTHONPATH = "C:\Users\grzes\Documents\Projects\AltirraSDL\src\AltirraSDL\AltirraBridge\sdk\python"
   ```
4. Drive the emulator (all methods verified against `altirra_bridge/client.py`):
   ```python
   from altirra_bridge import AltirraBridge

   token_path = r"%LOCALAPPDATA%\Temp\altirra-bridge-XXXX.token"  # path printed by the server

   with AltirraBridge.from_token_file(token_path) as atari:
       atari.boot("jabberwocky.xex")   # load and start the XEX
       atari.frame(120)                # advance deterministic frames
       regs = atari.regs()             # CPU register snapshot
       mem = atari.peek(0x0800, 32)    # raw memory read
       img = atari.screenshot()        # framebuffer capture
       atari.joy(0, "right", fire=True)
       atari.key("SPACE")
   ```

## 4. Failure Triage
- Black screen / no boot: re-check `make xex`, the `INITAD`/`RUNAD` vectors and `docs/memory_map.txt` before suspecting the emulator.
- A crash that reproduces only in AltirraSDL (not in a py65 harness) usually means ANTIC/GTIA/POKEY interaction — reproduce under `--bridge` and attach `regs()`, `peek()` and a screenshot as evidence.
