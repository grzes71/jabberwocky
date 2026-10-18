# Notes

## 3.11  Emulator Accuracy Notes

| Behaviour | Note |
|---|---|
| DLI/WSYNC timing | Verify on real hardware or a cycle-accurate emulator; small DMA differences matter. |
| Fine-scroll edge cases | Mixed-mode scrolling and VSCROL/HSCROL tricks are timing-sensitive. |
| GTIA 9/10/11 + HSCROL | Use even HSCROL values so GTIA pixel pairing stays correct. |

---

## 3.12  Practical Warnings

1. **Set `VDSLST` before enabling `NMIEN` bit 7.**
2. **In DLIs, write hardware registers** (`$D0xx`/`$D4xx`), **not page-2 shadows.**
3. **For clean visible splits, do `WSYNC` first** and then the hardware writes for the next scan line.
4. **Keep DLI handlers short and deterministic.**
