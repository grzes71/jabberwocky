# Relokacja pamięci — Skorygowany plan (missiles aktywne)

World data (20 ekranów + 3 labirynty) = **21686 B**, start `$7000` → koniec `$C4B5`, przekroczone `$BFFF` o **1206 B**.

## Strategia (łączny zysk: 1536 B)

### Ruch 1 — DLIST + GAME_FONT (zysk: 1024 B)

| Segment | Przed | Po |
|---|---|---|
| `DLIST_ADDR` | `$6800` | `$6610` (gap po BLOCKING_VRAM) |
| `GAME_FONT_ADDR` | `$6C00` | `$6800` (1KB aligned ✓) |
| `WORLD_DATA_ADDR` | `$7000` | `$6C00` |

DLIST (316 B) trafia do `$6610-$674B` — nie przekracza granicy 1KB (`$6400-$67FF` block).

### Ruch 2 — 2× OBJ_TYPE do strefy PMG (zysk: 512 B)

PMG single-line resolution — mapa bufora `$2000-$27FF`:

```
$2000-$22FF  (768 B)  ← NIEUŻYWANE przez ANTIC DMA
$2300-$23FF  (256 B)  ← Missiles (ogień smoka)
$2400-$27FF (1024 B)  ← Players 0-3 (smok + UI)
```

ENGINE kończy się na `$20AD`. Strefa `$20AE-$22FF` (594 B) jest **bezpieczna** — ANTIC DMA nigdy nie czyta z tych adresów.

Przenosimy `obj_type_width` (256 B) i `obj_type_height` (256 B) z `gen/world_data.asm` do `gen/world_obj_tiles.asm`. Dołączą na końcu ENGINE segmentu:

```
$20AE-$21AD  obj_type_width   (256 B)
$21AE-$22AD  obj_type_height  (256 B)
$22AE-$22FF  FREE             (82 B gap do missiles)
$2300        missiles start   ← bezpieczne
```

`obj_type_flags` (256 B) **pozostaje** w `world_data.asm`.

### Wynik

| Metryka | Wartość |
|---|---|
| World data (po usunięciu 2 tablic) | 21686 − 512 = **21174 B** |
| Start | `$6C00` |
| Koniec | `$BEB5` |
| Headroom do `$BFFF` | **330 B** |

---

## Proponowane zmiany

### [MODIFY] [main.asm](file:///c:/Users/grzes/Documents/Projects/jabberwocky/main.asm)

- `DLIST_ADDR = $6610` (było `$6800`)
- `GAME_FONT_ADDR = $6800` (było `$6C00`)
- `WORLD_DATA_ADDR = $6C00` (było `$7000`)
- Zaktualizowane komentarze w sekcji Memory Map

### [MODIFY] [Makefile](file:///c:/Users/grzes/Documents/Projects/jabberwocky/Makefile)

- `--charset-base 0x6800` (było `0x6C00`)

### [MODIFY] [scripts/gen_animated_charset.py](file:///c:/Users/grzes/Documents/Projects/jabberwocky/scripts/gen_animated_charset.py)

- Default `charset-base` → `0x6800`

### [MODIFY] [scripts/labirynt_builder.py](file:///c:/Users/grzes/Documents/Projects/jabberwocky/scripts/labirynt_builder.py)

- Przenieść generowanie `obj_type_width` i `obj_type_height` z `generate_world_asm()` do `generate_obj_tiles_asm()`.
- `obj_type_flags` pozostaje w `generate_world_asm()`.

### [MODIFY] [engine/charset_anim.asm](file:///c:/Users/grzes/Documents/Projects/jabberwocky/engine/charset_anim.asm)

- Komentarze: `$6C00` → `$6800`

### [MODIFY] [tests/test_charset_anim.py](file:///c:/Users/grzes/Documents/Projects/jabberwocky/tests/test_charset_anim.py)

- Zaktualizować hardkodowane adresy jeśli potrzebne

---

## Verification Plan

```bash
make all
```

Musi przejść bez błędów (`assets → data → tests → xex → check_memory`). Mapa pamięci powinna pokazywać ENGINE kończący się na ~`$22AD` i WORLD_DATA kończący się na ~`$BEB5`.
