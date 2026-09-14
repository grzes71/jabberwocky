# Project History & Changelog

<!-- AGENT INSTRUCTIONS: Always prepend new entries directly below this comment block. Use the exact format: `## [YYYY-MM-DD] - Feature/Fix Title` -->

## [2026-09-14] - Poprawka kolejności przywracania obiektów w game_init
- **Scena gry (`scenes/game.asm`)**:
  - Przesunięto wywołania `init_flame_collision` oraz `restore_all_secrets` przed `init_level_screens` w procedurze `game_init`.
  - Zapobiegło to ładowaniu wyczyszczonego bufora `screens_vram[0]` do `GAME_ACTION_VRAM` oraz `blocking_col8/9` przed przywróceniem obiektów, dzięki czemu obiekty z ekranu 0 (w tym `Secret` i `Secret+Interactive`) odnawiają się poprawnie przy starcie nowej gry.
- **Testy automatyczne (`tests/test_secret_collision.py`)**:
  - Rozszerzono test `test_secret_run_persistence_and_game_init_restoration` o wywołanie `GAME_INIT` i weryfikację odtworzenia kafelków w aktywnym buforze `GAME_ACTION_VRAM`.

## [2026-09-14] - Zbieranie obiektów Interactive oraz Secret + Interactive
- **Baza danych i prekompilacja (`scripts/labirynt_builder.py`)**:
  - Rozszerzono `bake_screen_blocking` o bit 1 (`$02`) dla obiektów z flagą `interactive: true`.
  - Włączono obiekty z flagami `interactive` oraz `secret` do generowania tablic backupowych `secret_objs_backup` z poprawnym kodowaniem masek `$01`, `$02` i `$04`.
- **Silnik kolizji i mechanika nagród (`engine/flame_collision.asm`)**:
  - W `check_dragon_secret_collision`: rozszerzono filtr wierszy na maskę `$06` (`blocking_col8/9`), wykrywającą kafelki `interactive` ($02) oraz `secret` ($04).
  - W `check_single_screen_secret`: dodano zapamiętywanie flag obiektu (`fc_cur_obj_flags`) i selekcję nagród:
    - Flaga `interactive` (tylko): `SCORE + 5` (procedura `add_score_5`), `ENERGY + 5` jednostek/sub-kroków (procedura `increase_energy_5`).
    - Flagi `secret` AND `interactive`: `SCORE + 10` (procedura `add_score_10`), `SHOTS + 1` dodatkowy strzał (procedura `add_shot_1`).
    - Flaga `secret` (tylko): `SCORE + 1` (`add_score_1`).
  - Dodano podprogramy `add_score_5`, `add_score_10` (arytmetyka BCD), `increase_energy_5` (5-krotne wywołanie `increase_energy_bar` z cappingiem) oraz `add_shot_1` (`inc SHOTS`, max 99, odświeżenie paska stanu).
  - Dodano aliasy kompatybilności `check_dragon_item_collision` oraz `restore_all_collectibles`.
- **Testy automatyczne (`tests/test_secret_collision.py`)**:
  - Dodano 7 nowych testów weryfikujących procedury `ADD_SCORE_5`, `ADD_SCORE_10`, `ADD_SHOT_1`, `INCREASE_ENERGY_5`, brak kolizji ze ścianą dla masek `$02` i `$06`, oraz pełne przepływy zbierania obiektów `interactive` (+5 pkt, +5 energii) i `secret+interactive` (+10 pkt, +1 strzał).

## [2026-09-13] - Zamiana dźwięku zebrania sekretu na krótki "click"
- **Warstwa audio (`engine/sound.asm`)**:
  - Skrócono czas trwania efektu dźwiękowego zebrania sekretu do 3 klatek (`SECRET_CLICK_FRAMES = 3`).
  - Zastąpiono dwutonowy dzwonek perkusyjnym, krótkim impulsem typu "click" o opadającej głośności (ramka 1: `$08`, `$AE`; ramka 2: `$14`, `$A7`; ramka 3: wyciszenie).
- **Testy (`tests/test_secret_collision.py`)**:
  - Zaktualizowano asercję timera dźwięku zebrania do nowej długości efektu.

## [2026-09-13] - Obsługa obiektów typu Secret, punktacja SCORE i trwałość w rozgrywce
- **Baza danych i prekompilacja (`scripts/labirynt_builder.py`)**:
  - Rozszerzono macierz kolizji `screens_blocking` o bit 2 (`$04`) dla obiektów z flagą `secret: true`.
  - Dodano generowanie tablic `secret_objs_backup` (`secret_objs_total`, współrzędne, wymiary, wskaźniki do kafli i masek) na potrzeby resetu nowej gry.
- **Engine kolizji (`engine/flame_collision.asm`)**:
  - `check_dragon_blocking_collision`: odfiltrowano bit 0 (`and #$01`), uniemożliwiając fałszywe zderzenia ze ścianą przy kontakcie z sekretami.
  - `check_dragon_secret_collision` & `check_single_screen_secret`: zoptymalizowana detekcja kolizji smoka ($O(1)$) z sekretami na podstawie strumieniowanych buforów `blocking_col8/9`.
  - `erase_object_from_source_buffers`: wymazywanie zebranego sekretu bezpośrednio z `screens_vram` i `screens_blocking` w High RAM, gwarantujące brak odradzania się po respawnie smoka (`respawn_dragon`).
  - `add_score_1`: obsługa 4-cyfrowej arytmetyki dziesiętnej BCD w `SCORE` z propagacją przeniesień i odświeżaniem paska stanu (`update_bottom_status`).
  - `restore_all_secrets`: procedura przywracania oryginalnych kafli i masek sekretów z tablic backupowych przy rozpoczęciu nowej gry (`game_init`).
- **Warstwa audio (`engine/sound.asm`)**:
  - Dodano `start_secret_sound` i `update_secret_sound` – 12-klatkowy dwutonowy dzwonek zebrania na 4. kanale POKEY (`AUDF4`, `AUDC4`).
- **Scena gry (`scenes/game.asm`)**:
  - Wpięto `restore_all_secrets` w `game_init`.
  - Wpięto `check_dragon_secret_collision` przed sprawdzaniem przeszkód w `check_dragon_collisions`.
  - Wpięto `update_secret_sound` w pętli renderowania ramki `@render_frame`.
- **Testy automatyczne (`tests/test_secret_collision.py`)**:
  - Utworzono zestaw 5 testów integracyjnych w py65 weryfikujących detekcję, punktację BCD, brak kolizji ze ścianą, trwałość po śmierci smoka i odtwarzanie po restarcie gry.

## [2026-09-13] - Inicjalizacja dziennika
- Utworzono strukturę pliku HISTORY.md.