# Jabberwocky — Atari 8-bit (XL/XE)

Projekt gry/dema na komputery **Atari 800XL / 65XE** (procesor 6502, układy ANTIC, GTIA, POKEY) inspirowany poematem Lewisa Carrolla *"Jabberwocky"* (w polskim przekładzie Stanisława Barańczaka jako *"Żabrołak"*).

Projekt łączy tradycyjne programowanie w asemblerze 6502 (MADS) z nowoczesnym zautomatyzowanym potokiem budowania (Python 3, Pydantic, PySide6, pytest, py65) oraz zintegrowanym środowiskiem edytorów GUI do tworzenia sprajtów, obiektów gry i labiryntów.

---

## Spis treści

- [Główne cechy](#główne-cechy)
- [Architektura silnika](#architektura-silnika)
- [Struktura projektu](#struktura-projektu)
- [Wymagania i narzędzia](#wymagania-i-narzędzia)
- [Instalacja i kompilacja](#instalacja-i-kompilacja)
- [Narzędzia wspomagające](#narzędzia-wspomagające)
  - [Labirynt Studio (Edytor ekranów i labiryntów)](#labirynt-studio-edytor-ekranów-i-labiryntów)
  - [Object Studio (Katalog obiektów gry)](#object-studio-katalog-obiektów-gry)
  - [Sprite Studio (Edytor grafiki PMG)](#sprite-studio-edytor-grafiki-pmg)
  - [Labirynt Builder (Kompilator świata)](#labirynt-builder-kompilator-świata)
  - [Memory Map Generator & Validator](#memory-map-generator--validator)
  - [Image Converter](#image-converter)
- [Mapa pamięci](#mapa-pamięci)
- [Testy](#testy)

---

## Główne cechy

- **Klasyczny target 6502**: Kod zoptymalizowany pod architekturę Atari XL/XE z zachowaniem oficjalnego zestawu instrukcji MOS 6502 oraz ścisłych reguł taktowania cykli i stron pamięci.
- **Wielostanowa maszyna stanów**:
  - `STATE_INTRO`: Scena narracyjna z poematem, polską czcionką i gradientami DLI (wyświetlana jednorazowo przy uruchomieniu gry, po czym następuje przejście do ekranu tytułowego).
  - `STATE_TITLE`: Główny ekran tytułowy w wysokiej rozdzielczości bitmapowej ze sprzętowym scroll-tickerem; naciśnięcie FIRE uruchamia bezpośrednio rozgrywkę.
  - `STATE_GAME`: Główny ekran rozgrywki z animowaną postacią smoka, zianiem ogniem, inercją i płynnym przewijaniem świata.
  - `STATE_GAME_OVER`: Ekran zakończenia obsługujący porażkę (utrata żyć, wyczerpanie energii smoka) oraz stan **VICTORY** po ukończeniu wszystkich poziomów; naciśnięcie FIRE wraca bezpośrednio do `STATE_TITLE` (scena intro nie jest ponownie wyświetlana).
- **Zaawansowane wykorzystanie ANTIC & GTIA**:
  - **Tryb ANTIC F** (320×175, 1 bpp) na ekranie tytułowym z podziałem LMS (Load Memory Scan) omijającym granicę 4 KB bufora ekranu.
  - **Tryb ANTIC 2** (40×24 znakowy) w scenie Intro z przerwaniami **DLI (Display List Interrupt)** dynamicznie modyfikującymi rejestry koloru tekstu w locie linii rastra.
  - **Hybrydowy Display List** w grze: 1 linia ANTIC 2 (pasek energii) + 11 linii w podwójnie wysokim trybie **ANTIC 5** (pole akcji) + 1 linia ANTIC 2 (dolny pasek: LEVEL, SCORE, LIVES, SHOTS).
  - **Sprzętowe płynne przewijanie (ANTIC HSCROL)**: Płynny sub-pixelowy fine scroll co 1 zegar koloru z rejestrem `HSCROL` ($D404) oraz 48-bajtową geometrią wierszy (4 kolumny marginesu lewego, 40 kolumn widocznych, 4 kolumny bufora wyprzedzającego).
  - **Podwójne buforowanie VRAM (Double Buffering)**: Dwa niezależne bufory akcji (`GAME_ACTION_VRAM` $6000 oraz `GAME_ACTION_VRAM_B` $6400). Przełączanie wskaźnika LMS Display Listy (`dlist_game_action_lms + 2`) odbywa się bezpiecznie w NMI VBLANK, gwarantując brak tearingu i zacięć obrazu.
- **Płynność i strumieniowanie świata**:
  - **Odroczone wypiekanie ekranu (Deferred Screen Baking)**: Wypiekanie nowych kolumn i obiektów (`bake_pending`, `execute_pending_bake`) rozłożone w czasie poza krytycznymi klatkami przesunięcia zgrubnego (coarse scroll), gwarantując stabilne 50/60 FPS bez szarpnięć.
  - Płynne wstrzykiwanie kolejnych ekranów zdefiniowanych w labiryncie kolumna po kolumnie.
  - Ogon wygaszający (tail mode) po ostatnim ekranie poziomu i automatyczne przejście do kolejnego labiryntu z nakładką nazwy (`engine/level_name.asm`).
- **Animacja i fizyka sprajtów PMG (Player/Missile Graphics)**:
  - Wieloklatkowy sprajt smoka Jabberwocky (Player 0) z akumulatorem fazy 16-bit (format 8.8) zapewniającym płynne machanie skrzydłami skorelowane z prędkością lotu.
  - Fizyka ruchu pionowego i poziomego w arytmetyce stałoprzecinkowej (prędkość, akceleracja, hamowanie, inercja).
  - Zianie ogniem oparte na pociskach PMG (tryb 5th player, `GPRIOR = $11`, `COLPF3`), 8-klatkowa animacja rozszerzania i zwijania jęzora ognia z dedykowanymi efektami dźwiękowymi POKEY.
  - Pasek energii smoka ze stałoprzecinkowym przelicznikiem Bresenhama, automatyczną detekcją PAL/NTSC i zabezpieczeniem przed wyczerpaniem tuż po respawnie.
  - Dwufazowa sekwencja śmierci smoka (zanik luminancji + przesunięcie w lewo, eksplozja POKEY).
- **Interakcja ze światem i detekcja kolizji**:
  - Szybka detekcja kolizji blokujących $O(1)$ smoka z terenem w oparciu o siatkę `BLOCKING_VRAM` ($6350).
  - Niszczenie kruchych przeszkód zianiem ognia (`check_flame_object_collision`) z aktualizacją kafli w VRAM i siatce blokowania oraz punktacją.
  - Zbieranie sekretów i znajdziek (`check_dragon_secret_collision`) ze śledzeniem zebranych obiektów w maskach bitowych (`screen_obj_destroyed`) dla każdego ekranu oraz sygnałem dźwiękowym POKEY.
- **Dynamiczne zestawy znaków i audio**:
  - Animowane kafle otoczenia (woda/lawa) przełączane w locie rastra z generatora JSON (`chars/animated.json`).
  - Podsystem audio POKEY (`engine/sound.asm`): efekty ziania ogniem, trzepotu skrzydeł, uderzenia w przeszkodę, wybuchu i zebrania sekretu.
- **Automatyczny Single Source of Truth (SSOT)**:
  - Definicje poziomów (`world/project.yaml`), obiektów (`world/objects.yaml`) i palet (`world/colors.yaml`) kompilowane skryptem Pythona do struktur asemblerowych SoA (Structure-of-Arrays).
  - Weryfikator pamięci sprawdzający kolizje segmentów i granice Zero Page w trakcie każdego `make`.

---

## Architektura silnika
 
```
       [ main.asm ]
            │
    ┌───────┴───────┐
    │  State Engine │ (Pętla główna zsynchronizowana z VBLANK RTCLOK)
    └───────┬───────┘
            ├── 1. STARTUP      --> scenes/intro.asm     (ANTIC Mode 2 + DLI, jednorazowo)
            ├── 2. STATE_TITLE  --> scenes/title.asm     (ANTIC Mode F + Mode 2 scroll)
            ├── 3. STATE_GAME   --> scenes/game.asm      (ANTIC 5 HSCROL + ANTIC 2 + PMG)
            └── 4. GAME_OVER    --> scenes/gameover.asm  (Powrót do STATE_TITLE)
```

Główna pętla gry działa w sposób deterministyczny w oparciu o synchronizację pionową (`RTCLOK`):
1. **Input Poll** (`update_input`): Odczyt joysticka/przycisku Fire z detekcją zbocza opadającego.
2. **State Dispatcher** (`dispatch_state`): Obsługa przejść stanów (`*_init`) oraz klatki logiki (`*_run`: fizyka smoka, zianie ogniem, odroczone wypiekanie kafelków `execute_pending_bake`).
3. **Detekcja kolizji i zbieranie**: Obsługa kolizji z terenem (`check_dragon_blocking_collision`), niszczenia obiektów ogniem (`check_flame_object_collision`) i sekretów (`check_dragon_secret_collision`).
4. **VBLANK NMI** (`vblank_game`): Bezpieczne przełączanie wskaźników LMS podwójnego bufora VRAM (`dlist_game_action_lms + 2`), aktualizacja sprzętowego rejestru `HSCROL`, tyknięcia podsystemu audio POKEY oraz animacja paska energii.

---

## Struktura projektu

```
jabberwocky/
├── main.asm                 # Główny punkt wejścia, wektory RUNAD, pętla i Display Listy
├── hardware.asm             # Adresy rejestrów ANTIC, GTIA, POKEY, PIA i OS
├── zeropage.asm             # Alokacja zmiennych strony zerowej ($80-$89)
├── Makefile                 # Reguły budowania, weryfikacji i uruchamiania
├── requirements.txt         # Zależności narzędzi w Pythonie
│
├── engine/                  # Podsystemy silnika gry (6502 ASM)
│   ├── flame_collision.asm  # Detekcja kolizji ognia i smoka (przeszkody, sekrety)
│   ├── level_name.asm       # Nakładka graficzna nazwy poziomu
│   ├── charset_anim.asm     # Silnik animacji zestawu znaków w VRAM
│   └── sound.asm            # Generator efektów dźwiękowych POKEY
│
├── scenes/                  # Moduły poszczególnych scen (6502 ASM)
│   ├── title.asm            # Ekran tytułowy
│   ├── intro.asm            # Wprowadzenie i wyświetlanie wiersza (DLI)
│   ├── game.asm             # Logika gry, fizyka PMG, HSCROL, podwójne buforowanie i streaming
│   ├── gameover.asm         # Ekran końca gry (Porażka / Sukces)
│   └── text_utils.asm       # Procedury wypisywania i konwersji znaków ATASCII/Internal
│
├── world/                   # Źródłowe definicje świata gry (SSOT)
│   ├── project.yaml         # Definicje ekranów i labiryntów (poziomów)
│   ├── objects.yaml         # Katalog obiektów gry (rozmiary 2x2, flagi, punkty)
│   └── colors.yaml          # Palety kolorów Atari (ANTIC Mode 5)
│
├── chars/                   # Konfiguracje obrotu i animacji znaków
│   ├── animated.json        # Definicje klatek animacji znaków
│   └── rotated.json         # Definicje wariantów obróconych kafli
│
├── labirynt_studio/         # Narzędzie GUI (PySide6) do projektowania ekranów i labiryntów
├── object_studio/           # Narzędzie GUI (PySide6) do edycji katalogu obiektów
├── sprite_studio/           # Narzędzie GUI (PySide6) do edycji sprajtów PMG
│
├── scripts/                 # Narzędzia potoku budowania (Python)
│   ├── labirynt_builder.py  # Kompilator world/project.yaml do gen/world_data.asm i tiles
│   ├── compile_sprites.py   # Kompilator definicji JSON sprajtów do MADS ASM
│   ├── compile_texts.py     # Kompilator tekstów narracyjnych
│   ├── convert_image.py     # Konwerter grafik (ANTIC Mode F)
│   ├── gen_animated_charset.py # Generator tablic animacji zestawu znaków
│   ├── gen_rotated_charset.py  # Generator wariantów obróconych znaków
│   └── generate_memory_map.py  # Analizator symboli MADS i walidator pamięci
│
├── sprites/                 # Źródłowe definicje sprajtów (JSON)
├── fonts/                   # Zestawy czcionek Atari (1024 bajty)
│   ├── text.fnt             # Czcionka tekstowa z polskimi diakrytykami
│   └── game.fnt             # Zestaw znaków kafli pola gry (ANTIC Mode 4/5)
├── texts/                   # Teksty źródłowe scen
├── img/                     # Źródłowe pliki graficzne
├── docs/                    # Dokumentacja i generowane raporty pamięci
│   ├── memory_map.txt       # Czytelne podsumowanie mapy pamięci i wolnej przestrzeni
│   └── memory_map.json      # Maszynowy model alokacji segmentów
├── tests/                   # Zestaw 132 testów jednostkowych i emulacyjnych py65 (pytest)
└── gen/                     # Pliki generowane automatycznie (nie edytować!)
```

---

## Wymagania i narzędzia

Do zbudowania projektu i uruchomienia narzędzi potrzebne są:

1. **Asembler MADS**: [Mad-Assembler](http://mads.atari8.info/) w wersji 2.1.6 lub nowszej.
2. **Emulator Atari**: [Altirra](https://www.virtualdub.org/altirra.html) (lub inny emulator Atari 8-bit obsługujący pliki `.xex`).
3. **Python**: Wersja 3.10 lub nowsza.
4. **GNU Make**: W środowisku Windows (np. z Git Bash, MSYS2 lub MinGW) lub Linux/macOS.

---

## Instalacja i kompilacja

### 1. Przygotowanie środowiska Python

```bash
# Utworzenie wirtualnego środowiska
python -m venv .venv

# Aktywacja środowiska (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Aktywacja środowiska (Linux/macOS)
source .venv/bin/activate

# Instalacja zależności
pip install -r requirements.txt
```

### 2. Konfiguracja ścieżek

W pliku `Makefile` zdefiniowane są domyślne ścieżki do asemblera i emulatora:
```makefile
MADS    ?= c:/Apps/Mad-Assembler-2.1.6/bin/windows_x86_64/mads.exe
ALTIRRA ?= C:/Apps/Altirra-4.40/Altirra64.exe
```
Możesz je dostosować w pliku `Makefile` lub przekazać jako zmienne środowiskowe / argumenty wywołania `make`.

### 3. Cele `make`

| Polecenie | Opis |
| :--- | :--- |
| `make` / `make all` | Buduje zasoby, kompiluje świat gry, asembluje `jabberwocky.xex`, odpala testy i weryfikuje mapę pamięci |
| `make assets` | Konwertuje grafiki, teksty i sprajty |
| `make data` | Kompiluje `world/project.yaml`, `world/objects.yaml` oraz `world/colors.yaml` do `gen/world_data.asm` |
| `make xex` | Buduje sam plik binarny `jabberwocky.xex` |
| `make check_memory` | Generuje raport pamięci `docs/memory_map.txt` oraz `docs/memory_map.json` |
| `make test` | Uruchamia pełny zestaw testów `pytest` (w tym emulację py65) |
| `make run` | Buduje projekt i uruchamia go w emulatorze Altirra |
| `make clean` | Usuwa pliki binarne oraz katalog `gen/` |
| `make help` | Wyświetla listę dostępnych celów |

---

## Narzędzia wspomagające

### Labirynt Studio (Edytor ekranów i labiryntów)
Aplikacja desktopowa napisana w **PySide6** dedykowana do projektowania poziomów w trybie ANTIC Mode 5:
- Wizualizacja siatki 40×11 znaków w proporcjach pikseli Atari (Pixel Aspect Ratio 2:1).
- Układanie obiektów na siatce 2×2 znaki metodą Drag & Drop.
- Podgląd rzeczywistej palety kolorów z `world/colors.yaml` oraz fontu `fonts/game.fnt`.
- Zarządzanie ekranami oraz sekwencjami labiryntów z walidacją spójności.
- Bezpośredni zapis i odczyt formatu `world/project.yaml`.

Uruchomienie:
```bash
python -m labirynt_studio.main
```

### Object Studio (Katalog obiektów gry)
Narzędzie GUI do definiowania obiektów gry umieszczanych w labiryntach:
- Konfiguracja wymiarów w siatce 2×2 znaki, kodów kafli z zestawu znaków oraz flag fizyki (np. kolizyjne, zniszczalne, znajdźki).
- Podgląd wyglądu obiektu w czasie rzeczywistym.
- Zapis do pliku `world/objects.yaml`.

Uruchomienie:
```bash
python -m object_studio.main
```

### Sprite Studio (Edytor grafiki PMG)
Aplikacja desktopowa w PySide6 do projektowania wieloklatkowych sprajtów PMG Atari:
- Siatka edycyjna z podglądem pikseli PMG (pojedyncza i podwójna szerokość).
- Obsługa wielu klatek animacji z kontrolą czasu trwania i podglądem na żywo.
- Eksport do formatu JSON kompilowanego przez `scripts/compile_sprites.py`.

Uruchomienie:
```bash
python -m sprite_studio.main
```

### Labirynt Builder (Kompilator świata)
Skrypt `scripts/labirynt_builder.py` automatycznie wywoływany przez `make data`:
- Parsuje `world/project.yaml`, `world/objects.yaml` oraz `world/colors.yaml`.
- Eksportuje definicje palety ekranu akcji (`world_color_bk`, `world_color_pf0`..`pf3`) z dziesiętnych wartości Atari podanych w `colors.yaml`.
- Wypieka 440-bajtowe bufory znakowe VRAM każdego ekranu.
- Generuje tablice SoA (Structure-of-Arrays) z kodami obiektów, spakowanymi współrzędnymi 2×2 oraz katalogiem labiryntów do `gen/world_data.asm`.
- Generuje tablice definicji kafli składowych obiektów do szybkiego wyszukiwania kolizyjnego w `gen/world_obj_tiles.asm`.

### Charset Anim & Rotate Generators
Skrypty `scripts/gen_animated_charset.py` oraz `scripts/gen_rotated_charset.py`:
- Generują klatki animowanych kafli w locie rastra na podstawie `chars/animated.json` do `gen/animated_chars.asm`.
- Przygotowują warianty obróconych kafli z `chars/rotated.json` do `gen/rotated_chars_*.asm`.

### Memory Map Generator & Validator
Skrypt `scripts/generate_memory_map.py` integruje się bezpośrednio z procesem asemblacji:
- Analizuje pliki symboli (`.lab`) i listingu (`.lst`) generowane przez MADS.
- Wykrywa nakładanie się segmentów kodu, tablic danych i buforów ekranu.
- Pilnuje restrykcji sprzętowych:
  - Zakaz alokacji zmiennych użytkownika w systemowej stronie zerowej OS (`$00`-`$7F`).
  - Zakaz naruszania pamięci OS ROM i rejestrów I/O (`$C000`-`$DFFF`).
- Przy wykryciu kolizji przerywa proces `make` z kodem błędu > 0.

### Image Converter
Skrypt `scripts/convert_image.py` wykorzystuje bibliotekę `atari-image-converter` do przygotowania 1-bitowej bitmapy dla trybu ANTIC F (320×175 pikseli), dopasowując układ danych bezpośrednio do Display Listy silnika.

---

## Mapa pamięci

Projekt zachowuje pełną izolację pamięci OS oraz precyzyjną alokację buforów:

| Zakres adresów | Rozmiar | Przeznaczenie |
| :--- | :--- | :--- |
| `$80` – `$89` | 10 B | Zmienne strony zerowej (`PTR_SRC`, `PTR_DST`, `ZP_TMP`, `PTR_BLK`, `PTR_COLL`) |
| `$8A` – `$FF` | 118 B | **Wolna strona zerowa** |
| `$0800` – `$080A` | 11 B | Wektor skoku inicjalizacyjnego (`CODE`) |
| `$080B` – `$1FA9` | ~6.0 KB | Podsystemy silnika (`engine/`: audio, kolizje, animacje kafli, nazwa poziomu) |
| `$1FAA` – `$27FF` | ~2.1 KB | **Wolna pamięć RAM** (w tym bufor PMG `$2000`–`$27FF`) |
| `$2800` – `$3E7D` | ~5.8 KB | Segment głównego kodu i logiki gry (`main.asm`, `scenes/`, fizyka smoka) |
| `$4000` – `$5B67` | ~7.0 KB | Bufor grafiki tytułowej VRAM (ANTIC Mode F, 320×175) |
| `$5C00` – `$5FFF` | 1024 B | Bufor czcionki tekstowej (`text.fnt`, wyrównany do 1 KB) |
| `$6000` – `$620F` | 528 B | Główny bufor pola akcji VRAM A (11 linii ANTIC 5 z HSCROL, 48 B/wiersz) |
| `$6300` – `$634F` | 80 B | Bufor paska statusu w grze (2 linie ANTIC 2) |
| `$6350` – `$63F7` | 168 B | Bufor siatki kolizji blokujących `BLOCKING_VRAM` (21×8 bajtów) |
| `$6400` – `$660F` | 528 B | Zapasowy bufor pola akcji VRAM B do podwójnego buforowania (Double Buffering) |
| `$6610` – `$674B` | 316 B | Segment Display List dla wszystkich scen (wyrównany do granicy 1 KB) |
| `$6800` – `$85C4` | ~7.6 KB | Czcionka gry (`game.fnt`), animowane kafle oraz dane świata (`gen/world_data.asm`) |
| `$8800` – `$8BBF` | 960 B | Bufor tekstu dla trybów znakowych ANTIC 2 (Intro, Game Over) |
| `$8BC0` – `$BFFF` | ~13.1 KB | **Wolna pamięć RAM** (dostępna na kolejne etapy i poziomy gry) |
| `$C000` – `$DFFF` | — | **Naruszenie zabronione** (OS ROM / Rejestry sprzętowe I/O) |

Szczegółowy i zawsze aktualny raport generowany jest po każdej kompilacji w pliku [docs/memory_map.txt](docs/memory_map.txt).

---

## Testy

Projekt posiada **132 zautomatyzowane testy** weryfikujące poprawność narzędzi oraz kod 6502 za pomocą emulacji py65:
- Testy kompilatora sprajtów, tekstów, obracania i animacji znaków oraz labiryntów (`labirynt_builder`, `gen_animated_charset`, `gen_rotated_charset`).
- Testy spójności modeli danych, kolorów, walidatorów `world/` oraz edytorów GUI (Studio).
- Testy emulacyjne 6502 (py65) weryfikujące:
  - Sprzętowe płynne przewijanie ekranu (`HSCROL` $D404, cykl `3 -> 2 -> 1 -> 0 -> 3`) z podwójnym buforowaniem (`GAME_ACTION_VRAM` / `GAME_ACTION_VRAM_B`) i synchronizacją VBLANK.
  - Odroczone wypiekanie ekranu (`deferred screen baking`) zapobiegające spadkom klatek podczas przewijania.
  - Przesuwanie bufora VRAM i wstrzykiwanie kolumn ze strumienia świata.
  - Wyliczanie czasu energii smoka, ubytek energii, zapobieganie natychmiastowej śmierci po respawnie oraz restart poziomu.
  - Detekcję kolizji smoka z przeszkodami w siatce blokującej (`BLOCKING_VRAM`).
  - Niszczenie przeszkód przez ogień smoka (`check_flame_object_collision`) i aktualizację kafli VRAM.
  - Zbieranie sekretów i znajdziek (`check_dragon_secret_collision`) ze śledzeniem zebranych obiektów w masce bitowej (`screen_obj_destroyed`) dla każdego ekranu.
  - Animację zestawów znaków w locie rastra (`charset_anim.asm`).
  - Rysowanie i dynamiczne odświeżanie dolnego paska stanu (`LEVEL:01 SCORE:0000 LIVES:03 SHOTS:01`) z kolorowaniem za pomocą sprajtów i missila PMG (x4 width).
  - Wyświetlanie nakładki nazwy poziomu (`level_name.asm`).
  - Przejście do stanu zakończenia gry z powodem VICTORY (`REASON_SUCCESS`) lub DEFEAT.
- Testy negatywne wykrywające próby kolizji i przekroczenia granic pamięci.

Uruchomienie:
```bash
make test
# lub bezpośrednio:
pytest tests -v
```

