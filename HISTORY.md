# Project History & Changelog

<!-- AGENT INSTRUCTIONS: Always prepend new entries directly below this comment block. Always use relative paths (relative to project root, e.g., scenes/game.asm), never absolute file:/// URIs. Use the exact format: `## [YYYY-MM-DD] - Feature/Fix Title` -->

## [2026-09-17] - Aktualizacja dokumentacji projektu (README.md)
- **Zakres weryfikacji**: Przegląd pliku [README.md](README.md) pod kątem zgodności z aktualną architekturą silnika, potokiem budowania, alokacją pamięci oraz stanem testów.
- **Wprowadzone aktualizacje**:
  - **Cechy silnika i architektura**: Dodano opisy podwójnego buforowania VRAM (`GAME_ACTION_VRAM` / `GAME_ACTION_VRAM_B`), synchronizacji przełączania LMS w VBLANK, odroczonego wypiekania ekranu (`deferred screen baking`), szybkiej detekcji kolizji smoka ($O(1)$ w oparciu o siatkę `BLOCKING_VRAM`), niszczenia obiektów zianiem ognia (`check_flame_object_collision`), zbierania sekretów ze śledzeniem w maskach bitowych (`check_dragon_secret_collision`), animowanych zestawów znaków oraz podsystemu audio POKEY (`engine/sound.asm`).
  - **Struktura projektu**: Dodano brakujące katalogi i moduły w drzewie plików: `engine/` (`flame_collision.asm`, `level_name.asm`, `charset_anim.asm`, `sound.asm`), `chars/` (`animated.json`, `rotated.json`), skrypty generatorów `gen_animated_charset.py` i `gen_rotated_charset.py` oraz zaktualizowano zakres strony zerowej (`$80`–`$89`).
  - **Narzędzia wspomagające**: Rozszerzono opis `Labirynt Builder` o generowanie tablic kafli składowych `gen/world_obj_tiles.asm` oraz dodano sekcję generatorów animacji i obrotów znaków.
  - **Mapa pamięci**: Zaktualizowano tabelę alokacji pamięci na podstawie aktualnego raportu [docs/memory_map.txt](docs/memory_map.txt) (w tym segment `ENGINE` `$080B`–`$1FA9`, bufor `BLOCKING_VRAM`, bufor VRAM B, segment czcionek i danych świata `$6800`–`$85C4`).
  - **Zestaw testów**: Zaktualizowano liczbę testów z 52 do **127 zautomatyzowanych testów** py65/pytest oraz zaktualizowano listę weryfikowanych obszarów (w tym kolizje, wypiekanie buforów, odnawianie energii smoka).
  - Weryfikacja: `make all` oraz pełny przebieg testów `pytest` (127 passed) bez błędów.

## [2026-09-17] - Naprawa natychmiastowej ponownej śmierci smoka po restarcie poziomu (Energy Respawn Race Condition)
- **Problem**: Po wyczerpaniu energii smoka i zakończeniu procedury śmierci (fade + explosion), poziom restartował się od nowa, jednak natychmiast na starcie uruchamiała się kolejna procedura śmierci, powodując utratę kolejnego życia.
- **Przyczyna**:
  - W procedurze `respawn_dragon` w [scenes/game.asm](scenes/game.asm) flaga `dragon_dying` była zerowana (`sta dragon_dying`) na samym początku, podczas gdy licznik energii `COUNTER_FULL` miał wciąż wartość `0` (uzupełnienie energii `init_energy_bar` znajdowało się dopiero pod koniec procedury, po długotrwałym pieczeniu ekranów w `init_level_screens`).
  - W przerwaniu VBLANK `vblank_game` procedura `update_energy_bar` działała nieustannie (nawet na ekranie nazwy poziomu `SUBSTATE_LEVEL_NAME`), nie weryfikując podstanu gry. W momencie gdy przerwanie VBLANK trafiło w okno pomiędzy wyzerowaniem `dragon_dying` a odnowieniem energii, `update_energy_bar` wykrywał `COUNTER_FULL == 0` i natychmiast wywoływał `start_dragon_death`, ustawiając `dragon_dying = 1` zanim poziom zdążył wystartować.
  - Ponadto w przerwaniu VBLANK brakowało blokady sprawdzania kolizji i poboru energii na ekranie nazwy poziomu (`show_level_name_screen`).
- **Rozwiązanie ([scenes/game.asm](scenes/game.asm), [tests/test_status_bar.py](tests/test_status_bar.py))**:
  - W procedurach `respawn_dragon` oraz `advance_to_next_level` w [scenes/game.asm](scenes/game.asm) natychmiast na wejściu przełączono podstan gry `game_substate = SUBSTATE_LEVEL_NAME` oraz przesunięto odnawianie energii `init_energy_bar` i `calc_energy_frames` na sam początek, przed wyzerowaniem flagi `dragon_dying`.
  - W procedurze VBLANK `vblank_game` dodano warunek `lda game_substate; cmp #SUBSTATE_PLAYING; bne @skip_gameplay_vbl`, dzięki czemu procedury sprawdzania kolizji (`check_dragon_collisions`, `check_flame_object_collision`) oraz ubytku energii (`update_energy_bar`) są aktywne wyłącznie podczas właściwego lotu na planszy.
  - W pętli `game_run` dodano zabezpieczenie pomijające renderowanie klatki gry, gdy po zakończeniu sekwencji śmierci nastąpiło przełączenie na podstan nazwy poziomu.
  - W [tests/test_status_bar.py](tests/test_status_bar.py) dodano test `test_respawn_after_energy_depletion_prevents_immediate_re_death`, weryfikujący poprawny przebieg respawnu po ubytku energii i odporność na przerwania VBLANK.
  - Wszystkie 127 testów py65 zakończone sukcesem (`127 passed`), mapa pamięci w pełni poprawna.

## [2026-09-17] - Eliminacja szarpnięcia przy przejściu między ekranami poprzez odroczone pieczenie bufora (Deferred Bake)
- **Problem**: Podczas lotu smoka w prawo, dokładnie w momencie przejścia między kolejnymi ekranami labiryntu (co 40 kroków koarsowych po zapełnieniu bufora strumieniowania), pojawiało się widoczne szarpnięcie / chwilowe przycięcie animacji (stutter).
- **Przyczyna**:
  - W momencie zakończenia strumieniowania kolumn 0..39 (`incoming_col_idx == 40`), procedura `scroll_playfield_step` wywoływała bezpośrednio `setup_incoming_screen_ptr`, która natychmiast synchronicznie uruchamiała `bake_screen` (~3000–6000 cykli CPU: czyszczenie 880 bajtów VRAM i BLK oraz renderowanie obiektów).
  - Ponieważ w tej samej klatce wykonywała się już procedura `shift_vram_left` (~4900 cykli CPU), łączny czas pracy CPU w klatce przejścia ekranów sięgał 9000–12000 cykli (80–105 linii rastra). Powodowało to przekroczenie budżetu klatki, kolizję z przerwaniem DLI oraz opóźnienie obsługi VBLANK (`vram_swap_pending`), co skutkowało pominięciem lub przesunięciem klatki i widocznym szarpnięciem.
- **Rozwiązanie ([scenes/game.asm](scenes/game.asm), [tests/test_scrolling.py](tests/test_scrolling.py))**:
  - Wprowadzono mechanizm odroczonego wypiekania nowego ekranu z flagą `bake_pending` (1 = oczekuje na wypiek).
  - W procedurze `setup_incoming_screen_ptr` usunięto bezpośrednie wywołanie `bake_screen`, zastępując je ustawieniem flagi `bake_pending = 1`.
  - Wprowadzono nową procedurę `execute_pending_bake` wywoływaną na początku pętli głównej `game_run`.
  - Wypiek nowego ekranu (`bake_screen`) następuje w klatce K+1 (zaraz po przejściu), w której akumulator przewijania (`scroll_accum`) nie osiąga progu koarsowego ($0400), dzięki czemu kosztowne operacje `shift_vram_left` i `bake_screen` nigdy nie wykonują się w tej samej klatce.
  - W procedurze `init_level_screens` dodano synchroniczne wywołanie `execute_pending_bake`, zapewniając natychmiastowe wypieczenie ekranu 1 podczas startu/respawnu przed prefillem kolumn 44..47.
  - Dodano testy w [tests/test_scrolling.py](tests/test_scrolling.py) weryfikujące obecność symboli `BAKE_PENDING` i `EXECUTE_PENDING_BAKE` oraz poprawne odroczenie wypieku i wykonanie w wolnej klatce.
  - Wszystkie 126 testów py65 zakończone sukcesem (`126 passed`), mapa pamięci w pełni zweryfikowana.

## [2026-09-16] - Likwidacja szarpania obrazu (Jitter) poprzez synchronizację fazową HSCROL i LMS w VBLANK
- **Problem**: Po wdrożeniu podwójnego buforowania VRAM pojawiło się gwałtowne migotanie i szarpanie obrazu (skoki o 3-4 zegary koloru w tył i w przód co kilka klatek na granicach kolumn) oraz niestabilność wynikająca z mid-frame zapisu do rejestru sprzętowego `HSCROL`.
- **Przyczyna**: 
  1. Desynchronizacja fazowa (1-klatkowa rozbieżność): procedura `update_world_scrolling` w pętli głównej natychmiast nadpisywała zmienną `hscrol_fine = 3` dla bieżącej klatki, podczas gdy zamiana wskaźnika LMS w Display List (`dlist_game_action_lms + 2`) następowała dopiero w kolejnym przerwaniu VBLANK (`vblank_game`). W efekcie przez całą jedną klatkę ANTIC wyświetlał stary bufor VRAM z nową wartością `HSCROL = 3`, powodując gwałtowny skok obrazu o 6-8 pikseli w tył, a w kolejnej klatce (po zamianie LMS) skok do przodu.
  2. Zapis sprzętowego rejestru `HSCROL` ($D404) odbywał się w przerwaniach DLI w trakcie aktywnego rastra (`dli_game_action` na linii 32 oraz wielokrotne zerowanie w `dli_game_top` i `dli_game_bottom`), co powodowało niepotrzebne przełączanie stanu rejestru w trakcie generowania obrazu i mikro-drgania cykli.
- **Rozwiązanie ([scenes/game.asm](scenes/game.asm), [tests/test_scrolling.py](tests/test_scrolling.py))**:
  - Wprowadzono zmienną buforującą `hscrol_next` w [scenes/game.asm](scenes/game.asm).
  - W procedurze `update_world_scrolling` obliczona wartość przewijania zapisywana jest do `hscrol_next` zamiast bezpośrednio do rejestru roboczego `hscrol_fine`.
  - W przerwaniu VBLANK `vblank_game` sprzężono atomowo: przepisanie `hscrol_fine = hscrol_next`, **bezpośredni zapis do rejestru sprzętowego `sta HSCROL` ($D404)** oraz przełączenie wskaźnika LMS Display List (`dlist_game_action_lms + 2`). Wartości sprzętowe wpisywane są w wygaszaniu pionowym, gdy ANTIC nie pobiera linii obrazu.
  - Usunięto zbędne i szkodliwe zapisy `sta HSCROL` z przerwań linii `dli_game_top`, `dli_game_action` oraz `dli_game_bottom` (linie pasków statusu nie mają ustawionego bitu `DL_HSCROL`, więc ANTIC ich nie przesuwa niezależnie od wartości w rejestrze).
  - Zaktualizowano procedury `game_init` oraz `init_level_screens`, inicjalizując `hscrol_next = 3` i `HSCROL = 3`.
  - W [tests/test_scrolling.py](tests/test_scrolling.py) dodano test jednostkowy `test_vblank_game_commits_hscrol_and_lms_swap` oraz zaktualizowano asercje na `HSCROL_NEXT`.
  - Wszystkie 125 testów py65 zakończone sukcesem (`125 passed`), walidacja mapy pamięci w `make all` potwierdzona.


## [2026-09-16] - Eliminacja rwania obrazu (Screen Tearing) poprzez sprzętowe podwójne buforowanie VRAM (Double Buffering)
- **Problem**: Podczas przewijania poziomu na ekranie widoczne było szarpanie i poziome rozrywanie obrazu (screen tearing) występujące regularnie co ~5 klatek przy przesunięciu o kolejną kolumnę.
- **Przyczyna**: Pętla `shift_vram_left` w [scenes/game.asm](scenes/game.asm) (~5000 cykli CPU, ~70 linii rastra) modyfikowała bezpośrednio bufor `GAME_ACTION_VRAM` w trakcie aktywnej generacji obrazu ANTIC, powodując wyświetlanie połówkowo przesuniętych danych przez wiązkę elektronów.
- **Rozwiązanie ([main.asm](main.asm), [scenes/game.asm](scenes/game.asm), [engine/flame_collision.asm](engine/flame_collision.asm), [tests/test_scrolling.py](tests/test_scrolling.py))**:
  - Zaalokowano drugi bufor pola gry `GAME_ACTION_VRAM_B = $6400` ($6400–$660F, 528 B) w obszarze dawnego bufora `BLOCKING_VRAM`.
  - Wprowadzono zmienne kontrolne `active_vram_buf` (0/1), `vram_swap_pending` oraz tablicę starszych bajtów buforów `vram_hi_tbl` ($60, $64).
  - Nadano etykietę `dlist_game_action_lms` dla instrukcji LMS pola akcji w Display List [main.asm](main.asm).
  - Przebudowano procedurę `shift_vram_left` na dwa dedykowane, zoptymalizowane warianty: `shift_vram_a_to_b` oraz `shift_vram_b_to_a` (odliczanie w dół `DEX/BPL`), czytające z bufora wyświetlanego (`VRAM_FRONT`) i zapisujące do bufora tylnego (`VRAM_BACK`), eliminując zakłócenia aktywnego rastra.
  - Zaktualizowano procedurę strumieniowania `@stream_screen_col` oraz czyszczenia ogona `level_tail_cols` w [scenes/game.asm](scenes/game.asm), aby kierowały zapis kolumny 47 do bufora tylnego oraz ustawiały flagę `vram_swap_pending = 1`.
  - W przerwaniu VBLANK `vblank_game` w [scenes/game.asm](scenes/game.asm) dodano atomowe przełączanie wskaźnika LMS w Display List (`sta dlist_game_action_lms + 2`) oraz negację flagi `active_vram_buf` (zajmujące ~20 cykli CPU).
  - W procedurze `erase_cur_object` w [engine/flame_collision.asm](engine/flame_collision.asm) zapewniono jednoczesne wymazywanie niszczonych przeszkód i zbieranych sekretów z obu buforów VRAM (`$6000` i `$6400`), zapobiegając desynchronizacji obiektów między buforami.
  - W procedurze `init_level_screens` w [scenes/game.asm](scenes/game.asm) dodano czyszczenie i synchronizację obu buforów A i B przy starcie poziomu.
  - Przeniesiono moduł `scenes/gameover.asm` do segmentu `LOW_CODE_ADDR` ($080B–$1FA9), zwalniając 530 bajtów w segmencie `CODE_ADDR` ($2800–$3E32) i zapewniając 461 bajtów wolnego marginesu przed adresem `$4000`.
  - Zaktualizowano testy [tests/test_scrolling.py](tests/test_scrolling.py), weryfikując poprawne działanie obu kierunków przesunięcia oraz strumieniowania do bufora docelowego.
  - Wszystkie 124 testy py65 zaliczone (`124 passed in 18.40s`), pełna weryfikacja mapy pamięci w `make all`.

## [2026-09-16] - Naprawa odnawiania się zebranych obiektów secret po śmierci smoka (Respawn Persistence)
- **Problem**: Gdy smok zebrał obiekty typu `secret`, a następnie zginął i poziom rozpoczynał się od nowa, zebrane wcześniej sekrety pojawiały się ponownie na planszy (umożliwiając wielokrotne zbieranie tych samych bonusów).
- **Przyczyna**: Procedura `respawn_dragon` w [scenes/game.asm](scenes/game.asm) wywoływała procedurę `init_flame_collision`, która zerowała całą 256-bajtową tablicę bitmasek `screen_obj_destroyed`. Gdy po zresetowaniu parametrów smoka wywoływana była procedura `init_level_screens` -> `bake_screen`, z powodu wyczyszczonej maski `screen_obj_destroyed` silnik traktował wszystkie obiekty jako niezebrane/żywe i wypiekał je na nowo do bufora VRAM i kolizji.
- **Rozwiązanie ([scenes/game.asm](scenes/game.asm), [tests/test_secret_collision.py](tests/test_secret_collision.py))**:
  - Usunięto zbędne wywołanie `jsr init_flame_collision` z procedury `respawn_dragon` w [scenes/game.asm](scenes/game.asm). `screen_obj_destroyed` jest teraz zerowany wyłącznie przy inicjalizacji nowej gry w `game_init`, natomiast pozostaje zachowany w trakcie trwania całej rozgrywki (run persistence).
  - Zaktualizowano testy integracyjne py65 w [tests/test_secret_collision.py](tests/test_secret_collision.py) (`test_secret_run_persistence_and_game_init_restoration` oraz `test_level1_screen_secret_persistence_and_game_init_restoration`), aby symulowały rzeczywistą procedurę `RESPAWN_DRAGON` i weryfikowały, że zebrane sekrety nie są re-renderowane do buforów stagingowych ani aktywnego pola gry `GAME_ACTION_VRAM`.
  - Wszystkie 124 testy py65 przeszły pomyślnie (`124 passed in 9.83s`), weryfikacja mapy pamięci `make all` zakończona sukcesem.


## [2026-09-15] - Naprawa uszkodzonego obrazu tytułowego po rozgrywce (Relokacja STUB_VRAM)
- **Problem**: Po zakończeniu rozgrywki (Game Over -> Title Screen) górna część obrazu tytułowego (~1/4 ekranu) była uszkodzona (nadpisana zerami/znakami).
- **Przyczyna**: Bufor tekstu `STUB_VRAM = $4000` nakładał się bezpośrednio na pamięć bitmapy ekranu tytułowego (`VRAM_ADDR = $4000`, `$4000-$5B67`). Procedury `clear_stub_vram` oraz `print_at` wywoływane przez ekrany Intro, Level Name oraz Game Over trwale nadpisywały pierwsze 960 bajtów (24 linie Mode F) obrazka tytułowego.
- **Rozwiązanie ([main.asm](main.asm))**:
  - Przeniesiono `STUB_VRAM` z `$4000` na dedykowany adres **`$8800`** (`$8800-$8BBF`, 960 B), w obszarze wolnej pamięci RAM powyżej buforów stagingowych świata.
  - Zaalokowano bufor `stub_vram_buf :960 dta 0` pod adresem `org STUB_VRAM`.
  - Bitmapa ekranu tytułowego pod adresem `$4000` jest teraz całkowicie odizolowana i pozostaje nienaruszona przez cały czas trwania gry.
  - Wszystkie 124 testy py65 przeszły pomyślnie (`124 passed in 9.79s`), pomyślna walidacja mapy pamięci w `make check_memory`.

## [2026-09-15] - Dynamiczne pieczenie ekranów z list obiektów (Uwolnienie >20 KB RAM)
- **Architektura Ping-Pong Staging Buffers i kompresja danych świata ([scripts/labirynt_builder.py](scripts/labirynt_builder.py), [main.asm](main.asm), [scenes/game.asm](scenes/game.asm), [engine/flame_collision.asm](engine/flame_collision.asm))**:
  - Wyeliminowano przechowywanie statycznych 440-bajtowych matryc VRAM oraz siatek kolizji dla każdego ekranu w pamięci RAM (co dla 20 ekranów pochłaniało ~18 KB, uniemożliwiając rozbudowę gry do 10 ekranów na poziom).
  - Wprowadzono kompaktową reprezentację ekranów jako list instancji obiektów: `screen_XXX_codes` (1 bajt na obiekt), `screen_XXX_coords` (1 spakowany bajt X/Y na obiekt) oraz `screen_XXX_obj_count`. Rozmiar danych 20 ekranów w pliku wynikowym spadł z 31,5 KB do ~1,5 KB danych maszynowych.
  - Zaalokowano podwójny bufor roboczy (`screen_buf_a_vram/blk`, `screen_buf_b_vram/blk`, łącznie 1760 bajtów) tuż za danymi świata w [main.asm](main.asm).
  - Zaimplementowano ultraszybką procedurę `bake_screen` w [scenes/game.asm](scenes/game.asm), która w czasie rzeczywistym renderuje kafelki obiektów oraz maski kolizji (blocking, interactive, secret) do wyznaczonego bufora stagingowego, z automatycznym pomijaniem obiektów zniszczonych na podstawie 256-bajtowej bitmaski `screen_obj_destroyed`.
  - Wprowadzono wskaźniki buforów ping-pong: `cur_left_vram_ptr`/`cur_left_blk_ptr` (lewy, schodzący ekran) oraz `incoming_screen_vram_ptr`/`incoming_screen_blk_ptr` (prawy, wjeżdżający ekran).
  - W procedurze `scroll_playfield_step` przy `incoming_col_idx == 40` wskaźniki buforów zamieniają się miejscami (swap), a kolejny ekran labiryntu jest natychmiast pieczony do zwolnionego bufora (~0.3 klatki, wykonywane raz na kilkaset klatek).
  - Zaktualizowano procedury kolizji [engine/flame_collision.asm](engine/flame_collision.asm) (`init_blocking_cols`, `shift_blocking_cols`, `erase_object_from_source_buffers`) do pracy na dynamicznych buforach stagingowych. Usunięto zbędne tablice backupowe sekretów, upraszczając `restore_all_secrets` do `rts`.
  - Przeniesiono moduły `scenes/text_utils.asm` oraz `scenes/intro.asm` do `LOW_CODE_ADDR` ($080B-$1D81), zabezpieczając segment `CODE_ADDR` przed kolizją z adresem `$4000`.
  - **Efekt**: Uwolniono ponad **20 KB** pamięci RAM (w tym 15,265 bajtów ciągłej wolnej przestrzeni `$845F-$BFFF`), co pozwala bez przeszkód rozbudować grę do 10+ ekranów na każdy labirynt.
- **Weryfikacja i testy ([tests/test_labirynt_builder.py](tests/test_labirynt_builder.py), [tests/test_scrolling.py](tests/test_scrolling.py), [tests/test_secret_collision.py](tests/test_secret_collision.py))**:
  - Zaktualizowano asercje testów emulatora `py65` do weryfikacji buforów stagingowych i list obiektów.
  - Wszystkie 124 testy jednostkowe przeszły pomyślnie (`124 passed in 10.22s`), pełna weryfikacja mapy pamięci zakończona sukcesem.

## [2026-09-15] - Relokacja pamięci dla 20 ekranów i rozszerzonego świata poniżej $BFFF
- **Relokacja DLIST, GAME_FONT oraz WORLD_DATA ([main.asm](main.asm), [Makefile](Makefile), [scripts/gen_animated_charset.py](scripts/gen_animated_charset.py), [engine/charset_anim.asm](engine/charset_anim.asm))**:
  - Rozwiązano błąd przekroczenia granicy pamięci RAM (`$BFFF`) po dodaniu kolejnych ekranów `CITY_03` i `CITY_04` (łącznie 20 ekranów i 3 labirynty, zajmujących wcześniej przestrzeń aż do `$C4B5`).
  - Przeniesiono `DLIST_ADDR` na adres **`$6610`** (316 B w luce po buforze siatki kolizji `BLOCKING_VRAM` `$6400-$660F`, mieszcząc się w całości w 1 KB bloku `$6400-$67FF`).
  - Przeniesiono czcionkę gry `GAME_FONT_ADDR` z `$6C00` na **`$6800`** (`$6800-$6BFF`, wyrównana do 1 KB dla `CHBASE`). Zaktualizowano parametr `--charset-base 0x6800` w `Makefile` i generatorze.
  - Przesunięto początek danych świata `WORLD_DATA_ADDR` z `$7000` na **`$6C00`**, zyskując 1024 bajty ciągłej przestrzeni RAM.
- **Przeniesienie tablic wymiarów obiektów do nieużywanego obszaru PMG ([scripts/labirynt_builder.py](scripts/labirynt_builder.py))**:
  - Przeniesiono generowanie 256-bajtowych tablic `obj_type_width` i `obj_type_height` (Structure-of-Arrays) z segmentu danych świata (`gen/world_data.asm`) do pliku `gen/world_obj_tiles.asm` dołączanego na końcu bloku `ENGINE`.
  - Tablice te ulokowano w bezpiecznym, nieużywanym przez DMA ANTIC obszarze bufora PMG single-line (`$20AE-$22AD`), z zachowaniem 82-bajtowego bufora bezpieczeństwa przed buforem pocisków ognia smoka (`$2300-$23FF`). Zysk w strefie world data: 512 bajtów.
  - W sumie odzyskano 1536 bajtów przestrzeni. Dane świata kończą się na `$BEDA`, z 293 bajtami bezpiecznego headroomu do limitu OS ROM `$BFFF`.
- **Weryfikacja testów ([tests/test_flame_collision.py](tests/test_flame_collision.py), [tests/test_status_bar.py](tests/test_status_bar.py), [tests/test_secret_collision.py](tests/test_secret_collision.py))**:
  - Zaktualizowano testy emulacji py65 do dynamicznego ustalania indeksu labiryntu zawierającego ekran `TOLEM_01`, dzięki czemu testy poprawnie przechodzą niezależnie od kolejności labiryntów ustalonej w `world/project.yaml`.
  - Wszystkie 124 testy jednostkowe przeszły pomyślnie (`124 passed in 18.12s`).

## [2026-09-15] - Zmiana kolejności labiryntów (Góra/Dół) w Labirynt Studio
- **UI Labirynt Studio ([labirynt_studio/ui/labyrinths_widget.py](labirynt_studio/ui/labyrinths_widget.py))**:
  - Dodano przyciski przesuwania labiryntów w górę (`▲`, `btn_lab_up`) oraz w dół (`▼`, `btn_lab_down`) obok przycisku "Usuń" w panelu zarządzania labiryntami.
  - Zaimplementowano metody `_move_labyrinth_up()` oraz `_move_labyrinth_down()`, które zamieniają sąsiednie elementy na liście `project.labyrinths`, odświeżają widok z zachowaniem zaznaczenia aktywnego labiryntu i emitują sygnał `labyrinths_changed` (oznaczający projekt jako zmodyfikowany `dirty`).
- **Respektowanie kolejności przez grę**:
  - Kompilator świata [scripts/labirynt_builder.py](scripts/labirynt_builder.py) generuje tablice labiryntów (`labyrinths_screen_count`, `labyrinths_screens_lo`/`hi`, `labyrinths_name_lo`/`hi`) dokładnie w kolejności listy `project.labyrinths` zdefiniowanej w `world/project.yaml`.
  - Silnik gry [scenes/game.asm](scenes/game.asm) rozpoczyna rozgrywkę od indeksu `current_level_idx = 0` (pierwszy labirynt na liście) i przy przejściu na kolejny poziom wykonuje `inc current_level_idx`, w pełni respektując kolejność ustaloną w edytorze.
- **Testy jednostkowe ([tests/test_labyrinths_widget.py](tests/test_labyrinths_widget.py))**:
  - Dodano test `test_labyrinths_widget_move_up_down` weryfikujący przestawianie pozycji labiryntów góra/dół, zachowanie na skrajnych pozycjach oraz emisję zdarzeń `labyrinths_changed`.
  - Wszystkie 124 testy jednostkowe przeszły pomyślnie (`124 passed`).


## [2026-09-15] - Relokacja segmentów pamięci RAM dla obsługi 3 poziomów poniżej $C000
- **Optymalizacja mapy pamięci RAM ([main.asm](main.asm), [Makefile](Makefile), [scripts/gen_animated_charset.py](scripts/gen_animated_charset.py))**:
  - Rozwiązano błąd przekroczenia granicy pamięci użytkownika (`Memory boundary violation: Segment 'FONT' ends at $C2D6, exceeding user RAM limit of $BFFF`) po dodaniu trzeciego poziomu (`LEVEL_01: Chmurny Gród`, ekrany `CITY_01`, `CITY_02`).
  - Przeniesiono segment czcionki tekstowej `FONT_ADDR` z `$7000` na **`$5C00`** (`$5C00-$5FFF`, 1024 bajty, wyrównana do 1 KB dla `CHBASE`).
  - Przeniesiono segment czcionki gry `GAME_FONT_ADDR` z `$7400` na **`$6C00`** (`$6C00-$6FFF`, 1024 bajty, wyrównana do 1 KB dla `CHBASE`), optymalnie wypełniając nieużywaną lukę za listami ekranowymi `DLIST_ADDR` ($6800-$693B).
  - Skonfigurowano `STUB_VRAM = $4000` (bufor tekstu 960 B dla ekranów statycznych Intro, Level Name i Game Over), wykorzystujący przestrzeń bufora obrazu tytułowego po zakończeniu sceny tytułowej.
  - Zwolniono 2048 bajtów ciągłej przestrzeni i przesunięto początek danych świata **`WORLD_DATA_ADDR` z `$7800` na `$7000`**.
  - Zaktualizowano parametr generatora `--charset-base 0x6C00` w `Makefile` oraz `scripts/gen_animated_charset.py`.
  - Dane świata 18 ekranów i 3 poziomów kończą się teraz bezpiecznie na `$BAD6`, pozostawiając **1321 bajtów wolnego zapasu** do granicy OS ROM (`$C000`).
- **Testy jednostkowe ([tests/test_charset_anim.py](tests/test_charset_anim.py))**:
  - Zaktualizowano testy animacji czcionek do dynamicznego pobierania adresu bazowego `labels['GAME_FONT_ADDR']` zamiast sztywnego `$7400`.
  - Wszystkie 123 testy jednostkowe przeszły pomyślnie (`123 passed`).


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