# Project History & Changelog

<!-- AGENT INSTRUCTIONS: Always prepend new entries directly below this comment block. Always use relative paths (relative to project root, e.g., scenes/game.asm), never absolute file:/// URIs. Use the exact format: `## [YYYY-MM-DD] - Feature/Fix Title` -->

## [2026-09-15] - Priorytet sprajta smoka na pierwszym planie (GTIA PRIOR)
- **Konfiguracja priorytetów GTIA ([scenes/game.asm](scenes/game.asm), [engine/level_name.asm](engine/level_name.asm))**:
  - Poprawiono wartość rejestru `GPRIOR`/`PRIOR` z błędnej wartości `$09` (%00001001) na `$11` (%00010001).
  - Wartość `$09` miała ustawiony bit 3 (`$08`), który w układzie GTIA przypisuje priorytet playfieldu nad sprajtami (`PF0 > PF1 > P0..P3 > PF2 > PF3 > BAK`). W efekcie kafelki tła rysowane kolorami `COLPF0` i `COLPF1` (np. drzewa, ściany, przeszkody) przykrywały sprajt smoka (`P0`).
  - Ustawienie bitu 0 (`$01`) bez bitu 3 wymusza ścisły priorytet 1 (`P0 > P1 > P2 > P3 > PF0 > PF1 > PF2 > PF3 > BAK`), gwarantując, że sprajt smoka Jabberwocky (`Player 0`) jest zawsze rysowany na pierwszym planie i przykrywa wszystkie kolory playfield'u (`PF0..PF3`) oraz tło (`BAK`).
  - Ustawienie bitu 4 (`$10`) poprawnie włącza tryb 5. gracza (Multiple Player Enable) dla 4 pocisków PMG reprezentujących jęzor ognia smoka, pobierających barwę z rejestru `COLPF3` (`pal_action_breath`).
  - W przerwaniu `dli_game_action` dodano bezpośredni zapis `lda #$11; sta PRIOR` zabezpieczający priorytet pierwszoplanowy smoka w obszarze gry.
  - W przerwaniu `dli_game_bottom` dodano przełączenie `lda #$09; sta PRIOR` wyłącznie na czas dolnego paska stanu, zapewniając widoczność tekstu trybu 2 (`PF1`) nad podkładowymi 4-krotnymi blokami sprajtów `P0..P3`.
- **Testy jednostkowe ([tests/test_dragon_priority.py](tests/test_dragon_priority.py), [tests/test_level_name.py](tests/test_level_name.py))**:
  - Utworzono zestaw testów `test_dragon_priority.py` weryfikujący:
    - Ustawienie `GPRIOR` i `PRIOR` na `$11` (bit 0 = 1, bit 4 = 1, bit 3 = 0) w procedurze `game_init`.
    - Ustawienie `PRIOR = $11` w przerwaniu DLI obszaru akcji (`dli_game_action`).
    - Przełączenie `PRIOR = $09` w przerwaniu dolnego paska stanu (`dli_game_bottom`).
  - Zaktualizowano asercję w `test_level_name.py` do wartości `0x11`.

## [2026-09-15] - Automatyczne wyłączanie interpretera BASIC przez wektor INITAD
- **Główny moduł startowy ([main.asm](main.asm))**:
  - Zaimplementowano procedurę `disable_basic` (wykonywaną z zablokowanymi przerwaniami `sei`/`cli`), która ustawia bit 1 w rejestrze `PORTB` (`$D301`), bezpiecznie wyłączając 8 KB ROM interpretera BASIC i udostępniając ten obszar (`$A000-$BFFF`) jako pełnoprawny RAM pod dane świata gry.
  - Skonfigurowano wektor inicjalizacji DOS **`INITAD` (`$02E2`)** wskazujący na `disable_basic`, dzięki czemu wyłączenie BASIC następuje natychmiast podczas ładowania pliku XEX, zanim loader zacznie wczytywać segment danych świata (`$7800-$BADB`) do pamięci.
  - Dodano wywołanie `jsr disable_basic` w procedurze `start`, gwarantując wyłączenie BASIC-a również w przypadku bezpośredniego skoku pod wektor `RUNAD`.
- **Weryfikacja mapy pamięci ([scripts/generate_memory_map.py](scripts/generate_memory_map.py), [tests/test_generate_memory_map.py](tests/test_generate_memory_map.py))**:
  - Zweryfikowano poprawną identyfikację wektora `INITAD` ($02E2-$02E3) jako typu `vector` oraz brak naruszenia ciągłości segmentu `LOW_CODE_ADDR` ($0800-$20AD).
  - Rozszerzono `test_parse_real_jabberwocky_lab_and_lst` o weryfikację obecności wektora `INITAD` w generowanej mapie pamięci.
- **Testy jednostkowe ([tests/test_disable_basic.py](tests/test_disable_basic.py))**:
  - Dodano `test_disable_basic_sets_portb_bit1` symulujący stan początkowy z włączonym BASIC-em i weryfikujący ustawienie bitu 1 w `PORTB` przy zachowaniu bitu 0 (aktywny OS ROM).
  - Dodano `test_xex_contains_initad_vector` sprawdzający obecność bloku `INITAD` w wynikowym pliku binarnym `jabberwocky.xex` oraz zgodność adresu docelowego z symbolem `DISABLE_BASIC`.

## [2026-09-15] - Nieśmiertelność smoka podczas ziania ogniem (Fire Invincibility)
- **Silnik kolizji ([engine/flame_collision.asm](engine/flame_collision.asm))**:
  - Dodano warunek w procedurze `check_dragon_blocking_collision`: gdy smok zieje ogniem (`fire_state != 0`), procedura natychmiast wychodzi z wyczyszczoną flagą Carry (`clc; rts`), ignorując kolizje śmiertelne z obiektami blokującymi (`blocking == true`).
  - Procedura `check_dragon_secret_collision` nie sprawdza `fire_state`, dzięki czemu smok podczas ziania ogniem wciąż w pełni zbiera obiekty typu Secret i Interactive oraz otrzymuje punkty i bonusy.
- **Testy jednostkowe ([tests/test_secret_collision.py](tests/test_secret_collision.py))**:
  - Dodano test `test_fire_breathing_invincibility_against_blocking_objects` sprawdzający, że przy `fire_state == 0` kolizja ze ścianą jest wykrywana, natomiast przy `fire_state != 0` (faza 1 oraz 2) kolizja jest ignorowana i smok nie ginie (`dragon_dying == 0`).
  - Dodano test `test_fire_breathing_still_collects_secrets` potwierdzający zbieranie i wymazywanie sekretów podczas aktywnego ziania ogniem.
- **Obsługa buforów PMG ([scenes/game.asm](scenes/game.asm))**:
  - Zidentyfikowano przyczynę pozostawania nieruchomego duszka smoka po przejściu na kolejny poziom: w `advance_to_next_level` rejestr `dragon_prev_y` był natychmiast nadpisywany wartością `DRAGON_START_Y` (114), bez wymazania poprzedniej pozycji smoka (np. Y=40 u góry ekranu). W rezultacie procedura `render_dragon` po zakończeniu ekranu tytułowego poziomu czyściła wyłącznie linie wokół 114, pozostawiając stary kształt duszka na skanliniach 40..66 w pamięci Player 0 RAM (`P0_ADDR`).
  - Utworzono procedurę `clear_action_pmg`, która czyści do zera wszystkie bufory PMG graczy i pocisków ($2300–$27FF), a następnie odtwarza dolne 8 linii maski statusu ($FF) na pozycji `bot_bar_pmg_y`.
  - Wpięto `clear_action_pmg` do procedury `advance_to_next_level`, `respawn_dragon` oraz `game_init`.
- **Testy jednostkowe ([tests/test_scrolling.py](tests/test_scrolling.py))**:
  - Rozszerzono `test_advance_to_next_level_refills_energy_to_100_percent` o weryfikację całkowitego wyczyszczenia pamięci `P0_ADDR` na poprzedniej pozycji smoka ($Y=80$).
  - Dodano test `test_clear_action_pmg_clears_ghost_dragon_across_whole_buffer` sprawdzający kompletne zerowanie całego bufora `P0..P3` i `M` oraz nienaruszenie nakładki paska stanu.
- **Silnik kolizji ([engine/flame_collision.asm](engine/flame_collision.asm))**:
  - Zidentyfikowano przyczynę ignorowania sekretów w kolejnych rozgrywkach: tablica `screen_destroyed_offsets` posiadała jedynie 8 wpisów dla 8 ekranów, podczas gdy świat gry posiada 16 ekranów, a Poziom 1 (`LEVEL_01`) wykorzystuje ekrany o indeksach 9–15 (`TOLEM_01`..`TOLEM_07`).
  - Dla ekranów $\ge 8$ odczyt przesunięcia z `screen_destroyed_offsets` wychodził poza tablicę, powodując nakładanie się masek obiektów oraz wyliczanie przesunięć 64 i 128 w buforze `screen_obj_destroyed`.
  - Bufor `screen_obj_destroyed` miał rozmiar zaledwie 40 bajtów, a procedura `init_flame_collision` czyściła tylko 40 bajtów (`ldx #39`). W efekcie bajty powyżej 40 nigdy nie były zerowane i w kolejnych grach obiekty na tych ekranach były błędnie uznawane za zniszczone/zebrane (`bne @next_obj`), przez co smok przelatywał przez widoczne sekrety bez ich zbierania.
  - Rozszerzono `screen_destroyed_offsets` do 32 ekranów (po 8 bajtów na ekran = do 64 obiektów/ekran bez kolizji).
  - Rozszerzono `screen_obj_destroyed` do pełnych 256 bajtów (`:256 dta 0`).
  - Zaktualizowano `init_flame_collision`, aby czyściła całe 256 bajtów (`ldx #0; sta screen_obj_destroyed,x; inx; bne @clr_loop`), zapewniając czysty stan wszystkich masek przy starcie gry (`game_init`) oraz po respawnie smoka (`respawn_dragon`).
- **Testy jednostkowe ([tests/test_secret_collision.py](tests/test_secret_collision.py))**:
  - Dodano test `test_init_flame_collision_clears_all_256_bytes` weryfikujący zerowanie całego 256-bajtowego bufora po wypełnieniu brudnymi danymi `$FF`.
  - Dodano test `test_level1_screen_secret_persistence_and_game_init_restoration` weryfikujący zbieranie sekretów na ekranie Poziomu 1 (`TOLEM_01`, ekran 9), ich trwałość w trakcie rozgrywki oraz poprawne odnawianie w buforach i czyszczenie bitmaski po rozpoczęciu nowej gry (`game_init`).
- **Kompilator świata ([scripts/labirynt_builder.py](scripts/labirynt_builder.py), [Makefile](Makefile))**:
  - Rozszerzono `obj_type_flags` o bit 7 (`$80`: `has_empty_tiles`), oznaczający obiekty zawierające co najmniej jeden pusty/przezroczysty kafelek (`tile == 0`).
  - Dodano generator `generate_obj_tiles_asm`, tworzący plik `gen/world_obj_tiles.asm` z tablicami kafli (`obj_code_<XX>_tiles`) oraz wskaźnikami Structure-of-Arrays (`obj_type_tiles_lo`, `obj_type_tiles_hi`).
  - Umieszczono tablice kafli w segmencie `LOW_CODE_ADDR` ($0800–$27FF, >2KB wolnego miejsca), chroniąc przestrzeń High RAM i granicę OS ROM ($C000+).
- **Wskaźnik w Zero Page ([zeropage.asm](zeropage.asm))**:
  - Zaalokowano 16-bitowy wskaźnik `PTR_COLL = $88` na potrzeby bezpośredniego adresowania matrycy kafli obiektu kanddata.
- **Silnik kolizji ([engine/flame_collision.asm](engine/flame_collision.asm))**:
  - Zaimplementowano procedurę `fc_calc_tile_offset` (`Y = dy * width + dx`) dla dynamicznego indeksowania kafli wewnątrz obiektu.
  - Zoptymalizowano `check_single_screen_secret` oraz `check_single_screen_flame`: dla obiektów 100% litych (`bit 7 == 0`) kolizja po bounding boxie jest potwierdzana natychmiast (`bpl` -> 2 cykle). Dla obiektów o nieregularnym kształcie (`bit 7 == 1`, np. piramidy, palmy, beczki z pustymi rogami) sprawdzane są przecięcia ze smokiem/płomieniem – jeśli kafel na pozycji kolizji to 0, kandydat jest ignorowany i sprawdzane są kolejne obiekty na ekranie.
  - Zaktualizowano procedury `erase_cur_object` oraz `erase_object_from_source_buffers`: dla obiektów z pustymi kaflami wymazywane są wyłącznie komórki z niezerowym kaflem, zapobiegając nadpisywaniu tła lub sąsiadujących obiektów w buforach VRAM i `blocking_col8/9`.
- **Testy jednostkowe ([tests/test_secret_collision.py](tests/test_secret_collision.py), [tests/test_flame_collision.py](tests/test_flame_collision.py))**:
  - Dodano test `test_obj_type_flags_has_empty_bit` weryfikujący flagę bitu 7 dla obiektów z pustymi kaflami i w 100% litych.
  - Dodano test `test_secret_empty_glyph_ignored_by_collision` weryfikujący ignorowanie kolizji smoka z pustym narożnikiem `BARREL_2_2` oraz jej wykrywanie na kafelku litym.
  - Dodano test `test_flame_empty_glyph_ignored_by_collision` weryfikujący brak zniszczenia `PALM_SWAMP` przy trafieniu w pusty kafelek narożnika i poprawne niszczenie przy sięgnięciu kafelka litego.

## [2026-09-14] - Aktualizacja reguł bonusów dla obiektów Secret i Interactive
- **Mechanika nagród ([engine/flame_collision.asm](engine/flame_collision.asm))**:
  - Zaktualizowano procedurę `check_single_screen_secret` i logikę przyznawania bonusów:
    - **Tylko Secret (`$04`)**: SCORE + 1 oraz **ENERGIA + 10** sub-kroków (wywołanie `increase_energy_10`).
    - **Tylko Interactive (`$02`)**: SCORE + 5, **ENERGIA + 40** sub-kroków (`increase_energy_40`) oraz **LIVES + 1** (nowa procedura `add_life_1` z limitem 99 i odświeżeniem paska stanu).
    - **Secret + Interactive (`$06`)**: SCORE + 10, **ENERGIA + 80** sub-kroków (`increase_energy_80`) oraz **SHOTS + 1** (`add_shot_1`).
  - Zaimplementowano procedurę `increase_energy_n` z punktami wejścia `increase_energy_10`, `increase_energy_40`, `increase_energy_80`, `increase_energy_100`.
- **Testy jednostkowe ([tests/test_secret_collision.py](tests/test_secret_collision.py), [tests/test_charset_anim.py](tests/test_charset_anim.py))**:
  - Zaktualizowano asercje przyrostu energii (+10, +40, +80) oraz dodatkowego życia (+1) przy zbieraniu obiektów.
  - Dopasowano `test_update_animated_charset_segment_transition` do zaktualizowanych wartości powtórzeń segmentów w [chars/animated.json](chars/animated.json).

## [2026-09-14] - Dynamiczny pionowy bounding box smoka zależny od klatki animacji
- **Kompilator duszków ([scripts/compile_sprites.py](scripts/compile_sprites.py))**:
  - Dodano automatyczne obliczanie pionowego zakresu niezerowych pikseli (`min_y` oraz `max_y`) dla każdej klatki animacji duszka.
  - Generowanie tablic `dragon_frame_min_y` i `dragon_frame_max_y` w formacie Structure-of-Arrays w generowanym pliku `gen/dragon_sprite.asm`.
- **Weryfikacja kolizji ([engine/flame_collision.asm](engine/flame_collision.asm))**:
  - W procedurach `check_dragon_blocking_collision` oraz `check_dragon_secret_collision` zastąpiono stałą wysokość 26 linii dynamicznym obliczaniem zakresu wierszy Mode 5 (`dc_dragon_row_min` i `dc_dragon_row_max_p1`) z użyciem rejestru `ANIM_PHASE+1` oraz tablic `dragon_frame_min_y` i `dragon_frame_max_y`.
  - Zapobiega to fałszywym kolizjom ze ścianami/przeszkodami w klatkach ze złożonymi skrzydłami (np. klatka 3 o wysokości 11 linii zamiast 26).
- **Testy jednostkowe ([tests/test_secret_collision.py](tests/test_secret_collision.py), [tests/test_compile_sprites.py](tests/test_compile_sprites.py), [tests/test_flame_collision.py](tests/test_flame_collision.py), [tests/test_scrolling.py](tests/test_scrolling.py))**:
  - Dodano test `test_dragon_frame_dependent_collision_bounds` weryfikujący brak kolizji w klatce 3 (złożone skrzydła) oraz kolizję w klatce 7 (rozpostarte skrzydła) przy identycznej pozycji pionowej.
  - Zaktualizowano indeks poziomu na 1 w testach sprawdzających ekrany lasu `FOREST_01`.

## [2026-09-14] - Poprawka izolacji QSettings i domyślnej palety PF0 w Object Studio
- **Object Studio ([object_studio/main.py](object_studio/main.py))**:
  - Zmieniono sygnaturę `load_resources` na `save_settings: bool = False`, aby wewnętrzne lub testowe wywołania ładowania zasobów nie nadpisywały automatycznie rejestru `QSettings` systemu operacyjnego.
  - Zapis do `QSettings` odbywa się wyłącznie przy celowej zmianie w oknie `action_configure_resources`.
- **Testy jednostkowe ([tests/test_object_studio_resources.py](tests/test_object_studio_resources.py))**:
  - Wprowadzono autouse fixture `isolate_settings_and_colors` izolującą `QSettings` w pamięci oraz przywracającą oryginalną paletę `DEFAULT_COLORS` po zakończeniu testów, zapobiegając wyciekaniu tymczasowych danych testowych do środowiska deweloperskiego użytkownika.
  - Zresetowano klucz `colors_path` w `QSettings` na `world/colors.yaml` (`PF0 = (140, 70, 0)` / `#8c4600`).

## [2026-09-14] - Podgląd graficzny obiektów (ikony) na liście w Object Studio
- **Lista obiektów ([object_studio/widgets/object_list_widget.py](object_studio/widgets/object_list_widget.py))**:
  - Dodano renderowanie małych ikon dla każdego obiektu na liście (`QListWidget.setIconSize(QSize(32, 32))`).
  - Zaimplementowano metodę `_render_icon` renderującą piksele kafli obiektu na podstawie aktualnego charsetu (`Charset`) i palety barw Atari, ze skalowaniem nearest-neighbor (zachowanie ostrości pikseli Atari).
  - Dodano metody `set_charset`, `set_colors` oraz `update_object_item`, dzięki czemu ikony na liście odświeżają się dynamicznie przy edycji na płótnie, zmianie właściwości oraz zmianie zasobów.
- **Główne okno ([object_studio/main.py](object_studio/main.py))**:
  - Przekazano `charset` i kolory do `ObjectListWidget` przy wczytywaniu zasobów i zmianie parametrów.
  - Podłączono `update_object_item` pod zdarzenia `_on_canvas_changed` oraz `_on_prop_changed` (natychmiastowa aktualizacja ikony obiektu na liście podczas rysowania).
- **Testy jednostkowe ([tests/test_object_studio_list.py](tests/test_object_studio_list.py))**:
  - Dodano test `test_object_list_widget_icon_rendering` weryfikujący generowanie i aktualizację ikon obiektów.

## [2026-09-14] - Konfiguracja i automatyczne ładowanie zasobów w Object Studio
- **Object Studio ([object_studio/main.py](object_studio/main.py))**:
  - Dodano obsługę argumentów wiersza poleceń (`--objects`, `--colors`, `--charset`) ze standardowymi wartościami domyślnymi (`world/objects.yaml`, `world/colors.yaml`, `fonts/game.fnt`).
  - Dodano automatyczne wczytywanie wszystkich trzech zasobów przy starcie programu (koniec z koniecznością ręcznego otwierania każdego pliku z osobna).
  - Wprowadzono zapamiętywanie skonfigurowanych ścieżek w rejestrze ustawień `QSettings("Atari", "ObjectStudio")`.
  - W menu `File` dodano opcję `Konfiguruj zasoby...` otwierającą dedykowane okno dialogowe wyboru plików.
  - Zaimplementowano metodę `load_resources` przeładowującą definicje obiektów, paletę kolorów Atari oraz zestaw znaków (.fnt) w czasie działania aplikacji z automatycznym odświeżeniem płótna, palety i listy.
  - W przypadku braku plików zasobów przy starcie program wyświetla okno dialogowe z prośbą o wskazanie poprawnych ścieżek (analogicznie do Labirynt Studio).
- **Okno dialogowe zasobów ([object_studio/widgets/resource_dialog.py](object_studio/widgets/resource_dialog.py))**:
  - Utworzono komponent `ResourceDialog` z polami wprowadzania i przyciskami przeglądania plików dla `objects.yaml`, `colors.yaml` oraz `game.fnt` wraz z walidacją ich istnienia przed zatwierdzeniem.
- **Ustawienia domyślne ([object_studio/settings.py](object_studio/settings.py))**:
  - Zaktualizowano kolory rezerwowe `DEFAULT_COLORS` do wartości odpowiadających `world/colors.yaml`.
- **Testy jednostkowe ([tests/test_object_studio_resources.py](tests/test_object_studio_resources.py))**:
  - Dodano zestaw testów sprawdzających walidację w `ResourceDialog`, automatyczne ładowanie i przeładowywanie zasobów w `MainWindow` oraz parsowanie argumentów CLI.

## [2026-09-14] - Resetowanie energii smoka do 100% na każdym nowym poziomie
- **Scena gry ([scenes/game.asm](scenes/game.asm))**:
  - W gałęzi `@have_another_level` procedury `advance_to_next_level` dodano wywołania `init_energy_bar` oraz `calc_energy_frames`, dzięki czemu po ukończeniu etapu i przejściu do kolejnego labiryntu smok zawsze startuje ze 100% energii (`COUNTER_FULL = 40`, `COUNTER_EIGHT = 83`).
  - Zresetowano również stan dynamiczny smoka (`dragon_y = DRAGON_START_Y`, `dragon_vel_hi/lo = 0`, `dragon_sub_y = 0`, wygaszenie strzałów i prędkość przelotowa `SCROLL_BASE_SPEED`).
- **Testy automatyczne ([tests/test_scrolling.py](tests/test_scrolling.py))**:
  - Dodano test `test_advance_to_next_level_refills_energy_to_100_percent` weryfikujący uzupełnienie paska energii w `GAME_STATUS_VRAM` (39 znaków $52 + 1 znak $53), liczników energii oraz pozycji smoka po przejściu do kolejnego labiryntu.
  - Wszystkie 102 testy przechodzą pomyślnie.

## [2026-09-14] - Reorganizacja pamięci RAM (relokacja silników pomocniczych do Low RAM $0800)
- **Architektura pamięci ([main.asm](main.asm))**:
  - Zdefiniowano segment `LOW_CODE_ADDR = $0800` w wolnej przestrzeni RAM (`$0800`–`$1FFF`, przed buforem PMG `$2000`).
  - Przeniesiono silniki pomocnicze (`engine/charset_anim.asm`, `engine/sound.asm`, `engine/flame_collision.asm`, `engine/level_name.asm`, `gen/dragon_sprite.asm`) z High RAM (`$7800+`, za danymi świata) do `LOW_CODE_ADDR` (`$0800`–`$1812`, 4115 bajtów).
  - Rozszerzone dane świata gry dla 16 ekranów / 2 labiryntów (`gen/world_data.asm`) mieszczą się teraz całkowicie w przedziale `$7800`–`$B8FF`, pozostawiając 1792 bajty wolnego bufora przed granicą OS ROM (`$BFFF`).
  - Zachowano ściśle rosnący porządek dyrektyw `org` w MADS (`$0800` -> `$2800` -> `$4000` -> `$6800` -> `$7000` -> `$7400` -> `$7800` -> `$02E0`).
- **Testy automatyczne**:
  - Zaktualizowano [tests/test_labirynt_builder.py](tests/test_labirynt_builder.py), [tests/test_level_name.py](tests/test_level_name.py) oraz [tests/test_scrolling.py](tests/test_scrolling.py) do dynamicznego odczytu liczby labiryntów i długości nazw poziomów z `world/project.yaml`.
  - Wszystkie 101 testów automatycznych py65 / pytest przechodzi pomyślnie.

## [2026-09-14] - Zmiana doładowania energii dla obiektów Interactive na 100 jednostek
- **Silnik kolizji (`engine/flame_collision.asm`)**:
  - Zmieniono procedurę doładowania energii przy zebraniu obiektu `Interactive` na `increase_energy_100` (100 sub-kroków `increase_energy_bar`, tj. 12.5 znaku paska energii z ograniczeniem do maksimum).
  - Zachowano aliasy kompatybilności `increase_energy_25` oraz `increase_energy_5`.
- **Testy automatyczne (`tests/test_secret_collision.py`)**:
  - Zaktualizowano testy `test_increase_energy_100` oraz `test_interactive_collection_flow` pod kątem 100 kroków doładowania energii.

## [2026-09-14] - Zwiększenie doładowania energii dla obiektów Interactive z 5 do 25
- **Silnik kolizji (`engine/flame_collision.asm`)**:
  - Zmieniono liczbę kroków doładowania energii przy zebraniu obiektu `Interactive` z 5 na 25 (`increase_energy_25`).
  - Procedura `increase_energy_25` wykonuje 25 sub-kroków `increase_energy_bar` (płynny przyrost energii o ponad 3 pełne znaki paska z zachowaniem limitu maksimum).
  - Zachowano alias wstecznej kompatybilności `increase_energy_5 = increase_energy_25`.
- **Testy automatyczne (`tests/test_secret_collision.py`)**:
  - Zaktualizowano test jednostkowy `test_increase_energy_25` oraz test integracyjny `test_interactive_collection_flow` pod kątem 25 kroków doładowania energii.

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