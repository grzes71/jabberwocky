; ==============================================================================
; SCENES/TITLE.ASM — Title Screen Scene
; Target: ANTIC Mode F (320x175) + 3-Player PMG
; ==============================================================================

title_init
    ; Blank screen DMA during setup
    lda #0
    sta SDMCTL
    sta DMACTL

    ; Reset GTIA PMG latches
    sta GRACTL
    sta GRAFP0
    sta GRAFP1
    sta GRAFP2
    sta GRAFP3
    sta GRAFM

    ; Clear PMG memory area ($2000-$27FF, 2KB)
    tax
@   sta PM_ADDR,x
    sta PM_ADDR+$100,x
    sta PM_ADDR+$200,x
    sta PM_ADDR+$300,x
    sta PM_ADDR+$400,x
    sta PM_ADDR+$500,x
    sta PM_ADDR+$600,x
    sta PM_ADDR+$700,x
    inx
    bne @-

    ; Draw 43-line sprite pattern into Player 0, 1, and 2
    ldx #0
    lda #$FF
@   sta P0_ADDR + SPRITE_Y,x
    sta P1_ADDR + SPRITE_Y,x
    sta P2_ADDR + SPRITE_Y,x
    inx
    cpx #SPRITE_H
    bne @-

    ; Set PMBASE (page $20)
    lda #>PM_ADDR
    sta PMBASE

    ; Configure Player positions: side by side (X, X+32, X+64)
    lda #SPRITE_X
    sta HPOSP0
    lda #SPRITE_X + SPRITE_W
    sta HPOSP1
    lda #SPRITE_X + (SPRITE_W * 2)
    sta HPOSP2

    ; Quadruple width (x4 = 3) for all 3 players
    lda #3
    sta SIZEP0
    sta SIZEP1
    sta SIZEP2

    ; Green color for all 3 players
    lda #SPRITE_COL
    sta PCOLR0
    sta COLPM0
    sta PCOLR1
    sta COLPM1
    sta PCOLR2
    sta COLPM2

    ; Priority: Player 0-3 in front of playfield
    lda #$01
    sta GPRIOR
    sta PRIOR

    ; Enable player display in GTIA
    lda #2
    sta GRACTL
    sta HITCLR

    ; Set Display List pointer (shadow and hardware)
    lda #<dlist_title
    sta SDLSTL
    sta DLISTL
    lda #>dlist_title
    sta SDLSTH
    sta DLISTH

    ; Colors for Graphics 8 / ANTIC Mode F:
    lda #$ca
    sta COLOR2
    sta COLPF2
    
    lda #$c0
    sta COLOR4

    lda #$00
    sta COLOR1
    sta COLPF1
    sta COLBK

    ; Enable inverse video in CHACTL (bit 1 = 1)
    lda #2
    sta CHACTL

    ; Clear 48-byte scroll VRAM buffer with inverted spaces ($80)
    lda #$80
    ldx #TITLE_SCROLL_VRAM_LEN - 1
@   sta title_scroll_vram,x
    dex
    bpl @-

    ; Reset scroll ticker state
    lda #0
    sta title_scroll_idx
    sta title_scroll_delay
    lda #3
    sta title_scroll_fine

    ; Check if slide-up effect is needed (only on first entry from STATE_INTRO)
    lda title_need_slide
    beq @direct_title_init

    ; ---- Initialize Slide-Up Animation ----
    lda #0
    sta title_need_slide        ; Consume flag (runs only once!)
    sta title_slide_lines       ; 0 visible lines initially
    sta title_slide_buf_idx     ; Start on buffer 0
    lda #1
    sta title_slide_active

    ; Build initial frame 0 display list into buffer 0 ($6000)
    lda #<TITLE_SLIDE_DLIST0
    sta PTR_DST
    lda #>TITLE_SLIDE_DLIST0
    sta PTR_DST+1
    jsr build_slide_dlist

    ; Set ANTIC Display List to slide buffer
    lda #<TITLE_SLIDE_DLIST0
    sta SDLSTL
    sta DLISTL
    lda #>TITLE_SLIDE_DLIST0
    sta SDLSTH
    sta DLISTH

    ; Turn off GTIA PMG players during slide
    lda #0
    sta GRACTL

    ; Enable standard playfield DMA only (no PMG: $22)
    lda #$22
    sta SDMCTL
    sta DMACTL

    ; VBLANK only ($40) — DLI disabled during slide
    lda #$40
    sta NMIEN
    rts

@direct_title_init
    jsr title_finish_slide
    rts

; ==============================================================================
; TITLE_FINISH_SLIDE — Ends slide and restores normal Title DLIST & PMG display
; ==============================================================================
title_finish_slide
    lda #0
    sta title_slide_active

    ; Set Display List pointer (shadow and hardware)
    lda #<dlist_title
    sta SDLSTL
    sta DLISTL
    lda #>dlist_title
    sta SDLSTH
    sta DLISTH

    ; Enable GTIA PMG player display
    lda #2
    sta GRACTL
    sta HITCLR

    ; Enable playfield DMA + single-line PMG + Player DMA (%00111010 = $3A)
    lda #$3A
    sta SDMCTL
    sta DMACTL

    ; Set DLI vector for Title scroll line
    lda #<dli_title_scroll
    sta VDSLST
    lda #>dli_title_scroll
    sta VDSLST+1

    ; Enable NMI: VBLANK ($40) + DLI ($80) = $C0
    lda #$C0
    sta NMIEN
    rts

title_run
    lda title_slide_active
    beq @normal_run

    ; ---- Slide-up is active ----
    lda fire_pressed
    beq @do_slide_step

    ; User pressed FIRE during slide: skip slide directly to STATE_GAME
    lda #0
    sta fire_pressed
    jsr title_finish_slide
    lda #$40                    ; VBLANK only, DLI disabled
    sta NMIEN
    lda #STATE_GAME
    sta game_state
    rts

@do_slide_step
    jsr update_title_slide
    rts

@normal_run
    ; Update smooth scrolling ticker (once per frame)
    jsr update_title_scroll

    lda fire_pressed
    beq @+
    lda #0
    sta fire_pressed

    ; Disable DLI before leaving scene
    lda #$40                    ; VBLANK only, DLI disabled
    sta NMIEN

    lda #STATE_GAME
    sta game_state
@   rts

; ==============================================================================
; UPDATE_TITLE_SLIDE — Advances visible lines by TITLE_SLIDE_STEP each frame
; ==============================================================================
update_title_slide
    lda title_slide_lines
    clc
    adc #TITLE_SLIDE_STEP
    cmp #TITLE_TOTAL_LINES
    bcc @continue_slide

    ; Slide complete: transition to normal static title screen
    jsr title_finish_slide
    rts

@continue_slide
    sta title_slide_lines

    ; Toggle double-buffer index
    lda title_slide_buf_idx
    eor #1
    sta title_slide_buf_idx
    bne @use_buf1

    lda #<TITLE_SLIDE_DLIST0
    sta PTR_DST
    lda #>TITLE_SLIDE_DLIST0
    sta PTR_DST+1
    jmp @do_build

@use_buf1
    lda #<TITLE_SLIDE_DLIST1
    sta PTR_DST
    lda #>TITLE_SLIDE_DLIST1
    sta PTR_DST+1

@do_build
    jsr build_slide_dlist

    ; Update ANTIC display list pointer to newly prepared buffer
    lda PTR_DST
    sta SDLSTL
    sta DLISTL
    lda PTR_DST+1
    sta SDLSTH
    sta DLISTH
    rts

; ==============================================================================
; BUILD_SLIDE_DLIST — Dynamic Display List Generator for Slide-Up
; Total scanlines in frame = 199 (constant throughout slide)
; Top blanks: 199 - title_slide_lines scanlines
; Followed by title_slide_lines of ANTIC Mode F, then DL_JVB.
; ==============================================================================
build_slide_dlist
    ldy #0

    ; 1. Calculate top blank scanlines: (199 - title_slide_lines)
    lda #199
    sec
    sbc title_slide_lines
    tax                         ; X = blank scanlines remaining (0..199)

@b8_loop
    cpx #8
    bcc @b_rem
    lda #DL_BLANK8
    sta (PTR_DST),y
    iny
    txa
    sec
    sbc #8
    tax
    jmp @b8_loop

@b_rem
    cpx #0
    beq @do_content
    ; X in range 1..7: opcode is (X - 1) << 4
    dex                         ; 0..6
    txa
    asl
    asl
    asl
    asl
    sta (PTR_DST),y
    iny

@do_content
    lda title_slide_lines
    beq @put_jvb

    ; First line with LMS: DL_MODE_F | DL_LMS, a(VRAM_ADDR)
    lda #DL_MODE_F | DL_LMS
    sta (PTR_DST),y
    iny
    lda #<VRAM_ADDR
    sta (PTR_DST),y
    iny
    lda #>VRAM_ADDR
    sta (PTR_DST),y
    iny

    ; First segment Mode F lines: min(title_slide_lines - 1, 101)
    lda title_slide_lines
    sec
    sbc #1
    cmp #101
    bcc @seg1_cnt
    lda #101
@seg1_cnt
    tax
    beq @check_seg2
    lda #DL_MODE_F
@seg1_loop
    sta (PTR_DST),y
    iny
    dex
    bne @seg1_loop

@check_seg2
    lda title_slide_lines
    cmp #103
    bcc @put_jvb

    ; Second segment LMS: DL_MODE_F | DL_LMS, a(VRAM_ADDR + $1000)
    lda #DL_MODE_F | DL_LMS
    sta (PTR_DST),y
    iny
    lda #<(VRAM_ADDR + $1000)
    sta (PTR_DST),y
    iny
    lda #>(VRAM_ADDR + $1000)
    sta (PTR_DST),y
    iny

    ; Second segment Mode F lines: (title_slide_lines - 103)
    lda title_slide_lines
    sec
    sbc #103
    tax
    beq @put_jvb
    lda #DL_MODE_F
@seg2_loop
    sta (PTR_DST),y
    iny
    dex
    bne @seg2_loop

@put_jvb
    lda #DL_JVB
    sta (PTR_DST),y
    iny
    lda PTR_DST
    sta (PTR_DST),y
    iny
    lda PTR_DST+1
    sta (PTR_DST),y
    rts

; ==============================================================================
; DLI ROUTINE — Triggered on DL_BLANK1 right before ANTIC Mode 2 scroll line
; Sets fine horizontal scroll (HSCROL) and playfield colors:
; In ANTIC Mode 2:
;   Normal text: COLPF1 = text, COLPF2 = background
;   Inverse text: COLPF2 = text, COLPF1 = background (or vice-versa in hardware)
; By setting COLPF1 and COLPF2:
;   Background of line (uninverted field) = COLBK (border)
;   Inverse field = Green ($C6)
; ==============================================================================
dli_title_scroll
    pha                         ; Save accumulator
    sta WSYNC                   ; Wait for horizontal sync

    lda title_scroll_fine       ; Load fine scroll offset (0..3)
    sta HSCROL                  ; Set ANTIC fine horizontal scroll

    pla                         ; Restore accumulator
    rti

; ==============================================================================
; SCROLL TICKER UPDATE ROUTINE
; Mode 2: 1 char = 4 color clocks (fine scroll 3 -> 2 -> 1 -> 0)
; ==============================================================================
update_title_scroll
    ; Optional frame delay to control scroll speed (1 = every frame)
    dec title_scroll_delay
    bne @done
    lda #TITLE_SCROLL_SPEED
    sta title_scroll_delay

    ; Decrement fine scroll
    lda title_scroll_fine
    sec
    sbc #1
    bpl @save_fine

    ; Wrap fine scroll: reset to 3 color clocks
    lda #3
    sta title_scroll_fine

    ; Coarse shift: shift 48-byte VRAM left by 1 position
    ldx #0
@shift_loop
    lda title_scroll_vram + 1,x
    sta title_scroll_vram,x
    inx
    cpx #TITLE_SCROLL_VRAM_LEN - 1
    bne @shift_loop

    ; Fetch next character from scroll text
    ldx title_scroll_idx
    lda title_scroll_text,x
    sta title_scroll_vram + TITLE_SCROLL_VRAM_LEN - 1

    ; Advance text index and loop if end reached
    inx
    cpx #TITLE_SCROLL_TEXT_LEN
    bcc @save_idx
    ldx #0                      ; Loop back to start
@save_idx
    stx title_scroll_idx
    rts

@save_fine
    sta title_scroll_fine
@done
    rts

; ==============================================================================
; CONSTANTS & BUFFERS
; ==============================================================================
TITLE_SCROLL_VRAM_LEN   = 48    ; ANTIC normal width fetches 48 bytes with DL_HSCROL
TITLE_SCROLL_SPEED      = 1     ; Step every 1 frame (smooth 50/60 fps)
TITLE_SLIDE_STEP        = 2     ; 2 scanlines per frame (~1.7s total slide)
TITLE_TOTAL_LINES       = 175   ; Mode F image height
TITLE_SLIDE_DLIST0      = $6000 ; Slide DLIST double-buffer 0 (256 B, page aligned)
TITLE_SLIDE_DLIST1      = $6100 ; Slide DLIST double-buffer 1 (256 B, page aligned)

title_scroll_fine       dta 3
title_scroll_delay      dta TITLE_SCROLL_SPEED
title_scroll_idx        dta 0

title_need_slide        dta 1   ; 1 = slide up on first entry from STATE_INTRO, 0 = direct
title_slide_active      dta 0   ; 1 during active slide animation
title_slide_lines       dta 0   ; Current visible Mode F lines (0..175)
title_slide_buf_idx     dta 0   ; Double-buffer toggle (0 or 1)

; 48-byte VRAM buffer for Mode 2 scroll line
title_scroll_vram
    :TITLE_SCROLL_VRAM_LEN dta 0

; Text data included from generated text compiler
    icl 'gen/title_scroll_text.asm'


