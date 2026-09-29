; ==============================================================================
; ENGINE/MUSIC.ASM — CMC Audio Player Wrapper & State Manager
; Target: Atari 800XL / 65XE (PAL 50Hz)
; ==============================================================================

MUSIC_DATA_ADDR = $9000
CMC_PLAYER_ADDR = $9A00

; Subsong IDs (0-based indexing confirmed by CMC player code):
; Subsong 1 (02:34) -> index 0: Game Over / Reserve
; Subsong 2 (04:45) -> index 1: Gameplay
; Subsong 3 (02:47) -> index 2: Title Screen
MUSIC_GAME_OVER = 0
MUSIC_GAMEPLAY  = 1
MUSIC_TITLE     = 2
MUSIC_NONE      = $FF

music_current_song  dta MUSIC_NONE
music_active        dta 0

; ==============================================================================
; Music_PlaySong — Public API to play a subsong
; Input:  A = song index (MUSIC_GAME_OVER=0, MUSIC_GAMEPLAY=1, MUSIC_TITLE=2)
; Output: A, X, Y preserved
; ==============================================================================
.proc Music_PlaySong
    cmp music_current_song
    beq @already_playing

    cmp #MUSIC_NONE
    beq @do_stop

    sta music_current_song

    pha                     ; preserve input A (song index)
    txa
    pha                     ; preserve input X
    tya
    pha                     ; preserve input Y

    ; Step 1: Initialize base address of music data module (A=$70)
    lda #$70
    ldx #<MUSIC_DATA_ADDR
    ldy #>MUSIC_DATA_ADDR
    jsr cmc_player.init

    ; Step 2: Select and start subsong (A=$00, X=subsong_id)
    ldx music_current_song  ; reload verified song index from RAM
    lda #$00
    jsr cmc_player.init

    lda #1
    sta music_active

    pla
    tay                     ; restore Y
    pla
    tax                     ; restore X
    pla                     ; restore A
@already_playing:
    rts

@do_stop:
    jmp Music_Stop
.endp

; ==============================================================================
; Music_Update — Public API called once per frame (50 Hz)
; Updates audio registers via cmc_player.play
; Input:  None
; Output: A, X, Y preserved
; ==============================================================================
.proc Music_Update
    pha                     ; preserve A unconditionally
    lda music_active
    beq @exit_pop

    txa
    pha                     ; preserve X
    tya
    pha                     ; preserve Y

    jsr cmc_player.play

    pla
    tay                     ; restore Y
    pla
    tax                     ; restore X
@exit_pop:
    pla                     ; restore A
    rts
.endp

; ==============================================================================
; Music_Stop — Public API to stop music and silence POKEY
; Input:  None
; Output: A, X, Y preserved
; ==============================================================================
.proc Music_Stop
    pha                     ; preserve A
    txa
    pha                     ; preserve X
    tya
    pha                     ; preserve Y

    lda #0
    sta music_active
    lda #MUSIC_NONE
    sta music_current_song

    ; Silence POKEY using CMC mute command (A=$40)
    lda #$40
    jsr cmc_player.init

    pla
    tay                     ; restore Y
    pla
    tax                     ; restore X
    pla                     ; restore A
    rts
.endp
