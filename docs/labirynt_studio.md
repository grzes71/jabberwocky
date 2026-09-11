# Labirynt Studio — Podręcznik Użytkownika i Dokumentacja Techniczna

**Labirynt Studio** to desktopowe narzędzie deweloperskie w Pythonie (PySide6) zaprojektowane specjalnie dla projektu gry **Jabberwocky** na platformę Atari 8-bit (XL/XE).

Aplikacja służy do:
1. Projektowania pojedynczych ekranów gry o rozdzielczości **40 × 11 znaków** (320 × 88 pikseli w natywnych zegarach Atari).
2. Rozmieszczania obiektów w oparciu o sztywną siatkę **2 × 2 znaki** ze sprzętowym snapem.
3. Wiernego podglądu grafiki w trybie rastrowym Atari ANTIC Mode 4 (kolory z `colors.yaml`, glify z `game.fnt`).
4. Składania nieliniowych labiryntów z wcześniej przygotowanych ekranów.
5. Walidacji granic ekranu, kolizji blokujących oraz spójności kodów.
6. Zapisywania i odczytywania projektów w formacie YAML (ze ścieżkami względnymi i kompaktową reprezentacją instancji).
7. Eksportu do binarnego formatu poziomów (`LEVEL.BIN`).

---

## 1. Jak uruchomić aplikację

Aplikację można uruchomić z poziomu środowiska wirtualnego Python w katalogu głównym projektu:

```bash
# Uruchomienie domyślne (wczytuje world/objects.yaml, world/colors.yaml, fonts/game.fnt)
.\.venv\Scripts\python.exe -m labirynt_studio.main

# Uruchomienie z jawnymi ścieżkami do zasobów
.\.venv\Scripts\python.exe -m labirynt_studio.main --objects world/objects.yaml --colors world/colors.yaml --charset fonts/game.fnt

# Uruchomienie z otwarciem zapisanego projektu
.\.venv\Scripts\python.exe -m labirynt_studio.main --project moj_projekt.yaml
```

W przypadku braku któregokolwiek z plików zasobów aplikacja nie przerywa działania błędem traceback, lecz wyświetla okno konfiguracji ścieżek (`ResourceDialog`).

---

## 2. Jak wczytać zasoby

1. W menu głównym wybierz **Plik -> Konfiguruj zasoby...**.
2. W oknie dialogowym wskaż:
   - Plik definicji obiektów (`world/objects.yaml`),
   - Plik palety kolorów Atari (`world/colors.yaml`),
   - Plik charsetu Atari (`fonts/game.fnt`).
3. Po zatwierdzeniu przyciskiem **OK** paleta obiektów, kolory oraz płótno edytora zostaną natychmiast odświeżone.

---

## 3. Jak tworzyć i edytować ekrany

### Tworzenie ekranu
1. W prawym górnym panelu **Ekrany** kliknij przycisk **Nowy**.
2. Wpisz unikalny identyfikator (np. `FOREST_01`, `CAVE_02`).
3. Nowy ekran zostanie dodany do biblioteki i załadowany na płótnie.

### Umieszczanie obiektów
1. W lewym panelu **Obiekty** wyszukaj interesujący obiekt (możesz filtrować po tagach, np. `drzewo`, `woda`, lub wpisać nazwę/kod w wyszukiwarce).
2. Kliknij wybrany obiekt na liście — w dolnej części panelu pojawi się jego podgląd rastrowy, kod, rozmiar i flagi.
3. Najedź kursorem myszy na płótno — zobaczysz półprzezroczystego "duszka" (ghost) snapującego do siatki 2×2. Zielona ramka oznacza, że obiekt mieści się na ekranie, czerwona — że przekracza granice.
4. Kliknij **Lewy Przycisk Myszy (LPM)**, aby umieścić obiekt.

### Zaznaczanie, przesuwanie i usuwanie
* Aby zaznaczyć istniejący obiekt, odznacz aktywny pędzel klawiszem **Esc** lub kliknij inny element, a następnie kliknij LPM na obiekt na płótnie.
* Zaznaczony obiekt możesz przeciągać myszą (z automatycznym przyciąganiem do siatki 2×2).
* Aby usunąć obiekt, kliknij na niego **Prawym Przyciskiem Myszy (PPM)** lub zaznacz go i naciśnij klawisz **Delete** / **Backspace**.

### Skróty klawiaturowe
* `Ctrl+Z` — Cofnij (Undo)
* `Ctrl+Y` / `Ctrl+Shift+Z` — Ponów (Redo)
* `Ctrl+C` — Kopiuj zaznaczony obiekt
* `Ctrl+V` — Wklej obiekt (w pozycji kursora)
* `Delete` — Usuń zaznaczony obiekt
* `Esc` — Anuluj zaznaczenie / odznacz aktywny obiekt

### Tryby widoku: DESIGN vs ATARI
* **DESIGN**: Wyświetla pomocniczą siatkę 2×2 znaki, obramowania obiektów, zaznaczenia oraz podgląd duszka przy najechaniu.
* **ATARI**: Pokazuje wierny, końcowy obraz rastrowy piksel-w-piksel z autentycznym charsetem i kolorami, bez żadnych linii pomocniczych.
* Zmiana powiększenia (Zoom): 2× (640×176), 3× (960×264), 4× (1280×352), 6× (1920×528).

---

## 4. Jak tworzyć labirynty

Labirynty w Labirynt Studio nie muszą być liniowe — reprezentują logiczne zbiory ekranów tworzące poziomy gry.

1. W prawym dolnym panelu **Labirynty** kliknij **Nowy**.
2. Podaj unikalny identyfikator (np. `LEVEL_01`) oraz opcjonalną nazwę opisową (np. `Ciemny Las`).
3. Zaznacz nowo utworzony labirynt na liście.
4. Użyj przycisku **+ Ekran**, aby dodać do labiryntu zaprojektowane wcześniej ekrany z biblioteki.
5. Kolejność ekranów można modyfikować przyciskami **▲** oraz **▼**, a usuwać przyciskiem **- Ekran**.
6. Podwójne kliknięcie na ekran na liście labiryntu natychmiast otwiera go do edycji na płótnie.

---

## 5. Format pliku projektu `project.yaml`

Projekt zapisywany jest w kompaktowym formacie YAML ze ścieżkami względnymi do zasobów:

```yaml
project:
  name: Jabberwocky

resources:
  objects: world/objects.yaml
  colors: world/colors.yaml
  charset: fonts/game.fnt

screens:
  - id: FOREST_01
    objects:
      - code: 4
        packed_xy: 0
      - code: 3
        packed_xy: 179

  - id: FOREST_02
    objects:
      - code: 4
        packed_xy: 35

labyrinths:
  - id: LEVEL_01
    name: "The Forest"
    screens:
      - FOREST_01
      - FOREST_02
```

W projekcie **nie duplikuje się** danych definicyjnych obiektów (nazw, rozmiaru, flag, kafli). Instancja na ekranie to wyłącznie para: `code` oraz `packed_xy`.

---

## 6. Jak działa format pozycji `packed_xy`

Każda instancja obiektu na ekranie reprezentowana jest przez dokładnie **2 bajty**:
* **Bajt 1: `code`** — 8-bitowy kod typu obiektu (0..255).
* **Bajt 2: `packed_xy`** — skompresowane współrzędne ekranowe.

### Siatka współrzędnych
Ekran ma geometrię **40 znaków szerokości × 11 znaków wysokości**.
Obiekty snapują do siatki co 2 znaki w poziomie i 2 znaki w pionie:
* `x` przyjmuje wartości: `0, 2, 4, ..., 38` (20 kolumn: `x_half = 0..19`).
* `y` przyjmuje wartości: `0, 2, 4, ..., 10` (6 wierszy: `y_half = 0..5`).

Razem istnieje dokładnie **20 × 6 = 120** dozwolonych pozycji bazowych.

### Pakowanie współrzędnych
* `x_half = x // 2` (zajmuje 5 bitów: wartości 0..31, maska `0x1F`)
* `y_half = y // 2` (zajmuje 3 bity: wartości 0..7, przesunięcie o 5 bitów w lewo)

$$packed\_xy = (y\_half \ll 5) \mid x\_half$$

Układ bitów w bajcie `packed_xy`:
```text
Bit 7  6  5 | 4  3  2  1  0
    Y_HALF   |    X_HALF
```

### Dekodowanie współrzędnych
$$x = (packed\_xy \ \& \ 0x1F) \ll 1$$
$$y = (packed\_xy \gg 5) \ll 1$$

### Przykłady skrajne:
* $(x=0, y=0) \rightarrow x_{half}=0, y_{half}=0 \rightarrow packed\_xy = 0$
* $(x=38, y=0) \rightarrow x_{half}=19, y_{half}=0 \rightarrow packed\_xy = 19$
* $(x=0, y=10) \rightarrow x_{half}=0, y_{half}=5 \rightarrow packed\_xy = 160$
* $(x=38, y=10) \rightarrow x_{half}=19, y_{half}=5 \rightarrow packed\_xy = 179$

---

## 7. Jak dodać nowy obiekt do `objects.yaml`

Plik `world/objects.yaml` jest Single Source of Truth (SSOT) dla definicji obiektów gry.

Aby dodać nowy obiekt, dopisz wpis w sekcji `objects:` w `world/objects.yaml`:

```yaml
- object: STONE_PILLAR
  id: STONE_PILLAR
  code: 85
  size:
    width: 2
    height: 4
  flags:
    blocking: true
    interactive: false
    secret: false
  tiles: [60, 61, 62, 63, 70, 71, 72, 73]
  tags: [skała, infrastruktura]
```

### Zasady:
1. `code`: Unikalna 8-bitowa liczba całkowita (1..255).
2. `size`: Rozmiar w znakach (`width` i `height`). Zalecane wielokrotności 2 (np. 2×2, 4×2, 2×4).
3. `tiles`: Lista numerów glifów z charsetu Atari (0..255) wiersz po wierszu. Liczba kafli musi być równa $width \times height$.
4. `flags`:
   - `blocking`: czy obiekt blokuje ruch (kolizja wykrywana przez walidator),
   - `interactive`: czy obiekt wchodzi w interakcję,
   - `secret`: czy obiekt maskuje sekretne przejście.
5. `tags`: Lista tagów używana do filtrowania w Labirynt Studio. Nowe tagi można dopisać również do nagłówka `tags:` na początku pliku.
