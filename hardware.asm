; ==============================================================================
; HARDWARE.ASM — Atari 800XL / 65XE Equates and Constants
; Target: Atari XL/XE (ANTIC, GTIA, POKEY, PIA, OS Shadows & Vectors)
; ==============================================================================

; --- GTIA Hardware Registers (Write) ---
HPOSP0      = $D000     ; Pozycja pozioma gracza 0
HPOSP1      = $D001     ; Pozycja pozioma gracza 1
HPOSP2      = $D002     ; Pozycja pozioma gracza 2
HPOSP3      = $D003     ; Pozycja pozioma gracza 3
HPOSM0      = $D004     ; Pozycja pozioma pocisku 0
HPOSM1      = $D005     ; Pozycja pozioma pocisku 1
HPOSM2      = $D006     ; Pozycja pozioma pocisku 2
HPOSM3      = $D007     ; Pozycja pozioma pocisku 3
SIZEP0      = $D008     ; Rozmiar gracza 0 (00=1x, 01=2x, 11=4x)
SIZEP1      = $D009     ; Rozmiar gracza 1
SIZEP2      = $D00A     ; Rozmiar gracza 2
SIZEP3      = $D00B     ; Rozmiar gracza 3
SIZEM       = $D00C     ; Rozmiar pocisków (bity 0..7)
GRAFP0      = $D00D     ; Rejestr grafiki gracza 0 (bezpośredni)
GRAFP1      = $D00E     ; Rejestr grafiki gracza 1 (bezpośredni)
GRAFP2      = $D00F     ; Rejestr grafiki gracza 2 (bezpośredni)
GRAFP3      = $D010     ; Rejestr grafiki gracza 3 (bezpośredni)
GRAFM       = $D011     ; Rejestr grafiki pocisków (bezpośredni)
COLPM0      = $D012     ; Rejestr koloru gracza/pocisku 0
COLPM1      = $D013     ; Rejestr koloru gracza/pocisku 1
COLPM2      = $D014     ; Rejestr koloru gracza/pocisku 2
COLPM3      = $D015     ; Rejestr koloru gracza/pocisku 3
COLPF0      = $D016     ; Kolor pola gry 0 (indeks 1 w ANTIC E/F)
COLPF1      = $D017     ; Kolor pola gry 1 (indeks 2 / jasność w Gr.8)
COLPF2      = $D018     ; Kolor pola gry 2 (indeks 3 / tło w Gr.0 i Gr.8)
COLPF3      = $D019     ; Kolor pola gry 3
COLBK       = $D01A     ; Kolor tła / ramki (COLBAK)
PRIOR       = $D01B     ; Priorytety GTIA i tryb 5. gracza
VDELAY      = $D01C     ; Opóźnienie pionowe PMG
GRACTL      = $D01D     ; Włączenie PMG DMA (bit 1=P/M, bit 0=missiles)
HITCLR      = $D01E     ; Kasowanie rejestrów kolizji
CONSOL      = $D01F     ; Przyciski konsoli (START/SELECT/OPTION)

; --- GTIA Hardware Registers (Read) ---
M0PF        = $D000     ; Kolizja missile 0 z playfieldem
M1PF        = $D001     ; Kolizja missile 1 z playfieldem
M2PF        = $D002     ; Kolizja missile 2 z playfieldem
M3PF        = $D003     ; Kolizja missile 3 z playfieldem
P0PF        = $D004     ; Kolizja player 0 z playfieldem
P1PF        = $D005     ; Kolizja player 1 z playfieldem
P2PF        = $D006     ; Kolizja player 2 z playfieldem
P3PF        = $D007     ; Kolizja player 3 z playfieldem
M0PL        = $D008     ; Kolizja missile 0 z graczami
M1PL        = $D009     ; Kolizja missile 1 z graczami
M2PL        = $D00A     ; Kolizja missile 2 z graczami
M3PL        = $D00B     ; Kolizja missile 3 z graczami
P0PL        = $D00C     ; Kolizja player 0 z graczami
P1PL        = $D00D     ; Kolizja player 1 z graczami
P2PL        = $D00E     ; Kolizja player 2 z graczami
P3PL        = $D00F     ; Kolizja player 3 z graczami
TRIG0       = $D010     ; Przycisk FIRE joysticka 0 (bit 0=0 wciśnięty)
TRIG1       = $D011     ; Przycisk FIRE joysticka 1
TRIG2       = $D012     ; Przycisk FIRE joysticka 2
TRIG3       = $D013     ; Przycisk FIRE joysticka 3

; --- PIA Hardware Registers ---
PORTA       = $D300     ; Port joysticków 0 i 1 (kierunki)
PORTB       = $D301     ; Bankowanie pamięci i włączenie OS ROM

; --- ANTIC Hardware Registers ---
DMACTL      = $D400     ; Bezpośrednia kontrola DMA ANTIC
CHACTL      = $D401     ; Kontrola znaków (inwersja, migotanie)
DLISTL      = $D402     ; Młodszy bajt wskaźnika Display List
DLISTH      = $D403     ; Starszy bajt wskaźnika Display List
HSCROL      = $D404     ; Poziomy fine scroll (0..15 color clocks)
VSCROL      = $D405     ; Pionowy fine scroll (0..7 scan lines)
PMBASE      = $D407     ; Baza pamięci PMG (strona, wyrównanie do 1K/2K)
CHBASE      = $D409     ; Baza zestawu znaków (strona, np. $E0 dla ROM)
WSYNC       = $D40A     ; Wait for Horizontal Sync
VCOUNT      = $D40B     ; Licznik linii rastra
NMIEN       = $D40E     ; Włączenie przerwań NMI (DLI, VBI)
NMIST       = $D40F     ; Rejestr statusu NMI

; --- POKEY Hardware Registers ---
AUDF1       = $D200     ; Częstotliwość kanału 1
AUDC1       = $D201     ; Głośność i barwa kanału 1
AUDF2       = $D202     ; Częstotliwość kanału 2
AUDC2       = $D203     ; Głośność i barwa kanału 2
AUDF3       = $D204     ; Częstotliwość kanału 3
AUDC3       = $D205     ; Głośność i barwa kanału 3
AUDF4       = $D206     ; Częstotliwość kanału 4
AUDC4       = $D207     ; Głośność i barwa kanału 4
AUDCTL      = $D208     ; Kontrola zegarów i filtrów POKEY
IRQEN       = $D20E     ; Włączenie przerwań IRQ z POKEY

; --- OS Shadow Registers & Vectors ---
RTCLOK      = $0012     ; Licznik klatek VBLANK (3 bajty: $12, $13, $14)
ATRACT      = $004D     ; Rejestr Attract Mode (0 = wyłączony)
VDSLST      = $0200     ; Wektor przerwania DLI
VVBLKD      = $0222     ; Wektor VBI Deferred
VVBLKI      = $0224     ; Wektor VBI Immediate
SDMCTL      = $022F     ; Cień DMACTL
SDLSTL      = $0230     ; Cień DLISTL
SDLSTH      = $0231     ; Cień DLISTH
STICK0      = $0278     ; Cień kierunków joysticka 0
STICK1      = $0279     ; Cień kierunków joysticka 1
STRIG0      = $0284     ; Cień przycisku FIRE 0 (0=wciśnięty, 1=zwolniony)
STRIG1      = $0285     ; Cień przycisku FIRE 1
GPRIOR      = $026F     ; Cień PRIOR
PCOLR0      = $02C0     ; Cień COLPM0
PCOLR1      = $02C1     ; Cień COLPM1
PCOLR2      = $02C2     ; Cień COLPM2
PCOLR3      = $02C3     ; Cień COLPM3
COLOR0      = $02C4     ; Cień COLPF0
COLOR1      = $02C5     ; Cień COLPF1
COLOR2      = $02C6     ; Cień COLPF2
COLOR3      = $02C7     ; Cień COLPF3
COLOR4      = $02C8     ; Cień COLBK
CHBAS       = $02F4     ; Cień CHBASE
CH          = $02FC     ; Kod ostatnio wciśniętego klawisza ($FF = brak)
RUNAD       = $02E0     ; Wektor uruchomienia pliku binarnego DOS
INITAD      = $02E2     ; Wektor inicjalizacji pliku binarnego DOS

; --- OS ROM Entry Points ---
SETVBV      = $E45C     ; Ustawienie wektora VBLANK (A=tryb, X/Y=adres)
SYSVBV      = $E45F     ; Wyjście z VBLANK Stage 1 (Immediate)
XITVBV      = $E462     ; Wyjście z VBLANK Stage 2 (Deferred)

; --- ANTIC Display List Instructions & Modes ---
DL_BLANK1   = $00       ; 1 pusta linia rastra
DL_BLANK2   = $10       ; 2 puste linie
DL_BLANK3   = $20       ; 3 puste linie
DL_BLANK4   = $30       ; 4 puste linie
DL_BLANK5   = $40       ; 5 pustych linii
DL_BLANK6   = $50       ; 6 pustych linii
DL_BLANK7   = $60       ; 7 pustych linii
DL_BLANK8   = $70       ; 8 pustych linii

DL_MODE_2   = $02       ; ANTIC 2 (tekst 40x24, Gr.0)
DL_MODE_3   = $03       ; ANTIC 3 (tekst 40x24 z descenderami)
DL_MODE_4   = $04       ; ANTIC 4 (tekst 40x24, 4 kolory, Gr.12/4)
DL_MODE_5   = $05       ; ANTIC 5 (tekst 40x12, 4 kolory, Gr.13/5)
DL_MODE_6   = $06       ; ANTIC 6 (tekst 20x24, 5 kolorów, Gr.1)
DL_MODE_7   = $07       ; ANTIC 7 (tekst 20x12, 5 kolorów, Gr.2)
DL_MODE_8   = $08       ; ANTIC 8 (grafika 40x24, 4 kolory, Gr.3)
DL_MODE_9   = $09       ; ANTIC 9 (grafika 80x48, 2 kolory, Gr.4)
DL_MODE_A   = $0A       ; ANTIC A (grafika 80x48, 4 kolory, Gr.5)
DL_MODE_B   = $0B       ; ANTIC B (grafika 160x96, 2 kolory, Gr.6)
DL_MODE_C   = $0C       ; ANTIC C (grafika 160x192, 2 kolory, Gr.14)
DL_MODE_D   = $0D       ; ANTIC D (grafika 160x96, 4 kolory, Gr.7)
DL_MODE_E   = $0E       ; ANTIC E (grafika 160x192, 4 kolory, Gr.15)
DL_MODE_F   = $0F       ; ANTIC F (grafika 320x192, 2 kolory, Gr.8)

DL_HSCROL   = $10       ; Modyfikator: włączenie horizontal scroll
DL_VSCROL   = $20       ; Modyfikator: włączenie vertical scroll
DL_LMS      = $40       ; Modyfikator: Load Memory Scan (+ 2 bajty adresu VRAM)
DL_DLI      = $80       ; Modyfikator: Display List Interrupt na tej linii
DL_JMP      = $01       ; Skok pod nowy adres DLIST (+ 2 bajty adresu)
DL_JVB      = $41       ; Skok pod adres DLIST i oczekiwanie na VBLANK
