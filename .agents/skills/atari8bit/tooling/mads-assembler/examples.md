# Examples

## 13.11 Practical MADS Example Patterns

Use MADS example patterns as a pattern library, not as cargo-cult source. These
examples are especially valuable when available in the current project or skill
bundle:

| Need | Example file | Technique to extract |
|---|---|---|
| Command-line parameters under DOS | `command_line.asm` | Check `BOOT`, validate `DOSVEC`, call the DOS parser through an indirect vector, copy ATASCII `$9B`-terminated args. |
| Compile-time flow | `if_else.asm`, `while.asm`, `rept.asm` | `IFT/ELI/ELS/EIF`, `#while/#end`, `.REPT` with `#` counter and label suffixes. |
| Scoped names | `macro_proc_local.asm`, `local*.asm` | Put macros/procs in `.LOCAL` namespaces; know that macro-local labels are uniquified per expansion. |
| Typed layout | `struct_enum.asm` | `.ENUM` values can define byte-sized types; `.STRUCT` fields can be used in `.VAR/.ZPVAR` and arrays. |
| Dual-address loader stubs | `file_loader.asm` | `ORG run_address,load_address` assembles for one address while storing bytes at another. |
| Boot disk loader | `Boot.asm` | Custom boot sector ("MADS format, JAC!", `opt h-f+`, `org $700`, 128-byte sectors): fills the DCB (`$301` DUNIT = drive 1, `$302` DCOMND = `'R'`, `$304` DBUF = `$0800`, `$30A` DAUX = first sector) and calls `load_from_disk` (`$E453`) in a loop, advancing `$304`/`$30A` per sector. |
| SDX/FAS inspection | `trace2.fas` | Parse `$FFFA/$FFFB/$FFFC/$FFFD/$FFFE` blocks and print segment/update/symbol metadata. |
| POKEY timer IRQ raster split | `irq_mcp.asm` | DLI arms the POKEY timer (`mva #1 AUDF4`, `STIMER` in the DLI) so a second IRQ fires per scanline for the colour split; the two display lists are swapped by ANTIC. |
| Tracker relocation | RMT/MPT/CMC/TMC relocator examples | Include player once, relocate module data with a macro, call init/play/silence through fixed vector offsets. |

When summarizing or porting Polish-commented examples, translate comments into precise English and keep the code idiom only if it still matches the target OS/DOS/hardware constraints.
