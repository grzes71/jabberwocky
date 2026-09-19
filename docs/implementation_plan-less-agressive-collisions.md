# Plan: Mniej agresywne sprawdzanie kolizji ze ścianami i przeszkodami (1-klatkowe opóźnienie)

## Opis problemu i cel
Obecnie kolizje sprzętowe GTIA Player 0 (smok) z polem gry PF0–PF2 (`dragon_p0pf & $07 != 0`) są rozpatrywane natychmiastowo w bieżącej klatce:
1. Odczyt rejestru `P0PF` w przerwaniu DLI.
2. W procedurze VBLANK `check_dragon_collisions` następuje natychmiastowe wywołanie `check_dragon_blocking_collision`.
3. Jeśli w danej linii Mode 5 występuje kafel blokujący (`blocking: true`), smok natychmiast wchodzi w stan śmierci/kraksy (`start_dragon_crash`).

Powoduje to, że nawet minimalne, jednoklatkowe muśnięcie krawędzi przeszkody lub pojedynczego piksela w ciasnym przejściu natychmiast uśmierca gracza.

Celem jest wprowadzenie **1-klatkowego bufora/opóźnienia (debouncingu)** dla kolizji ze ścianami i przeszkodami blokującymi:
- **Klatka N (pierwsze zgłoszenie kolizji)**: Rejestrujemy zdarzenie (ustawienie flagi `dragon_hit_pending = 1`), pobieramy ewentualne sekrety (`check_dragon_secret_collision`), ale **nie uruchamiamy** jeszcze testu zderzenia ani procedury kraksy.
- **Klatka N+1 (potwierdzenie kolizji)**:
  - Jeśli kolizja z PF0–PF2 **nadal występuje** (`dragon_p0pf & $07 != 0`) i flaga `dragon_hit_pending` jest aktywna: uruchamiamy `check_dragon_blocking_collision` i w razie zderzenia niszczymy smoka.
  - Jeśli w klatce N+1 **brak kolizji** (`dragon_p0pf & $07 == 0`): resetujemy flagę `dragon_hit_pending = 0`. Gracz uniknął zderzenia (chwilowe muśnięcie zostało wybaczone).

---

## Szczegóły techniczne i decyzje projektowe

### 1. Zbieranie sekretów (`check_dragon_secret_collision`)
Sekrety i obiekty interaktywne również są rysowane na warstwach PF0–PF2, ale ich zbieranie jest nagradzające (punkty, strzały, życie) i nie niszczy smoka. Zbieranie sekretów pozostanie **natychmiastowe** (już w pierwszej klatce kontaktu), aby gracz lecący z pełną prędkością nie ominął bonusu.

### 2. Doładowanie energii PF3 (`check_pf3`)
Ładowanie energii z niebieskich kryształów (kolor PF3, bit 3) nie jest kolizją śmiertelną i nadal będzie działać płynnie co klatkę.

### 3. Nowa zmienna stanu: `dragon_hit_pending`
Dodanie w [scenes/game.asm](file:///c:/Users/grzes/Documents/Projects/jabberwocky/scenes/game.asm):
```asm
dragon_hit_pending  dta 0           ; 0 = brak oczekującej kolizji, 1 = kolizja wystąpiła w poprzedniej klatce
```
Zmienna będzie resetowana do 0:
- Gdy brak kolizji w bieżącej klatce (`dragon_p0pf & $07 == 0`),
- Po rozpoczęciu sekwencji kraksy (`start_dragon_crash`),
- Podczas inicjalizacji gry (`init_game`),
- Podczas respawnu smoka i restartu poziomu (`restart_level_after_death`, `advance_to_next_level`).

---

## Proponowane zmiany

### [scenes/game.asm](file:///c:/Users/grzes/Documents/Projects/jabberwocky/scenes/game.asm)
- Dodanie deklaracji zmiennej `dragon_hit_pending dta 0`.
- Wyzerowanie `dragon_hit_pending` we wszystkich procedurach inicjalizujących stan smoka (linie ~207, ~1860, ~2922).
- Modyfikacja `check_dragon_collisions`:
  - Gdy `ZP_TMP & $07 == 0`: wyzerowanie `dragon_hit_pending`, przejście do `@check_pf3`.
  - Gdy `ZP_TMP & $07 != 0`:
    - Wywołanie `check_dragon_secret_collision`.
    - Sprawdzenie `dragon_hit_pending`:
      - Jeśli `0`: ustawienie `dragon_hit_pending = 1` i przejście do `@check_pf3` (brak testu kraksy w tej klatce).
      - Jeśli `!= 0`: kolizja potwierdzona w kolejnej klatce -> wywołanie `check_dragon_blocking_collision`. Jeśli kolizja z przeszkodą blokującą, zerowanie `dragon_hit_pending` i wywołanie `start_dragon_crash`.

### Testy jednostkowe ([tests/](file:///c:/Users/grzes/Documents/Projects/jabberwocky/tests/))
- Aktualizacja istniejących testów w [tests/test_status_bar.py](file:///c:/Users/grzes/Documents/Projects/jabberwocky/tests/test_status_bar.py) oraz [tests/test_flame_collision.py](file:///c:/Users/grzes/Documents/Projects/jabberwocky/tests/test_flame_collision.py):
  - Dostosowanie testów bezpośrednio wywołujących `CHECK_DRAGON_COLLISIONS`, aby symulowały drugą klatkę lub wywoływały procedurę dwukrotnie.
- Dodanie dedykowanych testów weryfikujących debouncing kolizji:
  - **Pojedyncza klatka muśnięcia**: Klatka 1 z kolizją (`dragon_hit_pending` staje się 1, brak kraksy), Klatka 2 bez kolizji (`dragon_hit_pending` staje się 0, brak kraksy).
  - **Dwie kolejne klatki kolizji**: Klatka 1 z kolizją, Klatka 2 z kolizją -> następuje kraksa (`dragon_dying == 3`).
  - **Zbieranie sekretów**: Następuje już w pierwszej klatce kontaktu.

---

## Plan weryfikacji

### Testy automatyczne
1. `make all` — weryfikacja czystej kompilacji (MADS), generowania assetów i mapy pamięci (`scripts/generate_memory_map.py`).
2. `.venv/Scripts/python.exe -m pytest tests -v` — uruchomienie pełnego zestawu testów jednostkowych py65 (wszystkie 166+ testów musi zakończyć się sukcesem).
