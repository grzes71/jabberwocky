# Obsługa Kolizji z Obiektami „Secret” (Zniknięcie Obiektu, SCORE +1, Trwałość w Rozgrywce)

Implementacja wysoce wydajnego algorytmu detekcji kolizji smoka z obiektami oznaczonymi flagą `secret: true`. Po wleceniu smoka w taki obiekt:
1. Obiekt znika z ekranu gry (`GAME_ACTION_VRAM`),
2. Wartość `SCORE` rośnie o 1,
3. Odtwarzany jest czysty dźwięk zebrania (POKEY kanał 4),
4. **Trwałość w rozgrywce (wymóg użytkownika)**: zebrany obiekt pozostaje zebrany (niewidoczny i nieaktywny) przez resztę danej rozgrywki — nawet gdy smok zginie i dany poziom restartuje się od początku (`respawn_dragon`). Obiekty sekretów odnawiają się dopiero przy starcie nowej gry po Game Over (`game_init`).

---

## Architektura Rozwiązania

### 1. Współdzielona matryca kolizji ekranu (`screens_blocking`)
- W pre-renderowanej tablicy 440 bajtów na ekran (11 wierszy $\times$ 40 kolumn) dotychczas wykorzystywany był wyłącznie bit 0 (`$01` dla `blocking`).
- **Bit 2 (`$04`)** koduje obecność kafelków obiektów oznaczonych `secret: true`.
- **Zero dodatkowej pamięci RAM** — matryce ekranów nie zwiększają swojego rozmiaru.

### 2. Zero-overhead spatial grid streaming
- Istniejący bufor `blocking_col8` i `blocking_col9` (22 bajty w High RAM) automatycznie przesyła pełne bajty z matrycy ekranu podczas przewijania.
- Flagi `secret` są zawsze aktualne w kolumnach smoka (kolumny 8 i 9 VRAM).

### 3. Błyskawiczna detekcja kolizji ($O(1)$, ~20 cykli w klatce)
- W standardowych klatkach (99.9% czasu) sprawdzamy jedynie, czy `(blocking_col8[r] | blocking_col9[r]) & $04` w wierszach smoka jest niezerowe.
- Koszt: zaledwie 2-3 odczyty i maskowania, brak jakiegokolwiek szarpania ekranu.

### 4. Zdarzenie zebrania i trwałość w rozgrywce
Gdy smok wlatuje w kafelki sekretu (wykryty bit `$04`):
1. **Natychmiastowe usunięcie z ekranu**:
   - Wyczyszczenie kafelków obiektu w `GAME_ACTION_VRAM` do `$00`.
   - Wyzerowanie bitów kolizji w `blocking_col8` i `blocking_col9`.
2. **Trwałe usunięcie z buforów źródłowych poziomu w RAM**:
   - Wyzerowanie kafelków tego obiektu w `screens_vram[screen]` oraz `screens_blocking[screen]`.
   - Dzięki temu:
     - Jeśli poziom przewija się dalej, żadna część obiektu nie pojawi się ponownie.
     - Jeśli smok zginie i poziom restartuje się od początku (`respawn_dragon`), `load_world_screen` ładuje poziom z bufora RAM, w którym sekret **jest już trwale usunięty**! Obiekt nie odnawia się w danej rozgrywce!
3. **Punktacja**:
   - Zwiększenie `SCORE` o 1 (`add_score_1` z obsługą dziesiętną BCD) i aktualizacja dolnego paska stanu (`update_bottom_status`).
4. **Audio**:
   - Uruchomienie czystego dźwięku zebrania na POKEY kanale 4 (`AUDF4`, `AUDC4`).
5. **Restart całej gry (`game_init`)**:
   - Przy powrocie do nowej gry po Game Over procedura `restore_all_secrets` przywraca pierwotne kafelki sekretów z małej tablicy kopii zapasowej wygenerowanej przez `scripts/labirynt_builder.py` (~50-100 bajtów w High RAM).

---

## Proponowane Zmiany w Plikach

### 1. Narzędzia i Pipeline Danych
#### [MODIFY] [`scripts/labirynt_builder.py`](file:///c:/Users/grzes/Documents/Projects/jabberwocky/scripts/labirynt_builder.py)
- W `bake_screen_blocking` ustawianie bitu 2 (`$04`) dla kafelków obiektów z `secret: true`.
- Generowanie tablicy kopii zapasowej sekretów (`secret_objs_backup`) umożliwiającej przywrócenie stanu kafelków w `screens_vram` i `screens_blocking` przy starcie nowej gry (`game_init`).

### 2. Silnik Kolizji i Dźwięku
#### [MODIFY] [`engine/flame_collision.asm`](file:///c:/Users/grzes/Documents/Projects/jabberwocky/engine/flame_collision.asm)
- W `check_dragon_blocking_collision`: maskowanie `and #$01` (kolizja śmiertelna dotyczy wyłącznie obiektów `blocking`).
- Dodanie `check_dragon_secret_collision`:
  - Weryfikacja bitu 2 (`$04`) w kolumnach 8 i 9.
  - Wyczyszczenie kafelków w `GAME_ACTION_VRAM`, `blocking_col8/9`, oraz w buforach źródłowych `screens_vram` i `screens_blocking`.
  - Wywołanie `add_score_1` oraz `start_secret_sound`.
- Dodanie procedur `add_score_1` oraz `restore_all_secrets`.

#### [MODIFY] [`engine/sound.asm`](file:///c:/Users/grzes/Documents/Projects/jabberwocky/engine/sound.asm)
- Dodanie obsługi dźwięku zebrania sekretu na kanale 4 POKEY (`start_secret_sound`, `update_secret_sound`).

### 3. Pętla Gry
#### [MODIFY] [`scenes/game.asm`](file:///c:/Users/grzes/Documents/Projects/jabberwocky/scenes/game.asm)
- W `game_init`: wywołanie `restore_all_secrets` (odnowienie sekretów przed nową rozgrywką).
- W `check_dragon_collisions`: wywołanie `check_dragon_secret_collision` przed detekcją ścian i energii PF3.
- W `vblank_game`: wywołanie `update_secret_sound`.

---

## Plan Weryfikacji

### Testy Automatyczne (py65 + pytest)
1. Utworzenie dedykowanego testu [`tests/test_secret_collision.py`](file:///c:/Users/grzes/Documents/Projects/jabberwocky/tests/test_secret_collision.py):
   - Zebranie obiektu `secret: true` usuwa go z VRAM i zwiększa `SCORE` o 1.
   - Zebrany obiekt nie zabija smoka.
   - Po wywołaniu `respawn_dragon` i przeładowaniu ekranu (`load_world_screen`), zebrany sekret **nie pojawia się ponownie**.
   - Po wywołaniu `game_init` (nowa gra), sekret zostaje przywrócony.
2. Uruchomienie pełnego suite:
   ```bash
   make all
   make test
   ```
3. Weryfikacja mapy pamięci przez `scripts/generate_memory_map.py` (sprawdzenie headroomu).
