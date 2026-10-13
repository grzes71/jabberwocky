# Sio Disk

## §7.1  SIO Serial I/O

> ⚠ **SIO timeout:** Each SIO phase is time-limited: SIO arms a countdown timer (derived from the DCB timeout `DTIMLO` and the handler's own limits) and returns a timeout error (`$8A`) if the device never answers. A silent device therefore fails the call instead of hanging it — check `DSTATS` ($0303) after every SIO call before reusing the DCB, and never retry-loop on a dead channel.

> ⚠ **IOCB status discipline:** After CIO calls, always check the returned status before consuming data or reusing the IOCB. Poll loops that treat any nonzero status as success can race device-handler transitions and lose data.

### Frame format

```
[LEADER] [DEVICE_ID (1)] [COMMAND_FRAME] [ACK/NACK] [DATA_FRAME(s)] [STATUS_FRAME]
```

| Field | Value |
|---|---|
| Device ID | Unit address: $31–$3F disk (D1:–D8: = $31–$38), $40–$4F printer, $60 cassette, $70+ third-party |
| Leader | A run of `$55` bytes; the frame begins at the first byte that is not `$55` |
| COMMAND frame | 5 bytes: Device ID + command byte + AUX1 + AUX2 + checksum, sent while COMMAND is asserted low |
| ACK/NACK | 1 byte from the device: ACK `$41` (`'A'`) or NAK `$4E` (`'N'`) |
| DATA frame | Data bytes + one-byte checksum |
| STATUS | One byte from the device at the end of the operation: COMPLETE `$43` (`'C'`) or ERROR `$45` (`'E'`) |

The selected device answers the command frame with ACK (`$41`); NAK (`$4E`) or silence means the frame was rejected. The receiving side acknowledges each data frame the same way, and a finished operation ends with a single status byte, COMPLETE (`$43`) or ERROR (`$45`).

---

## §7.2  Disk Drives (810 / 1050 / XF551 / Indus GT)

| Drive | Key features |
|---|---|
| 810 | WD1771 FDC; single density (FM), 128-byte sectors, 90 KB |
| 1050 | Single + enhanced density (130 KB); 256-byte sectors need a US Doubler-class ROM; single-sided |
| XF551 | Double density (MFM), 256-byte sectors, 360 KB double-sided |
| Indus GT | Double density, 180 KB single-sided; compatible with the standard SIO disk commands |

The drive's SIO address goes in `DDEVIC` ($31 for D1:, $32 for D2:, …) and the drive number in `DUNIT`.

---
