# Jabberwocky — Atari 8-bit (XL/XE)

Projekt gry/dema na komputery **Atari 800XL / 65XE** (procesor 6502, układy ANTIC, GTIA, POKEY) inspirowany poematem Lewisa Carrolla *"Jabberwocky"* (w polskim przekładzie Stanisława Barańczaka jako *"Żabrołak"*).

Projekt łączy tradycyjne programowanie w asemblerze 6502 (MADS) z nowoczesnym zautomatyzowanym potokiem budowania (Python 3, Pydantic, PySide6, PyTest) oraz zintegrowanym środowiskiem do tworzenia grafiki i sprajtów.

---

## Spis treści

- [Główne cechy](#główne-cechy)
- [Architektura silnika](#architektura-silnika)
- [Struktura projektu](#struktura-projektu)
- [Wymagania i narzędzia](#wymagania-i-narzędzia)
- [Instalacja i kompilacja](#instalacja-i-kompilacja)
- [Narzędzia wspomagające](#narzędzia-wspomagające)
  - [Sprite Studio (Edytor grafiki PMG)](#sprite-studio-edytor-grafiki-pmg)
  - [Memory Map Generator & Validator](#memory-map-generator--validator)
  - [Image Converter](#image-converter)
- [Mapa pamięci](#mapa-pamięci)
- [Testy](#testy)

---

## Główne cechy

- **Klasyczny target 6502**: Kod zoptymalizowany pod architekturę Atari XL/XE z zachowaniem oficjalnego zestawu instrukcji MOS 6502 oraz ścisłych reguł taktowania cykli i stron pamięci.
- **Wielostanowa maszyna stanów**:
  - `STATE_TITLE`: Ekran tytułowy w wysokiej rozdzielczości bitmapowej.
  - `STATE_INTRO`: Scena narracyjna z poematem, polską czcionką i gradientami DLI.
  - `STATE_GAME`: Główny ekran rozgrywki z animowaną postacią smoka i fizyką inercyjną.
  - `STATE_GAME_OVER`: Ekran zakończenia z przejściem do ponownej rozgrywki.
- **Zaawansowane wykorzystanie ANTIC & GTIA**:
  - **Tryb ANTIC F** (320×175, 1 bpp) na ekranie tytułowym z podziałem LMS (Local Memory Scan) omijającym granicę 4 KB bufora ekranu.
  - **Tryb ANTIC 2** (40×24 znakowy) w scenie Intro z przerwaniami **DLI (Display List Interrupt)** dynamicznie zmieniającymi rejestry koloru tekstu w locie linii rastra.
  - **Hybrydowy Display List** w grze: 11 linii w podwójnie wysokim trybie **ANTIC 5** (160×16 znaków, pole akcji) + 2 linie w trybie **ANTIC 2** (pasek statusu).
- **Animacja i fizyka sprajtów PMG (Player/Missile Graphics)**:
  - Wieloklatkowy sprajt smoka Jabberwocky (Player 0) z akumulatorem fazy 16-bit (stałoprzecinkowy format 8.8) zapewniającym płynną animację niezależną od wariacji klatek.
  - Fizyka ruchu pionowego w arytmetyce stałoprzecinkowej (prędkość, akceleracja, opór/tarcie inercyjne).
  - Pęd przewijania (momentum scroll) połączony z częstotliwością machania skrzydłami.
- **Automatyczny Single Source of Truth (SSOT)**:
  - Dane graficzne i sprajty przechowywane w formacie JSON i kompilowane do struktur asemblerowych SoA (Structure-of-Arrays).
  - Weryfikator pamięci sprawdzający kolizje segmentów i granice Zero Page w trakcie każdego `make`.

---

## Architektura silnika

```
       [ main.asm ]
            │
    ┌───────┴───────┐
    │  State Engine │ (Pętla główna zsynchronizowana z VBLANK RTCLOK)
    └───────┬───────┘
            ├── STATE_TITLE     --> scenes/title.asm     (ANTIC Mode F)
            ├── STATE_INTRO     --> scenes/intro.asm     (ANTIC Mode 2 + DLI)
            ├── STATE_GAME      --> scenes/game.asm      (ANTIC 5 + ANTIC 2 + PMG)
            └── STATE_GAME_OVER --> scenes/gameover.asm  (ANTIC Mode 2)
```

Główna pętla gry działa w sposób deterministyczny w oparciu o synchronizację pionową (`RTCLOK`):
1. **Input Poll** (`update_input`): Odczyt joysticka/przycisku Fire z detekcją zbocza opadającego.
2. **State Dispatcher** (`dispatch_state`): Obsługa przejść stanów (`*_init`) i wykonania klatki (`*_run`).
3. **Render & PMG Updates**: Aktualizacja buforów Player/Missile oraz rejestrów GTIA.

---

## Struktura projektu

```
jabberwocky/
├── main.asm                 # Główny punkt wejścia, wektory RUNAD, pętla i Display Listy
├── hardware.asm             # Adresy rejestrów ANTIC, GTIA, POKEY, PIA i OS
├── zeropage.asm             # Alokacja zmiennych strony zerowej ($80-$FF)
├── Makefile                 # Reguły budowania, weryfikacji i uruchamiania
├── requirements.txt         # Zależności narzędzi w Pythonie
│
├── scenes/                  # Moduły poszczególnych scen
│   ├── title.asm            # Ekran tytułowy
│   ├── intro.asm            # Wprowadzenie i wyświetlanie wiersza (DLI)
│   ├── game.asm             # Logika rozgrywki, fizyka i animacja PMG
│   ├── gameover.asm         # Ekran końca gry
│   └── text_utils.asm       # Procedury wypisywania i konwersji znaków ATASCII/Internal
│
├── sprite_studio/           # Narzędzie GUI (PySide6) do edycji sprajtów PMG
│   ├── main.py              # Główna aplikacja okienkowa Sprite Studio
│   ├── models.py            # Modele danych sprajtów (klatki, warstwy)
│   ├── validation.py        # Walidacja specyfikacji PMG
│   ├── history.py           # Historia cofania (Undo/Redo)
│   └── widgets/             # Komponenty interfejsu (Canvas, Palette, Timelines)
│
├── scripts/                 # Narzędzia potoku budowania (Python)
│   ├── compile_sprites.py   # Kompilator definicji JSON sprajtów do MADS ASM
│   ├── convert_image.py     # Konwerter grafik (ANTIC Mode F)
│   └── generate_memory_map.py # Analizator symboli MADS i walidator pamięci
│
├── sprites/                 # Źródłowe definicje sprajtów (JSON)
│   └── jabberwocky.json     # Definicja klatek i masek smoka Jabberwocky
│
├── fonts/                   # Zestawy czcionek Atari (1024 bajty)
│   └── text.fnt             # Zestaw znaków z polskimi diakrytykami
│
├── texts/                   # Teksty źródłowe scen
│   └── title.txt            # Treść wiersza "Żabrołak"
│
├── img/                     # Źródłowe pliki graficzne
│   └── title.png            # Grafika ekranu tytułowego
│
├── docs/                    # Dokumentacja i generowane raporty pamięci
│   ├── memory_map.txt       # Czytelne podsumowanie mapy pamięci i wolnej przestrzeni
│   ├── memory_map.json      # Maszynowy model alokacji segmentów
│   └── architecture/        # Specyfikacje techniczne modułów
│
├── tests/                   # Zestaw testów jednostkowych (pytest)
│   ├── test_compile_sprites.py
│   └── test_generate_memory_map.py
│
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

Zaleca się utworzenie środowiska wirtualnego:

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
| `make` / `make all` | Konwertuje zasoby, kompiluje sprajty, asembluje `jabberwocky.xex` i weryfikuje mapę pamięci |
| `make xex` | Buduje sam plik binarny `jabberwocky.xex` |
| `make check_memory` | Generuje raport pamięci `docs/memory_map.txt` oraz `docs/memory_map.json` |
| `make test` | Uruchamia pełny zestaw testów `pytest` |
| `make run` | Buduje projekt i uruchamia go w emulatorze Altirra |
| `make clean` | Usuwa pliki binarne oraz katalog `gen/` |
| `make help` | Wyświetla listę dostępnych celów |

---

## Narzędzia wspomagające

### Sprite Studio (Edytor grafiki PMG)
Aplikacja desktopowa napisana w **PySide6** (Qt) ułatwiająca projektowanie wieloklatkowych sprajtów na układy PMG Atari:
- Siatka edycyjna z podglądem pikseli PMG (pojedyncza i podwójna szerokość).
- Obsługa wielu klatek animacji z kontrolą czasu trwania.
- Podgląd animacji na żywo z regulacją FPS.
- Eksport i import w formacie JSON zgodnym z kompilatorem silnika.

Uruchomienie:
```bash
python -m sprite_studio.main
```

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
| `$80` – `$84` | 5 B | Zmienne strony zerowej (`PTR_SRC`, `PTR_DST`, `ZP_TMP`) |
| `$85` – `$FF` | 123 B | **Wolna strona zerowa** |
| `$0800` – `$2FFF` | 10 KB | **Wolna pamięć RAM** |
| `$2000` – `$27FF` | 2 KB | Bufor grafiki graczy i pocisków (PMG, wyrównany do 2 KB) |
| `$3000` – `$3A82` | ~2.7 KB | Segment kodu i logiki gry (`main.asm`, sceny, tablice) |
| `$3E80` – `$3F8F` | 272 B | Segment Display List (niewykraczający poza granicę 1 KB) |
| `$4000` – `$5B67` | ~7 KB | Bufor grafiki tytułowej VRAM (ANTIC F, 320×175) |
| `$5C00` – `$5FBF` | 960 B | Bufor tekstu dla trybów znakowych ANTIC 2 (Intro, Stubs) |
| `$6000` – `$61B7` | 440 B | Bufor pola akcji w grze (11 linii ANTIC 5) |
| `$6200` – `$624F` | 80 B | Bufor paska statusu w grze (2 linie ANTIC 2) |
| `$7000` – `$73FF` | 1024 B | Bufor zestawu znaków (Font, wyrównany do 1 KB) |
| `$7400` – `$BFFF` | ~19 KB | **Wolna pamięć RAM** (dostępna na kolejne etapy gry) |
| `$C000` – `$DFFF` | — | **Naruszenie zabronione** (OS ROM / Rejestry sprzętowe) |

Szczegółowy i zawsze aktualny raport generowany jest po każdej kompilacji w pliku [docs/memory_map.txt](docs/memory_map.txt).

---

## Testy

Projekt posiada zautomatyzowane testy jednostkowe weryfikujące poprawność kompilatora sprajtów oraz mechanizmu walidacji pamięci (w tym testy negatywne wykrywające próby kolizji i przekroczenia granic pamięci):

```bash
make test
# lub bezpośrednio:
pytest tests -v
```
