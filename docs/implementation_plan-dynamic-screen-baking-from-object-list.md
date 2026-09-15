# Plan implementacji: Dynamiczne pieczenie ekranów z list obiektów (Wariant A)

Zwiększenie liczby ekranów do 10 na każdy poziom (łącznie min. 30 ekranów dla 3 poziomów) przy zachowaniu ścisłych limitów pamięci Atari 8-bit RAM ($0800–$BFFF).

## User Review Required

> [!IMPORTANT]
> **Fundamentalna zmiana reprezentacji danych świata:**
> Zamiast pre-renderować na etapie budowania pełne 440-bajtowe matryce `screen_XXX_vram` oraz `screen_XXX_blocking` dla każdego ekranu (co przy 30 ekranach pochłonęłoby aż **26,4 KB** na same matryce), w pamięci stałej ROM/XEX przechowujemy **wyłącznie kompaktowe listy instancji obiektów** (`obj_count`, `codes`, `coords` — średnio ~70 bajtów na ekran).
>
> 30 ekranów zajmie w pamięci świata zaledwie **~2,5–3 KB** (zamiast 31,5 KB), co zwalnia **ponad 20 KB pamięci RAM** i umożliwia bezproblemową rozbudowę gry do 30, 50, a nawet 80+ ekranów.

> [!NOTE]
> W pamięci RAM alokowane są dwa bufory robocze (Ping-Pong Staging Buffers) po 880 bajtów każdy (440 B VRAM + 440 B Blocking = 1760 B łącznie):
> - **Bufor A**: ekran aktualnie schodzący (Left Screen)
> - **Bufor B**: ekran aktualnie wjeżdżający (Incoming Screen)
>
> Kiedy ekran wjeżdża w całości na pole gry (`incoming_col_idx == 40`), następuje zamiana ról (pointer swap), a kolejny ekran z labiryntu jest w ułamku klatki (~2-3 ms) wypiekany z listy obiektów do zwolnionego bufora przez procedurę 6502 `bake_screen`.

---

## Proponowane zmiany

### 1. Kompilator świata ([scripts/labirynt_builder.py](file:///c:/Users/grzes/Documents/Projects/jabberwocky/scripts/labirynt_builder.py))

- Usunięcie generowania statycznych 440-bajtowych tablic `screen_XXX_vram` i `screen_XXX_blocking` w `generate_world_asm()`.
- Pozostawienie funkcji `bake_screen_vram` i `bake_screen_blocking` w Pythonie jako narzędzi pomocniczych i testowych.
- Generowanie wyłącznie tablic obiektów:
  - `screen_XXX_obj_count`: liczba obiektów na danym ekranie (1 bajt)
  - `screen_XXX_codes`: tablica kodów obiektów (1 bajt na obiekt)
  - `screen_XXX_coords`: tablica spakowanych współrzędnych `packed_xy` (1 bajt na obiekt)
  - Wskaźniki SoA: `screens_obj_count`, `screens_codes_lo/hi`, `screens_coords_lo/hi`.
- Usunięcie generatora tablic backupu sekretów (`secret_objs_*`), ponieważ odtworzenie ekranu jest natychmiastowe z listy obiektów.

---

### 2. Silnik pieczenia ekranów w 6502 ([scenes/game.asm](file:///c:/Users/grzes/Documents/Projects/jabberwocky/scenes/game.asm))

- **Implementacja procedury `bake_screen`**:
  - Wejście: `X = screen_idx`, `PTR_DST` = docelowy bufor VRAM (440 B), `PTR_BLK` = docelowy bufor Blocking (440 B).
  - Krok 1: Wypełnienie buforów zerami ($00).
  - Krok 2: Pobranie liczby obiektów z `screens_obj_count,x`.
  - Krok 3: Pętla po obiektach $i = 0 .. N-1$:
    - Sprawdzenie bitu w `screen_obj_destroyed` — jeśli obiekt został zniszczony ogniem lub zebrany jako sekret, jest pomijany!
    - Rozpakowanie współrzędnych `packed_xy`: `obj_x = (packed & $1F) * 2`, `obj_y = ((packed >> 4) & $0E)`.
    - Pobranie wymiarów `obj_type_width`, `obj_type_height` oraz flag `obj_type_flags`.
    - Obliczenie maski kolizji (`$01` blocking, `$02` interactive, `$04` secret).
    - Jeśli obiekt posiada puste glify (`flags & $80`), pobranie wskaźnika do kafelków z `obj_type_tiles_lo/hi`.
    - Zapis kafelków do bufora VRAM i maski kolizji do bufora Blocking.
- **Alokacja buforów stagingowych**:
  - `screen_buf_a_vram` (440 B) + `screen_buf_a_blk` (440 B)
  - `screen_buf_b_vram` (440 B) + `screen_buf_b_blk` (440 B)
  - Wskaźniki: `cur_left_vram_ptr`, `cur_left_blk_ptr`, `incoming_screen_vram_ptr`, `incoming_screen_blk_ptr`.
- **Aktualizacja `init_level_screens`**:
  - Wypieczenie ekranu 0 poziomu do bufora A.
  - Skopiowanie bufora A do `GAME_ACTION_VRAM` (kolumny 4..43) i inicjalizacja `blocking_col8/9`.
  - Wypieczenie ekranu 1 poziomu (jeśli istnieje) do bufora B.
  - Ustawienie `incoming_screen_vram_ptr` na bufor B.
- **Aktualizacja `scroll_playfield_step`**:
  - Po zakończeniu wjeżdżania ekranu (`incoming_col_idx == 40`):
    - Zamiana wskaźników buforów (bufor B staje się Left Screen).
    - Wypieczenie kolejnego ekranu z labiryntu do bufora A (staje się Incoming Screen).

---

### 3. Detekcja kolizji i destrukcja ([engine/flame_collision.asm](file:///c:/Users/grzes/Documents/Projects/jabberwocky/engine/flame_collision.asm))

- Uaktualnienie `erase_object_from_source_buffers`:
  - Obiekt jest wymazywany bezpośrednio z aktywnego bufora stagingowego (A lub B) oraz z widocznego `GAME_ACTION_VRAM`.
  - Ustawiany jest odpowiedni bit w `screen_obj_destroyed`.
  - Brak potrzeby modyfikacji stałych tablic w High RAM!
- Usunięcie procedury `restore_all_secrets`:
  - Przy rozpoczęciu nowej gry wystarczy wyczyszczenie `screen_obj_destroyed` (`init_flame_collision`), a wszystkie sekrety są automatycznie renderowane przy pieczeniu ekranów.

---

### 4. Pamięć i plik główny ([main.asm](file:///c:/Users/grzes/Documents/Projects/jabberwocky/main.asm))

- Przeniesienie buforów stagingowych (1760 B) do dedykowanego obszaru pamięci RAM (np. `$6800` lub tuż za małym segmentem `WORLD_DATA`).
- Zaktualizowanie komentarzy mapy pamięci.

---

### 5. Aktualizacja testów py65 ([tests/](file:///c:/Users/grzes/Documents/Projects/jabberwocky/tests/))

- [tests/test_labirynt_builder.py](file:///c:/Users/grzes/Documents/Projects/jabberwocky/tests/test_labirynt_builder.py): aktualizacja asercji na obecność `screens_obj_count`, `screens_codes_lo/hi` zamiast `screens_vram_lo/hi`.
- [tests/test_scrolling.py](file:///c:/Users/grzes/Documents/Projects/jabberwocky/tests/test_scrolling.py): testy przewijania weryfikujące strumieniowanie z bufora stagingowego.
- [tests/test_secret_collision.py](file:///c:/Users/grzes/Documents/Projects/jabberwocky/tests/test_secret_collision.py): testy zbierania sekretów i ich automatycznego odtwarzania przy nowej grze.

---

## Plan weryfikacji

### Testy automatyczne
1. Kompilacja całego projektu i asercje poprawności:
   ```bash
   make all
   ```
2. Uruchomienie pełnego zestawu testów jednostkowych i emulacji py65:
   ```bash
   make test
   ```
3. Weryfikacja mapy pamięci (`docs/memory_map.txt`):
   - Upewnienie się, że `WORLD_DATA` skurczyło się do ~2-3 KB.
   - Upewnienie się, że wolna pamięć RAM wynosi > 18 KB.

### Testy działania w emulatorze
- `make run` (Altirra):
  - Sprawdzenie płynności przewijania ekranów.
  - Sprawdzenie ziania ogniem i niszczenia obiektów.
  - Sprawdzenie zbierania sekretów i przechodzenia między ekranami labiryntu.
