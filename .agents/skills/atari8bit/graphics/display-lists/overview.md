# Overview

## Purpose

This file is a focused supplement to the ANTIC and display-list overview files.
Use it when the main boilerplate is not enough and you need the practical split-
screen rules: hardware-vs-shadow writes, scroll-update timing, chained DLIs,
and 4 KB playfield-boundary handling.

---

## Quick-Lookup

| Need | See § |
|---|---|
| Mandatory PHA/TXA/TYA/PLA/RTI boilerplate | §1 |
| Shadow vs hardware register table | §2 |
| VSCROL / HSCROL update rules | §2.1 |
| Shared multi-zone DLI | §4.1 |
| Chained per-band DLI handlers | §4.2 |
| Deferred VBI via `SETVBV` / `XITVBV` | §6 |
| 4 KB playfield boundary handling | §7 |
