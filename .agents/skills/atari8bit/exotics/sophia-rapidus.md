---
name: atari8bit-peripherals
description: >-
  Sophia GTIA replacement card, APE-Time RTC, LDW Super 2000/CA-2001 SIO Z80 peripheral on Atari 8-bit.
---
# 16 — Peripheral Exotics & Misc Hardware

> LDW Super 2000 / CA-2001 programming guide (EN) — content self-contained but from a single unverified source.
> **Primary sources:** FujiNet firmware `github.com/FujiNetWIFI/fujinet-firmware` (`include/fujiCommandID.h`, `include/fujiDeviceID.h`, `lib/device/fujiDevice/fujiDevice.{h,cpp}`, `lib/device/NDevice/NDevice.{h,cpp}`, `lib/device/sio/sioNetwork.cpp`, `lib/device/fujiClock/fujiClock.cpp`) plus the project wiki (`FujiNet-Network-Protocol-Handbook`, `Accessing-the-Real-Time-Clock`, `SIO-Commands-for-Device-ID-$70`, `Additional-Commands-for-R:-Devices`). Vendor documentation for Sophia 2 and the LDW Super 2000/CA-2001 is not available online, so §16.1 and §16.3 are unverified.
> **Scope:** Sophia GTIA replacement (A/B/C + Sophia 2), APE-Time RTC (SIO $45/$93), LDW Super 2000/CA-2001 (SIO $58 Z80)
> **Key items:** APE DCB $45/$01/$93; LDW $58 Z80 @$7F00; Sophia 2 register map deliberately not listed (see §16.1)

## Quick-lookup

| Need | See § |
|---|---|
| Sophia: what it is, output formats, capabilities | §16.1 |
| Sophia 2: why no detection/register map is listed here | §16.1 |
| APE-Time RTC: SIO DCB $45/$01/$93, 6-byte binary payload | §16.2 |
| LDW Super 2000/CA-2001: SIO $58 upload + execute | §16.3 |
| LDW Z80 ROM functions $00\u2013$14 at $0004 | §16.3 |
| LDW I/O port table $0/$1\u2013$E/$F | §16.3 |

---

## 16.1 Sophia — GTIA Replacement Hardware

Sophia is a third-party GTIA replacement card that fits between the GTIA chip and the mainboard and takes over the video output, emulating the stock GTIA registers so unmodified software keeps working.

### Versions

| Version | Output |
|---------|--------|
| Sophia (Rev A / Rev B) | RGB / YPbPr, GTIA-compatible timing |
| **Sophia 2** (Simius, 2020) | RGB (TTL) and VGA output, settings stored on the card |

> ⚠ **Sophia register map is intentionally absent.** The register addresses, enable bits, signature byte and revision-register claims that earlier versions of this file carried (`$D01D`/`$D01E`/`$D015` bit assignments, "PMCNTL bit 3/4/5", "REV nibbles BCD 4..9") could not be verified against any authoritative source and have been removed. Take the register map from Simius's Sophia 2 documentation before writing detection or configuration code.

### Documented capabilities (feature level)

- 256-colour palette available in every graphics mode (Sophia's colour registers are 8-bit vs. GTIA's 7-bit).
- Per-pixel colour in hires Graphics 8 via `COLPF1`, where stock GTIA allows only one background colour.
- Corrected Graphics 10 pixel positioning/cycle behaviour relative to GTIA.
- Sophia 2 offers configurable output timing/resolution (e.g. VGA) with settings stored on the card.

The register names, addresses and bit meanings behind these features are **not** listed here — see the note above.

### Detection

> ⚠ **No detection routine is included.** Sophia 1 exposes no documented signature register, and Sophia 2's enable/signature registers could not be verified here; including an unverified routine would be worse than none. Get the register map (enable bit, signature value) from the Sophia 2 documentation before writing detection code.

Two rules that do not depend on the register map:

- `GRACTL` (`$D01D`) is **write-only** on the GTIA — never read it back to decide anything; keep your own shadow copy of the last value written (and of the player/missile enable bits you must restore).
- Never report "Sophia 2" from a signature probe alone: a zero/unknown result means "Sophia 1 or stock GTIA".

---

## 16.2 APE-Time Real-Time Clock

APE-Time is a SIO real-time clock protocol (originating with AtariMax's APE) that FujiNet also implements at device `$45`, so stock software can read NTP-synced time with no cartridge and no DOS.

| DCB field | Value |
|-----------|-------|
| DDEVIC | `$45` |
| DUNIT | `$01` |
| DCMND | `$93` |
| DSTATS | `$40` |
| DBUF | address of a 6-byte buffer |
| DBYT | `$06` |
| DTIMLO | `$0F` (15 s) |
| DAUX1 / DAUX2 | `$EE` / `$A0` in the published example; FujiNet ignores both (`DAUX1 = 1` selects the alternate time zone) |

After `JSR SIOV` (`$E459`) the device writes 6 bytes:

| Byte | Meaning |
|------|---------|
| 0 | Day, plain binary (1–31) |
| 1 | Month, plain binary (1–12) |
| 2 | Year, plain binary, as year−2000 |
| 3 | Hour (0–23) |
| 4 | Minute (0–59) |
| 5 | Second (0–59) |

The values are **binary, not BCD** — print them directly. The published BASIC example compares each byte with 10 to pad single digits, which only makes sense for binary values (`PEEK`ing a BCD byte would show e.g. 19 for the 13th of the month).

Beyond `$93`, FujiNet's `$45` clock device also answers `$49` (`'I'`, ISO-8601 local string), `$5A` (`'Z'`, ISO-8601 UTC), `$50` (`'P'`, 4-byte ProDOS time), `$4D` (7-byte simple time + hundredths) and `$99`/`$74` (set alternate/FujiNet time zone). See the FujiNet clock section for the full list.

---

## 16.3 LDW Super 2000 / CA-2001 Positioning Device

> ⚠ **Single unverified source:** everything in this section comes from one vendor/community article and could not be cross-checked. In particular the "2-second USR-break watchdog" timing advice is unverified — use it only as a starting point. The Z80 function table is documented as `$00`–`$14`; `$15` and above are reserved.

LDW Super 2000 (and compatible clone CA-2001) is a position-digitiser peripheral with a Z80 CPU, communicating over SIO command `$58`. The Z80 firmware runs at 4 MHz; code is uploaded to address `$7F00` in the device RAM.

### Command `$58` — two phases

**Phase 1 — upload firmware:**
| DCB field | Value |
|-----------|-------|
| DDEVIC | `$31` |
| UNIT | station number |
| DCMND | `$58` ('X') |
| DSTATS | `$80` (write) |
| DBUFA | buffer address in Atari RAM |
| DTIMLO | sector-timeout (8 = typical) |
| DBYT | ≤ 256 bytes |
| DAUX2 | `$01` (download-to-device-RAM) |

Busy lamp lights on the device console during upload. A second command must NOT be sent between upload and execute.

**Phase 2 — execute firmware:**

Same DCMND `$58`, but `DBUFA` → data buffer, `DSBY` = expected result byte count, `DTIMLO` = timeout. `DSTATS` determines the data transfer direction:

| DSTATS | Meaning |
|--------|---------|
| `$00` | No data exchange |
| `$40` | Read result bytes from device (`DBUFA`) |
| `$80` | Write additional input bytes to device |
| `$C0` | Bidirectional |

**Z80 ROM function table** (at `$0004` in device address space):

| FN | Description |
|----|-------------|
| `$00` | Return ROM version (major×256 + minor) in (DE) |
| `$01` | Return head / idle |
| `$02` | Seek head to track (D = track × 2) |
| `$03` | Read sector (E) from track (D) |
| `$04` | Write sector (E) to track (D) |
| `$05` | Receive byte from SIO (C = return) |
| `$06` | Transmit byte to SIO (A = value) |
| `$07` | Receive record of length (B) from SIO into (DE); B=0 → 256 bytes |
| `$08` | Transmit record of length (B) from (DE) to SIO |
| `$09` | Convert digit for display (A in/out) |
| `$0A` | Decimal conversion (A → DE, 2-digit) |
| `$0B` | Hex conversion (A → DE, 2-digit) |
| `$0C` | Motor on/off (CF=1 → on; CF=0 → off) |
| `$0D` | Update switch status / detect disk change |
| `$0E` | Return current buffer address (→BC) |
| `$0F` | Return control-flag byte address (→IX) |
| `$10` | Audio beep |
| `$11` | Update the display |
| `$12` | Return register addresses (read and write controller) (→BC, →DE) |
| `$13` | Set write density for current mode |
| `$14` | Return status / current track (→DE, →IX; track × 2) |

**Z80 I/O ports:**

| Port | I/O | Description |
|------|-----|-------------|
| `$0/$1` | IN | Audio signal |
| `$2/$3` | IN | Index impulse tracking enable |
| `$4/$5` | IN | Invert TxD |
| `$6/$7` | IN | Invert RxD |
| `$8/$9` | IN | Generation / set DDEN for FDC |
| `$A/$B` | IN | Motor |
| `$C/$D` | IN | Index impulse output |
| `$E/$F` | IN | RAM charger switch (maps $0000–$7FFF RAM → RAM → ROM) |

---

*LDW Super 2000 / CA-2001 content is reproduced from a single unverified source. APE-Time behaviour was verified against the FujiNet firmware and wiki. Sophia register-level details could not be verified and were removed (see §16.1).*
