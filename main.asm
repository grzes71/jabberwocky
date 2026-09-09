; ==============================================================================
; JABBERWOCKY — Main Entry Point & State Machine
; Target: Atari 800XL / 65XE
; ==============================================================================

    icl 'hardware.asm'
    icl 'zeropage.asm'

; ---- Memory Map Equates ----
CODE_ADDR       = $3000
DLIST_ADDR      = $3E80
VRAM_ADDR       = $4000
STUB_VRAM       = $5C00             ; 960-byte text buffer ($5C00-$5FBF)
GAME_ACTION_VRAM = $6000            ; 440-byte action playfield ($6000-$61B7, 11 lines Antic 5)
GAME_STATUS_VRAM = $6200            ; 80-byte status bar ($6200-$624F, 2 lines Antic 2)
FONT_ADDR       = $7000             ; 1024-byte font ($7000-$73FF, 1KB aligned)

PM_ADDR         = $2000             ; 2KB aligned PMG buffer ($2000-$27FF)
M_ADDR          = PM_ADDR + $0300   ; Missiles buffer ($2300-$23FF, 256 bytes)
P0_ADDR         = PM_ADDR + $0400   ; Player 0 buffer
P1_ADDR         = PM_ADDR + $0500   ; Player 1 buffer
P2_ADDR         = PM_ADDR + $0600   ; Player 2 buffer

SPRITE_X        = 83                ; Horizontal position of Player 0
SPRITE_W        = 32                ; Width in color clocks (8 pixels * 4)
SPRITE_Y        = 32                ; Vertical start line
SPRITE_H        = 43                ; 43 lines high
SPRITE_COL      = $C4               ; Green color (Hue $C, Lum 4)

; ---- Game States ----
STATE_TITLE     = 0
STATE_INTRO     = 1
STATE_GAME      = 2
STATE_GAME_OVER = 3

; ==============================================================================
; CODE SEGMENT
; ==============================================================================
    org CODE_ADDR

start
    ; Enable interrupts for OS VBLANK / RTCLOK
    cli

    ; Set default text font ($7000)
    lda #>FONT_ADDR
    sta CHBASE
    sta CHBAS

    ; Initialize state machine
    lda #STATE_TITLE
    sta game_state
    lda #$FF
    sta prev_state
    lda #0
    sta fire_pressed
    sta prev_trig

main_loop
    ; Wait for next vertical blank
    lda RTCLOK+2
@wait_frame
    cmp RTCLOK+2
    beq @wait_frame

    ; Update inputs (joystick fire edge detection)
    jsr update_input

    ; Dispatch current state
    jsr dispatch_state

    jmp main_loop

; ---- Input Update Routine ----
update_input
    lda #0
    sta fire_pressed

    ; STRIG0 is updated by OS VBLANK: 0 = pressed, 1 = released
    lda STRIG0
    bne @btn_released

    ; Button is currently down (0)
    ldx prev_trig
    cpx #1
    bne @btn_done

    ; Edge transition detected (was 1, now 0)
    lda #1
    sta fire_pressed
    lda #0
    sta prev_trig
    rts

@btn_released
    lda #1
    sta prev_trig

@btn_done
    rts

; ---- State Machine Dispatcher ----
dispatch_state
    lda game_state
    cmp prev_state
    beq @run_current

    ; State transition: run new state's _init
    sta prev_state
    asl
    tax
    lda scene_init_tbl,x
    sta jmp_target
    lda scene_init_tbl+1,x
    sta jmp_target+1
    jsr call_target
    rts

@run_current
    lda game_state
    asl
    tax
    lda scene_run_tbl,x
    sta jmp_target
    lda scene_run_tbl+1,x
    sta jmp_target+1
    jsr call_target
    rts

call_target
    jmp (jmp_target)

; ---- State Machine Variables & Jump Tables ----
game_state      dta STATE_TITLE
prev_state      dta $FF
fire_pressed    dta 0
prev_trig       dta 0
jmp_target      dta a(0)

scene_init_tbl
    dta a(title_init)
    dta a(intro_init)
    dta a(game_init)
    dta a(gameover_init)

scene_run_tbl
    dta a(title_run)
    dta a(intro_run)
    dta a(game_run)
    dta a(gameover_run)

; ---- Include Scene Modules ----
    icl 'scenes/text_utils.asm'
    icl 'scenes/title.asm'
    icl 'scenes/intro.asm'
    icl 'scenes/game.asm'
    icl 'scenes/gameover.asm'

; ---- Include Generated Assets ----
    icl 'gen/dragon_sprite.asm'

; ==============================================================================
; DISPLAY LIST SEGMENTS (within $3E80 - $3FFF, never crossing 1KB boundary)
; ==============================================================================
    org DLIST_ADDR

; Display list for Title Screen (ANTIC Mode F, 320x175)
dlist_title
    dta DL_BLANK8
    dta DL_BLANK8
    dta DL_BLANK8

    ; First 4KB segment: 102 lines of ANTIC Mode F (102 * 40 = 4080 bytes)
    dta DL_MODE_F | DL_LMS, a(VRAM_ADDR)
    :101 dta DL_MODE_F

    ; Second 4KB segment (LMS at $5000): 73 lines of ANTIC Mode F (73 * 40 = 2920 bytes)
    dta DL_MODE_F | DL_LMS, a(VRAM_ADDR + $1000)
    :72 dta DL_MODE_F

    dta DL_JVB, a(dlist_title)

; Display list for Stub Text Screens (ANTIC Mode 2, 40x24)
dlist_stub
    dta DL_BLANK8
    dta DL_BLANK8
    dta DL_BLANK8

    dta DL_MODE_2 | DL_LMS, a(STUB_VRAM)
    :23 dta DL_MODE_2

    dta DL_JVB, a(dlist_stub)

; Display list for Intro Scene (ANTIC Mode 2, 40x24 with 4 DLIs before text lines)
dlist_intro
    dta DL_BLANK8
    dta DL_BLANK8
    dta DL_BLANK8

    dta DL_MODE_2 | DL_LMS, a(STUB_VRAM)
    :7 dta DL_MODE_2
    dta DL_MODE_2 | DL_DLI      ; Row 8: DLI 1 triggers before row 9
    dta DL_MODE_2               ; Row 9: Text line 1
    dta DL_MODE_2 | DL_DLI      ; Row 10: DLI 2 triggers before row 11
    dta DL_MODE_2               ; Row 11: Text line 2
    dta DL_MODE_2 | DL_DLI      ; Row 12: DLI 3 triggers before row 13
    dta DL_MODE_2               ; Row 13: Text line 3
    dta DL_MODE_2 | DL_DLI      ; Row 14: DLI 4 triggers before row 15
    dta DL_MODE_2               ; Row 15: Text line 4
    :8 dta DL_MODE_2            ; Rows 16..23

    dta DL_JVB, a(dlist_intro)

; Display list for Main Game Screen (1 line ANTIC 2 + 11 lines ANTIC 5 + 1 line ANTIC 2)
dlist_game
    dta DL_BLANK8
    dta DL_BLANK8
    dta DL_BLANK8

    ; Top status bar: 1 line of ANTIC Mode 2 (40x1, 8 scanlines)
    dta DL_MODE_2 | DL_LMS, a(GAME_STATUS_VRAM)

    ; Action playfield: 11 lines of ANTIC Mode 5 (40x11, 16 scanlines each)
    dta DL_MODE_5 | DL_LMS, a(GAME_ACTION_VRAM)
    :10 dta DL_MODE_5

    ; Bottom status bar: 1 line of ANTIC Mode 2 (40x1, 8 scanlines)
    dta DL_MODE_2 | DL_LMS, a(GAME_STATUS_VRAM + 40)

    dta DL_JVB, a(dlist_game)

; ==============================================================================
; SCREEN MEMORY (VRAM)
; Title image: 7,016 bytes ($4000-$5B67)
; ==============================================================================
    org VRAM_ADDR
    ins 'gen/title.bin'

; ==============================================================================
; DEFAULT FONT DATA
; 1024-byte character set ($7000-$73FF, 1KB aligned)
; ==============================================================================
    org FONT_ADDR
font_data
    ins 'fonts/text.fnt'

; ==============================================================================
; RUN ADDRESS VECTOR
; ==============================================================================
    org RUNAD
    dta a(start)
