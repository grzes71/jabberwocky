---
name: py65
description: >-
  Use for py65 (6502 emulator in Python) work: writing pytest harnesses that
  load the MADS-built .xex into emulated memory, run 6502 subroutines via
  mpu.step(), poke/peek memory, parse .lab symbols, observe memory I/O, and
  compare 6502 results with Python models.
---

# py65 — 6502 emulator for tests

Repo: https://github.com/mnaberez/py65 · `pip install py65` (declare in `requirements.txt`).
Emulates MOS 6502 (also `py65.devices.mpu65c02`, `mpu65org16`). **CPU + flat RAM only** — no ANTIC/GTIA/POKEY/PIA, no OS ROM. Hardware registers are just RAM cells, and nothing generates interrupts; the MPU does implement the entry sequences, though: `mpu.irq()` and `mpu.nmi()` push the return address + status and vector through `$FFFE`/`$FFFA` (+7 cycles).

## Core API

```python
from py65.devices.mpu6502 import MPU
mem = bytearray(65536)            # any indexable of 64K ints works
mpu = MPU(memory=mem)             # NOTE: pass memory=; default is a plain list
mpu.memory[0x80] = 5              # peek/poke (mpu.memory is the object you passed)
mpu.pc = 0x2000                   # registers: pc, a, x, y, sp, p
mpu.step()                        # execute ONE instruction
mpu.processorCycles               # cumulative cycle count (reset() zeroes it)
mpu.reset()                       # sp=$FF, a=x=y=0, p=BREAK|UNUSED, processorCycles=0
mpu.stPush(b) / mpu.stPushWord(w) # stack helpers (stack at $0100-$01FF)
mpu.stPop() / mpu.stPopWord()
mpu.p & mpu.CARRY                 # flags: NEGATIVE OVERFLOW UNUSED BREAK DECIMAL INTERRUPT ZERO CARRY
mpu.irq() / mpu.nmi()             # run the IRQ/NMI entry sequence manually
```

- The constructor is `MPU(memory=None, pc=0x0000)`: `memory=` must be passed explicitly for a caller-owned buffer, and `reset()` sets `pc` from that `pc` argument — the default 0 is *not* the reset vector. Pass `pc=None` to make `reset()` read `$FFFC/$FFFD`.
- Unknown/illegal opcodes are emulated as 2-byte no-ops (`inst_not_implemented` advances `pc` by 1 on top of `step()`'s own increment, 0 cycles) — no exception, so bad jumps run silently and mis-aligned stepping never stops. Always use a step limit.
- `BRK` pushes state and jumps via `$FFFE`; with zeroed vectors it runs into `$0000`. Don't rely on it as a stop — use the return-address trick below.
- `mpu.sp` is 8-bit offset; `mpu.pc`, `a`, `x`, `y` are masked on assignment by the instruction logic only — keep values in range yourself (0–255 / 0–65535).
- Decimal mode (`SED`) is implemented (NMOS semantics). Always `CLD` in test setup if unsure.

## Project harness pattern (see `tests/test_flame_collision.py`, `tests/test_status_bar.py`)

1. `make all` first: tests need `jabberwocky.xex` and `gen/jabberwocky.lab` (assert existence in fixtures with "run make all" message).
2. `parse_labels(lab)` — regex `^[0-9a-fA-F]{2}\t([0-9a-fA-F]{4})\t(name)`; **upper-case keys** (`labels["DRAW_BOTTOM_STATUS"]`).
3. `load_xex(path, mem)` — parse DOS segments: optional `FF FF` header, each segment `start_lo start_hi end_lo end_hi data…`; `FF FF` may repeat between segments; `length = end-start+1`. Nothing is executed: an INIT/RUNAD segment (`$02E2`/`$02E0`) is only written to memory, so call the init routine yourself via `run_subroutine`.
4. Fresh `mem = bytearray(65536)` per test (fixture) — never share state between tests.
5. Set inputs (`mpu.memory[labels["X"]] = v`), call routine, assert outputs against the Python model.

### Calling a subroutine (JSR-equivalent)

```python
def run_subroutine(mpu, addr, max_steps=100_000):
    mpu.sp = 0xFD
    mpu.stPushWord(0x0100 - 1)    # RTS pulls addr, then +1 → $0100
    mpu.memory[0x0100] = 0x00     # BRK sentinel (never executed)
    mpu.pc = addr
    steps = 0
    while mpu.pc != 0x0100 and steps < max_steps:
        mpu.step(); steps += 1
    assert mpu.pc == 0x0100, f"no return in {max_steps} steps (PC={mpu.pc:#06x})"
```

- Pushing `RET-1` is mandatory (RTS adds 1). Sentinel `$0100` lives in stack page but sp=$FD keeps it unused — fine for shallow tests; the routine must not push beyond ~250 bytes.
- Set registers before running: `mpu.a = 3; mpu.x = 0; mpu.y = 7`. Read results after: `mpu.a`, `mpu.p & mpu.ZERO`.
- 16-bit values: `mpu.memory[a] | (mpu.memory[a+1] << 8)` — the project's tests inline this everywhere; add a `peek16` helper only if a test file needs it repeatedly.
- Measure cost: `c0 = mpu.processorCycles; run…; cycles = mpu.processorCycles - c0` (verifies cycle-count comments in time-critical code).

## Intercepting hardware / OS (project caveats)

- No hardware is simulated: poll loops on `VCOUNT`/`RTCLOK`/`WSYNC`/`CONSOL` hang. Pre-seed the RAM cell (e.g. `mem[RTCLOK+2] = n`) or patch the loop, or stub the routine by writing `RTS` (`$60`) at its label: `mpu.memory[labels["WAIT_VBL"]] = 0x60`.
- Simulate frame ticks / collisions by writing registers directly (`M0PF`, `P0PL` etc.) before the call; hardware-clear-on-read behaviour (`HITCLR`) must be modelled in Python.
- Interrupt handlers (VBI/DLI) are tested as plain subroutines but end in `RTI` (`$40`) not `RTS` — push the return PC first and the status byte last (RTI pops P first), and note that a handler entered this way gets its own `$00` status:
  ```python
  mpu.stPushWord(0x0100); mpu.stPush(0x00)   # PC first, then P (RTI pops P first)
  ```
  Alternatively call `mpu.irq()`/`mpu.nmi()` after pointing `$FFFE`/`$FFFA` at the handler: py65 then pushes PC and P exactly like the hardware.
- Programs that loop forever (`jmp *`, main loop): run `N` steps/frames and then inspect state, or stop when `pc == labels["MAIN_LOOP"]`.
- py65 has no OS, so every OS/zero-page location your routine reads must be seeded by the test; keep your own scratch in `$80–$FF` (the FP/BASIC area `$D4–$FF` and the rest of `$00–$7F` are not initialised the way the Atari OS would).

## Observers & tracing (optional)

```python
from py65.memory import ObservableMemory
om = ObservableMemory()                        # subject=… optional underlying memory
om.subscribe_to_write(range(0xD000, 0xD100), lambda addr, val: log.append((addr, val)))
om.subscribe_to_read(range(0xD40B, 0xD40C), lambda addr: vcount)   # return value substitutes the read
mpu = MPU(memory=om)
```

- Callbacks: write → `callback(address, value)` (may return new value); read → `callback(address)` returns the byte, or `None` to fall through to RAM.
- Use for emulating `VCOUNT`, `SKSTAT`, capturing POKEY/GTIA writes in music tests. Slower than bytearray — enable only where needed.
- Disassemble for debugging: `from py65.disassembler import Disassembler; Disassembler(mpu).instruction_at(pc)` → `(length, text)`.
- `py65mon` interactive monitor exists (`py65mon -m 6502`; commands `load`, `goto`, `step`, `registers`, `disassemble`, `mem`) — useful for manual debugging, not for CI.

## Assertions & style

- Compare against a Python reference model for the same inputs; parametrize over edge values (0, 1, 127, 128, 255, wraparound, page-cross).
- Assert both outputs **and** non-clobbered memory/registers (guard bytes around buffers).
- Always bound execution (`max_steps`) and report PC in failure messages.
- Cycle-budget a DLI phase by stepping until the next `STA WSYNC` and measuring `processorCycles` (see `test_dli_faza_a_cycle_budget_and_faza_b_iter0`). Assert **each** phase separately against the mode/DMA budget and assert that the expected `WSYNC`s are still present, in order: a phase that grew silently is exactly what slips the whole kernel by one scanline.
- When a routine's contract is "Input: A = id", assert the id actually reached the tables: run it for two different ids and compare against each id's own data. A routine that always loads id 0 (e.g. because a loop clobbered A) still passes a single-id test.

- Don't test generated data content in `gen/` by hand-edited values — read labels from the `.lab` so tests survive relayout.
- Missing symbol ⇒ build is stale: keep a "symbols exist" test (see `test_flame_collision_symbols_exist`).

## Gotchas

- MADS is case-insensitive by default and writes symbol names to the `.lab` file in upper case, while this project's `parse_labels` also upper-cases them — always look up `labels["NAME"]` in upper case.
- Local/proc-scoped labels appear as `PROC.LABEL`; the regex must allow `.`, `@`, `?`.
- xex with INIT segments (`$02E2/$02E3`) are **not executed** by the loader above — init code must be called explicitly via `run_subroutine`.
- Bank-switched memory (`PORTB`) is not emulated; extended RAM reads/writes alias into the same 64K.
- py65 versions: API names (`stPushWord`, `processorCycles`, `memory`) are stable in 1.x; check `pip show py65` if an attribute is missing.
- Performance: about 10^6 simple instructions/s in CPython (measured with a NOP/JMP loop; expect less in test loops that peek/poke a lot); keep per-test step budgets under ~1M steps.
