# Reset

## 2.2  Power-On / Reset

| Condition | Behavior |
|---|---|
| Power-on | CPU starts through the RESET vector; RAM contents are undefined until initialized |
| 400/800 RESET key | Raises an NMI reported by ANTIC `NMIST` bit 5 and enters the OS warm-start path; RAM is preserved; PIA is **not** reset |
| XL/XE RESET key | Hardware reset of the system; RAM is normally preserved on a warm reset, but hardware and OS shadows/vectors must be reinitialized |

Practical rules:

- Use `WARMST ($08)` and `COLDST ($0244)` together with your own RAM signature if you need to distinguish a recoverable warm reset from a cold start.
- If you own `SDLSTL`, `VDSLST`, or VBI vectors, expect the OS warm-start path to rebuild display/editor state unless you reinstall your values.
- Power-on RAM patterns are not stable data; always initialize anything you depend on.

---
