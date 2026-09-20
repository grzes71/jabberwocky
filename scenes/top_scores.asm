; ==============================================================================
; SCENES/TOP_SCORES.ASM — Top 10 High Scores & Joystick Name Entry
; Target: ANTIC Mode 2 (40x24 text) on STUB_VRAM ($B000)
; ==============================================================================

TOP_SCORES_COUNT    = 10
NAME_LEN            = 5
NAME_CHARSET_LEN    = 37

NAME_REPEAT_INIT    = 12        ; Initial delay before auto-repeat (frames)
NAME_REPEAT_RATE    = 4         ; Auto-repeat interval (frames)

; ==============================================================================
; TOP SCORES SCENE INITIALIZATION & EXECUTION
; ==============================================================================

top_scores_init
    ; Check if this game's final score has already been processed
    lda score_processed
    bne @ts_show_table

    ; First time entering from GAME OVER: check if player qualifies for Top 10
    jsr check_score_qualified
    bcc @ts_not_qualified

    ; Player qualifies! Mark score as processed and transition to name entry
    lda #1
    sta score_processed
    lda #STATE_ENTER_NAME
    sta game_state
    rts

@ts_not_qualified
    lda #1
    sta score_processed

@ts_show_table
    ; Blank DMA during reconfiguration
    lda #0
    sta SDMCTL
    sta DMACTL

    ; Reset PMG
    jsr disable_pmg

    ; Use default text font
    lda #>FONT_ADDR
    sta CHBASE
    sta CHBAS

    ; Set DLIST pointer to top scores display list
    lda #<dlist_top_scores
    sta SDLSTL
    sta DLISTL
    lda #>dlist_top_scores
    sta SDLSTH
    sta DLISTH

    ; Set colors: Deep blue background ($70) and border ($70), bright white text ($0E)
    lda #$70
    sta COLOR2
    sta COLPF2

    lda #$0E
    sta COLOR1
    sta COLPF1

    lda #$70
    sta COLOR4
    sta COLBK

    ; Clear text screen
    jsr clear_stub_vram

    ; Render Top Scores header
    lda #<ts_txt_title
    sta PTR_SRC
    lda #>ts_txt_title
    sta PTR_SRC+1
    ldx #0
    ldy #14
    jsr print_at

    lda #<ts_txt_subtitle
    sta PTR_SRC
    lda #>ts_txt_subtitle
    sta PTR_SRC+1
    ldx #1
    ldy #15
    jsr print_at

    lda #<ts_txt_col_headers
    sta PTR_SRC
    lda #>ts_txt_col_headers
    sta PTR_SRC+1
    ldx #2
    ldy #12
    jsr print_at

    ; Render 10 high-score rows (Rows 3..12)
    ldx #0
@ts_render_rows_loop
    stx ts_render_idx
    jsr render_top_score_row
    ldx ts_render_idx
    inx
    cpx #TOP_SCORES_COUNT
    bcc @ts_render_rows_loop

    ; Render prompt: ">> PRESS FIRE TO CONTINUE <<"
    lda #<ts_txt_prompt
    sta PTR_SRC
    lda #>ts_txt_prompt
    sta PTR_SRC+1
    ldx #13
    ldy #6
    jsr print_at

    ; Enable playfield DMA ($22)
    lda #$22
    sta SDMCTL
    sta DMACTL
    rts

top_scores_run
    lda fire_pressed
    beq @ts_run_rts
    lda #0
    sta fire_pressed
    sta score_processed         ; Reset flag for next game session
    lda #STATE_TITLE
    sta game_state
@ts_run_rts
    rts

; Render single row X (0..9) at screen row 3+X, col 12
render_top_score_row
    ; Calculate row VRAM address = STUB_VRAM + stub_row[3+X] + 12
    lda ts_render_idx
    clc
    adc #3
    tay                         ; Y = screen row (3..12)

    lda stub_row_lo,y
    clc
    adc #12                     ; Col 12
    sta PTR_DST
    lda stub_row_hi,y
    adc #0
    sta PTR_DST+1

    ; 1. Copy rank prefix (5 chars: " 1.  " .. "10.  ")
    lda ts_render_idx
    tay
    lda hs_name_offset,y        ; Offset = idx * 5
    tax
    ldy #0
@ts_copy_rank
    lda ts_rank_strings,x
    sta (PTR_DST),y
    inx
    iny
    cpy #5
    bcc @ts_copy_rank

    ; 2. Copy name (5 chars)
    lda ts_render_idx
    tay
    lda hs_name_offset,y        ; Offset = idx * 5
    tax
    ldy #5
@ts_copy_name
    lda hs_names,x
    sta (PTR_DST),y
    inx
    iny
    cpy #10
    bcc @ts_copy_name

    ; 3. Separator (2 spaces)
    lda #0                      ; Display code for space
    sta (PTR_DST),y
    iny
    sta (PTR_DST),y
    iny

    ; 4. Copy 4-digit score (each digit + $10 display code)
    lda ts_render_idx
    tay
    lda hs_score_offset,y       ; Offset = idx * 4
    tax
    ldy #12
@ts_copy_score
    lda hs_scores,x
    clc
    adc #$10                    ; Convert 0..9 to internal screen codes ($10..$19)
    sta (PTR_DST),y
    inx
    iny
    cpy #16
    bcc @ts_copy_score
    rts

; ==============================================================================
; ENTER NAME SCENE INITIALIZATION & EXECUTION
; ==============================================================================

enter_name_init
    ; Blank DMA during reconfiguration
    lda #0
    sta SDMCTL
    sta DMACTL

    ; Reset PMG
    jsr disable_pmg

    ; Use default text font
    lda #>FONT_ADDR
    sta CHBASE
    sta CHBAS

    ; Set DLIST pointer to stub text display list
    lda #<dlist_stub
    sta SDLSTL
    sta DLISTL
    lda #>dlist_stub
    sta SDLSTH
    sta DLISTH

    ; Set colors: Deep purple/crimson ($52), bright gold text ($2E), border ($50)
    lda #$52
    sta COLOR2
    sta COLPF2

    lda #$2E
    sta COLOR1
    sta COLPF1

    lda #$50
    sta COLOR4
    sta COLBK

    ; Clear text screen
    jsr clear_stub_vram

    ; Reset name entry variables
    lda #0
    sta cursor_pos
    sta name_input_timer
    lda #$0F
    sta name_prev_stick

    ; Default name: "AAAAA" (all indices = 0)
    lda #0
    sta name_indices
    sta name_indices+1
    sta name_indices+2
    sta name_indices+3
    sta name_indices+4

    ; Render header: "NEW HIGH SCORE!"
    lda #<en_txt_title
    sta PTR_SRC
    lda #>en_txt_title
    sta PTR_SRC+1
    ldx #3
    ldy #12
    jsr print_at

    ; Render "YOUR SCORE: XXXX"
    lda #<en_txt_score_lbl
    sta PTR_SRC
    lda #>en_txt_score_lbl
    sta PTR_SRC+1
    ldx #5
    ldy #12
    jsr print_at

    ; Print the 4 score digits after "YOUR SCORE: " (at col 24)
    lda stub_row_lo+5
    clc
    adc #24
    sta PTR_DST
    lda stub_row_hi+5
    adc #0
    sta PTR_DST+1

    ldy #0
@en_print_player_score
    lda SCORE,y
    clc
    adc #$10
    sta (PTR_DST),y
    iny
    cpy #4
    bcc @en_print_player_score

    ; Render "ENTER YOUR NAME:"
    lda #<en_txt_prompt_lbl
    sta PTR_SRC
    lda #>en_txt_prompt_lbl
    sta PTR_SRC+1
    ldx #8
    ldy #12
    jsr print_at

    ; Draw initial name field [ A A A A A ]
    jsr draw_name_field

    ; Render instructions
    lda #<en_txt_help1
    sta PTR_SRC
    lda #>en_txt_help1
    sta PTR_SRC+1
    ldx #15
    ldy #2
    jsr print_at

    lda #<en_txt_help2
    sta PTR_SRC
    lda #>en_txt_help2
    sta PTR_SRC+1
    ldx #18
    ldy #9
    jsr print_at

    ; Enable playfield DMA ($22)
    lda #$22
    sta SDMCTL
    sta DMACTL
    rts

enter_name_run
    ; 1. Check if FIRE button pressed -> Confirm name and insert score
    lda fire_pressed
    beq @en_check_joystick
    lda #0
    sta fire_pressed

    ; Insert score into table and transition to TOP SCORES
    jsr insert_high_score
    lda #STATE_TOP_SCORES
    sta game_state
    rts

@en_check_joystick
    ; Read STICK0 (shadow $0278), low nibble has direction bits
    lda STICK0
    and #$0F
    cmp #$0F
    bne @en_stick_active

    ; Joystick centered / released: clear repeat timer and previous stick state
    sta name_prev_stick
    lda #0
    sta name_input_timer
    rts

@en_stick_active
    ; Check if direction changed from previous frame
    cmp name_prev_stick
    beq @en_stick_held

    ; New direction: trigger immediately and set initial repeat delay
    sta name_prev_stick
    lda #NAME_REPEAT_INIT
    sta name_input_timer
    jmp @en_execute_direction

@en_stick_held
    ; Direction held: check repeat timer
    lda name_input_timer
    beq @en_repeat_trigger
    dec name_input_timer
    rts

@en_repeat_trigger
    lda #NAME_REPEAT_RATE
    sta name_input_timer

@en_execute_direction
    ; Bit 0 = 0: UP -> Next character (A -> B -> C ...)
    lda name_prev_stick
    and #$01
    bne @en_check_down

    ldx cursor_pos
    inc name_indices,x
    lda name_indices,x
    cmp #NAME_CHARSET_LEN
    bcc @en_up_ok
    lda #0
    sta name_indices,x
@en_up_ok
    jsr draw_name_field
    rts

@en_check_down
    ; Bit 1 = 0: DOWN -> Previous character (C -> B -> A ...)
    lda name_prev_stick
    and #$02
    bne @en_check_left

    ldx cursor_pos
    lda name_indices,x
    bne @en_down_dec
    lda #NAME_CHARSET_LEN
@en_down_dec
    sec
    sbc #1
    sta name_indices,x
    jsr draw_name_field
    rts

@en_check_left
    ; Bit 2 = 0: LEFT -> Move cursor left (min 0)
    lda name_prev_stick
    and #$04
    bne @en_check_right

    lda cursor_pos
    beq @en_left_rts
    dec cursor_pos
    jsr draw_name_field
@en_left_rts
    rts

@en_check_right
    ; Bit 3 = 0: RIGHT -> Move cursor right (max 4)
    lda name_prev_stick
    and #$08
    bne @en_dir_done

    lda cursor_pos
    cmp #4
    bcs @en_right_rts
    inc cursor_pos
    jsr draw_name_field
@en_right_rts
@en_dir_done
    rts

; Draw editable name box on Row 11: "[ A A A A A ]" with inverse cursor
draw_name_field
    lda stub_row_lo+11
    clc
    adc #13                     ; Col 13
    sta PTR_DST
    lda stub_row_hi+11
    adc #0
    sta PTR_DST+1

    ; Col 13: '['
    ldy #0
    lda #$3B                    ; Display code for '['
    sta (PTR_DST),y
    iny

    ; Col 14: space
    lda #0
    sta (PTR_DST),y

    ; Cols 15..23: 5 letters with spaces between
    ldx #0
@dn_char_loop
    ; Fetch character display code from charset
    ldy name_indices,x
    lda name_charset,y

    ; Check if this is the active cursor position
    cpx cursor_pos
    bne @dn_not_cursor
    ora #$80                    ; Invert video for active cursor!
@dn_not_cursor
    ; Output position in row: Y = 2 + X*2
    pha
    txa
    asl                         ; X * 2
    clc
    adc #2                      ; Offset = 2 + X*2
    tay
    pla
    sta (PTR_DST),y
    iny
    lda #0                      ; Space between letters
    sta (PTR_DST),y

    inx
    cpx #NAME_LEN
    bcc @dn_char_loop

    ; Closing bracket ']' at offset 12 (Col 25)
    ldy #12
    lda #$3D                    ; Display code for ']'
    sta (PTR_DST),y
    rts

; ==============================================================================
; HIGH SCORE TABLE RANKING & INSERTION LOGIC
; ==============================================================================

; Check if player's SCORE strictly qualifies for Top 10 (SCORE > 10th score)
; Returns Carry=1 if qualified, Carry=0 if not qualified
check_score_qualified
    ldx #9                      ; Entry 9 is the 10th (lowest) entry
    jsr compare_score_entry
    rts

; Compare SCORE (4 digits) with hs_scores entry X (X = 0..9)
; Preserves X register!
; Returns Carry=1 if SCORE > hs_scores[X]
;         Carry=0 if SCORE <= hs_scores[X]
compare_score_entry
    lda hs_score_offset,x
    tay                         ; Y = hs_scores byte offset
    lda SCORE
    cmp hs_scores,y
    bne @cmp_done
    lda SCORE+1
    cmp hs_scores+1,y
    bne @cmp_done
    lda SCORE+2
    cmp hs_scores+2,y
    bne @cmp_done
    lda SCORE+3
    cmp hs_scores+3,y
    bne @cmp_done
    ; All 4 digits identical -> SCORE == entry, return Carry=0 (strict >)
    clc
    rts
@cmp_done
    ; If SCORE > hs_scores: CMP sets Carry=1
    ; If SCORE < hs_scores: CMP clears Carry=0
    rts

; Insert SCORE and entered name into the Top 10 high-score table
insert_high_score
    ; 1. Find slot X (0..9) where SCORE > hs_scores[X]
    ldx #0
@ins_find_slot
    jsr compare_score_entry
    bcs @ins_slot_found
    inx
    cpx #TOP_SCORES_COUNT
    bcc @ins_find_slot
    ; Safety fallback: not greater than any entry
    rts

@ins_slot_found
    stx insert_idx

    ; 2. Shift entries down from 8 down to insert_idx (discarding 10th)
    cpx #9
    beq @ins_do_store           ; If inserting at position 9, no shift needed

    ldy #8                      ; Y = source entry (to shift to Y+1)
@ins_shift_down_loop
    cpy insert_idx
    bcc @ins_do_store

    ; Shift 4 score bytes: hs_scores[Y] -> hs_scores[Y+1]
    ldx hs_score_offset,y
    lda hs_scores,x
    sta hs_scores+4,x
    lda hs_scores+1,x
    sta hs_scores+5,x
    lda hs_scores+2,x
    sta hs_scores+6,x
    lda hs_scores+3,x
    sta hs_scores+7,x

    ; Shift 5 name bytes: hs_names[Y] -> hs_names[Y+1]
    ldx hs_name_offset,y
    lda hs_names,x
    sta hs_names+5,x
    lda hs_names+1,x
    sta hs_names+6,x
    lda hs_names+2,x
    sta hs_names+7,x
    lda hs_names+3,x
    sta hs_names+8,x
    lda hs_names+4,x
    sta hs_names+9,x

    dey
    bpl @ins_shift_down_loop

@ins_do_store
    ; 3. Store new score at insert_idx
    ldy insert_idx
    ldx hs_score_offset,y
    lda SCORE
    sta hs_scores,x
    lda SCORE+1
    sta hs_scores+1,x
    lda SCORE+2
    sta hs_scores+2,x
    lda SCORE+3
    sta hs_scores+3,x

    ; 4. Store new name at insert_idx (converted to display codes)
    ldx hs_name_offset,y
    ldy name_indices
    lda name_charset,y
    sta hs_names,x

    ldy name_indices+1
    lda name_charset,y
    sta hs_names+1,x

    ldy name_indices+2
    lda name_charset,y
    sta hs_names+2,x

    ldy name_indices+3
    lda name_charset,y
    sta hs_names+3,x

    ldy name_indices+4
    lda name_charset,y
    sta hs_names+4,x
    rts

; ==============================================================================
; DATA & LOOKUP TABLES
; ==============================================================================

; Multiples lookup tables for 10 entries
hs_score_offset
    dta 0, 4, 8, 12, 16, 20, 24, 28, 32, 36

hs_name_offset
    dta 0, 5, 10, 15, 20, 25, 30, 35, 40, 45

; State variables
score_processed     dta 0
cursor_pos          dta 0
name_input_timer    dta 0
name_prev_stick     dta $0F
ts_render_idx       dta 0
insert_idx          dta 0

; 5-character name indices (0..36)
name_indices        dta 0, 0, 0, 0, 0

; Character set lookup (A-Z, 0-9, space) in Atari internal display codes
name_charset
    dta d'A', d'B', d'C', d'D', d'E', d'F', d'G', d'H', d'I', d'J'
    dta d'K', d'L', d'M', d'N', d'O', d'P', d'Q', d'R', d'S', d'T'
    dta d'U', d'V', d'W', d'X', d'Y', d'Z'
    dta d'0', d'1', d'2', d'3', d'4', d'5', d'6', d'7', d'8', d'9'
    dta d' '

; Default Top 10 High Scores (10 entries x 4 decimal digits = 40 bytes)
hs_scores
    dta 0, 1, 5, 0              ; 1. 0150
    dta 0, 1, 3, 0              ; 2. 0130
    dta 0, 1, 1, 0              ; 3. 0110
    dta 0, 1, 0, 0              ; 4. 0100
    dta 0, 0, 8, 0              ; 5. 0080
    dta 0, 0, 6, 0              ; 6. 0060
    dta 0, 0, 5, 0              ; 7. 0050
    dta 0, 0, 3, 0              ; 8. 0030
    dta 0, 0, 2, 0              ; 9. 0020
    dta 0, 0, 1, 0              ; 10. 0010

; Default Top 10 Names (10 entries x 5 characters = 50 bytes)
hs_names
    dta d'DRACO'                ; 1
    dta d'WITCH'                ; 2
    dta d'VORPL'                ; 3
    dta d'JABBY'                ; 4
    dta d'BANDR'                ; 5
    dta d'JUBJB'                ; 6
    dta d'BOROG'                ; 7
    dta d'MOME '                ; 8
    dta d'SLITH'                ; 9
    dta d'TOVES'                ; 10

; Rank prefix strings (10 x 5 bytes)
ts_rank_strings
    dta d' 1.  '
    dta d' 2.  '
    dta d' 3.  '
    dta d' 4.  '
    dta d' 5.  '
    dta d' 6.  '
    dta d' 7.  '
    dta d' 8.  '
    dta d' 9.  '
    dta d'10.  '

; Text Strings
ts_txt_title
    dta 11, d'JABBERWOCKY'
ts_txt_subtitle
    dta 10, d'TOP SCORES'
ts_txt_col_headers
    dta 16, d'RANK  NAME   SCORE'
ts_txt_prompt
    dta 28, d'>> PRESS FIRE TO CONTINUE <<'*

en_txt_title
    dta 15, d'NEW HIGH SCORE!'
en_txt_score_lbl
    dta 12, d'YOUR SCORE: '
en_txt_prompt_lbl
    dta 16, d'ENTER YOUR NAME:'
en_txt_help1
    dta 36, d'JOYSTICK: UP/DOWN=CHAR LEFT/RIGHT=POS'
en_txt_help2
    dta 21, d'PRESS FIRE TO CONFIRM'*
