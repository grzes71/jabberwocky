# Podsumowanie: Kolizja i Zbieranie Obiektów Typu Secret (Score +1 & Persistence)

## Zrealizowane Wymagania
1. **Wykrywanie kolizji ze smokiem z obiektami `secret: true`**:
   - Wykorzystano spatial matrix kolizji: bit 2 (`$04`) w tablicach `screens_blocking` oraz w strumieniowanych buforach kolumny 8 i 9 (`blocking_col8`, `blocking_col9`).
   - Zerowy narzut na pamięć RAM i streaming (współdzielony bufor z `blocking`).
   - W kolumnach 8 i 9 smok sprawdza wyłącznie zakres wierszy smoka (`dc_dragon_row_min` .. `dc_dragon_row_max_p1 - 1`). Jeśli bit 2 nie występuje, detekcja kończy się w ~30 cyklach bez szarpnięć ekranu.
2. **Efekt zebrania sekretu**:
   - Obiekt natychmiast znika z bufora ekranu gry (`GAME_ACTION_VRAM`) oraz `blocking_col8/9` (`erase_cur_object`).
   - `SCORE` zostaje zwiększony o 1 (4-cyfrowa arytmetyka dziesiętna BCD z propagacją przeniesień do 9999).
   - Dolny pasek stanu natychmiast odświeża wynik (`update_bottom_status`).
   - Odtwarzany jest 12-klatkowy dwutonowy dźwięk zebrania (POKEY Kanał 4, `start_secret_sound`).
3. **Odseparowanie od kolizji ze ścianami (`blocking`)**:
   - `check_dragon_blocking_collision` filtruje wyłącznie bit 0 (`and #$01`). Obiekty z flagą `secret: true` nie powodują zatrzymania ani śmierci smoka.
4. **Trwałość zebrania w trakcie bieżącej rozgrywki (Persistence across deaths)**:
   - Po zebraniu sekret jest natychmiast czyszczony w buforach źródłowych ekranu (`screens_vram` i `screens_blocking` w High RAM).
   - Gdy smok zginie i nastąpi restart poziomu (`respawn_dragon` -> `load_world_screen`), ekran ładuje się już bez zebranego sekretu.
   - W przypadku nowej gry (`game_init` po Game Over), procedura `restore_all_secrets` przywraca pierwotne kafle i maski z wygenerowanych tablic backupowych `secret_objs_backup`.

---

## Zmodyfikowane i Utworzone Pliki

| Plik | Zakres zmian |
| --- | --- |
| [scripts/labirynt_builder.py](file:///c:/Users/grzes/Documents/Projects/jabberwocky/scripts/labirynt_builder.py) | Oznaczanie bitu 2 (`$04`) dla kafli `secret` w `screens_blocking`. Generowanie tabel `secret_objs_backup` dla przywracania stanu na `game_init`. |
| [engine/sound.asm](file:///c:/Users/grzes/Documents/Projects/jabberwocky/engine/sound.asm) | Implementacja dwutonowego dzwonka zebrania sekretu na kanale 4 POKEY (`start_secret_sound`, `update_secret_sound`). |
| [engine/flame_collision.asm](file:///c:/Users/grzes/Documents/Projects/jabberwocky/engine/flame_collision.asm) | `check_dragon_blocking_collision` (filtr `and #$01`), `check_dragon_secret_collision`, `check_single_screen_secret`, `erase_object_from_source_buffers`, `add_score_1`, `restore_all_secrets`. |
| [scenes/game.asm](file:///c:/Users/grzes/Documents/Projects/jabberwocky/scenes/game.asm) | Wywołanie `restore_all_secrets` w `game_init`, wywołanie `check_dragon_secret_collision` przed sprawdzaniem ściany, wywołanie `update_secret_sound` w pętli ramki. |
| [tests/test_secret_collision.py](file:///c:/Users/grzes/Documents/Projects/jabberwocky/tests/test_secret_collision.py) | 5 automatycznych testów integracyjnych w py65 sprawdzających pełen cykl detekcji, punktację BCD, brak kolizji ze ścianą, trwałość po respawnie i odtworzenie na nową grę. |

---

## Weryfikacja i Wyniki

- **Kompilacja i mapa pamięci (`make all`)**:
  - `CODE` segment ($2800..$3FFF): **138 bajtów wolnego miejsca** (wykorzystano jedynie 9 bajtów na skoki `JSR`, cała logika umieszczona w High RAM).
  - Całkowita wolna pamięć RAM: **18 374 bajtów (39.0% headroomu)**.
  - Brak nakładania się segmentów.
- **Testy automatyczne (`pytest`)**:
  - `tests/test_secret_collision.py`: 5/5 zdanych testów.
  - Cały zestaw testów projektu: **94/94 zdanych testów** (100% pass).
