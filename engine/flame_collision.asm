; ==============================================================================
; ENGINE/FLAME_COLLISION.ASM — Dragon Fire Object Collision & Destruction
; Target: Atari 800XL / 65XE (MOS 6502, MADS syntax)
;
; Hierarchical Multi-Tier Collision Detection:
;   Tier 1: Hardware GTIA missile collision gatekeeper (flame_m_pf) & fire_state ($O(1)$, < 10 cycles)
;   Tier 2: Flame VRAM AABB bounding box calculation ($O(1)$, ~25 cycles)
;   Tier 3: Active screen resolution & row-pruned object checks (~10 cycles / obj)
;   Tier 4: VRAM erasure of destroyed object instances ($W \times H$ cells set to $00)
; ==============================================================================

FLAME_COL_MIN           = 10            ; Mode 5 char column at dragon_x (64) + 8 color clocks

; Maximum VRAM column reached by flame per fire animation frame (0..7)
flame_col_max_tbl
    dta 11, 12, 13, 15, 16, 17, 18, 18

; Screen destroyed bitmask byte offsets (8 screens * 5 bytes = 40 bytes)
screen_destroyed_offsets
    dta 0, 5, 10, 15, 20, 25, 30, 35

; Single-bit bitmask lookup table (0..7)
fc_bit_mask_tbl
    dta $01, $02, $04, $08, $10, $20, $40, $80

; VRAM Mode 5 row start address lookup table (11 rows of 48 bytes each)
vram_row_offsets_lo
    dta <(GAME_ACTION_VRAM + 0 * 48)
    dta <(GAME_ACTION_VRAM + 1 * 48)
    dta <(GAME_ACTION_VRAM + 2 * 48)
    dta <(GAME_ACTION_VRAM + 3 * 48)
    dta <(GAME_ACTION_VRAM + 4 * 48)
    dta <(GAME_ACTION_VRAM + 5 * 48)
    dta <(GAME_ACTION_VRAM + 6 * 48)
    dta <(GAME_ACTION_VRAM + 7 * 48)
    dta <(GAME_ACTION_VRAM + 8 * 48)
    dta <(GAME_ACTION_VRAM + 9 * 48)
    dta <(GAME_ACTION_VRAM + 10 * 48)

vram_row_offsets_hi
    dta >(GAME_ACTION_VRAM + 0 * 48)
    dta >(GAME_ACTION_VRAM + 1 * 48)
    dta >(GAME_ACTION_VRAM + 2 * 48)
    dta >(GAME_ACTION_VRAM + 3 * 48)
    dta >(GAME_ACTION_VRAM + 4 * 48)
    dta >(GAME_ACTION_VRAM + 5 * 48)
    dta >(GAME_ACTION_VRAM + 6 * 48)
    dta >(GAME_ACTION_VRAM + 7 * 48)
    dta >(GAME_ACTION_VRAM + 8 * 48)
    dta >(GAME_ACTION_VRAM + 9 * 48)
    dta >(GAME_ACTION_VRAM + 10 * 48)

; ==============================================================================
; DATA STORAGE (High RAM)
; ==============================================================================
flame_m_pf              dta 0           ; Latched M0PF..M3PF from DLI 3 (action area)
screen_obj_destroyed    :40 dta 0       ; 40 bytes: 8 screens * 5 bytes bitmask (up to 40 objs/screen)

; 22-byte spatial grid for dragon collision (dragon is fixed at cols 8..9 in VRAM)
blocking_col8           :11 dta 0       ; Mode 5 blocking flags for VRAM col 8 (11 rows)
blocking_col9           :11 dta 0       ; Mode 5 blocking flags for VRAM col 9 (11 rows)

dragon_stream_screen    dta 0           ; Screen index currently feeding dragon stream
dragon_stream_col       dta 0           ; Next column in screen to stream into blocking_col9
dragon_stream_ptr       dta a(0)        ; Pointer to blocking buffer of current screen

; Local calculation variables
fc_flame_row_min        dta 0
fc_flame_row_max        dta 0
fc_flame_row_max_p1     dta 0
fc_flame_col_max        dta 0
fc_flame_col_max_p1     dta 0

dc_dragon_row_min       dta 0
dc_dragon_row_max       dta 0
dc_dragon_row_max_p1    dta 0

fc_screen_id            dta 0
fc_vram_col0            dta 0
fc_obj_total            dta 0
fc_obj_idx              dta 0
fc_cur_packed_xy        dta 0
fc_cur_obj_x            dta 0
fc_cur_obj_y            dta 0
fc_cur_obj_w            dta 0
fc_cur_obj_h            dta 0
fc_cur_vram_x           dta 0

fc_erase_r              dta 0
fc_erase_c              dta 0

; ==============================================================================
; init_flame_collision
; Clears hardware latches and all destroyed object bitmasks
; ==============================================================================
.proc init_flame_collision
    lda #0
    sta flame_m_pf
    ldx #39
@clr_loop
    sta screen_obj_destroyed,x
    dex
    bpl @clr_loop
    rts
.endp

; ==============================================================================
; check_flame_object_collision
; Primary frame entry point. Called from vblank_game.
; ==============================================================================
.proc check_flame_object_collision
    ; --------------------------------------------------------------------------
    ; TIER 1: Hardware & State Gatekeeper ($O(1)$, ~10 cycles)
    ; --------------------------------------------------------------------------
    lda fire_state
    bne @fire_is_on
    lda #0
    sta flame_m_pf
    rts

@fire_is_on
    lda flame_m_pf
    bne @got_hardware_hit
    rts

@got_hardware_hit
    ; Reset latch now that we are processing it
    lda #0
    sta flame_m_pf

    ; Preserve ZP pointers on stack
    lda PTR_SRC
    pha
    lda PTR_SRC+1
    pha
    lda PTR_DST
    pha
    lda PTR_DST+1
    pha

    ; --------------------------------------------------------------------------
    ; TIER 2: Calculate Flame Bounding Box in VRAM Coordinates
    ; --------------------------------------------------------------------------
    ; Flame columns: min = 10, max = flame_col_max_tbl[fire_frame]
    ldx fire_frame
    cpx #8
    bcc @frame_ok
    ldx #7
@frame_ok
    lda flame_col_max_tbl,x
    sta fc_flame_col_max
    clc
    adc #1
    sta fc_flame_col_max_p1

    ; Flame rows:
    ; Action playfield starts at scanline 34.
    ; Flame covers scanlines dragon_y + 10 .. dragon_y + 16 (7 scanlines).
    ; rel_start = dragon_y + 10 - 34 = dragon_y - 24
    ; rel_end   = dragon_y + 16 - 34 = dragon_y - 18
    ; row = rel / 16 (4 right shifts)
    lda dragon_y
    sec
    sbc #24
    bcs @rel_start_pos
    lda #0
@rel_start_pos
    lsr
    lsr
    lsr
    lsr
    sta fc_flame_row_min

    lda dragon_y
    sec
    sbc #18
    bcs @rel_end_pos
    lda #0
@rel_end_pos
    lsr
    lsr
    lsr
    lsr
    cmp #11
    bcc @row_max_ok
    lda #10
@row_max_ok
    sta fc_flame_row_max
    clc
    adc #1
    sta fc_flame_row_max_p1

    ; --------------------------------------------------------------------------
    ; TIER 3: Check Active Screens
    ; --------------------------------------------------------------------------
    ; Fetch labyrinth screen list pointer for current_level_idx
    ldx current_level_idx
    lda labyrinths_screens_lo,x
    sta PTR_SRC
    lda labyrinths_screens_hi,x
    sta PTR_SRC+1

    ; 1. Left Screen: exists if level_screen_pos > 0
    lda level_screen_pos
    beq @skip_left_screen

    ; If incoming_col_idx >= 38, left screen has scrolled completely past flame (col 9 < 10)
    lda incoming_col_idx
    cmp #38
    bcs @skip_left_screen

    ; Left screen index = level_screen_pos - 1
    lda level_screen_pos
    sec
    sbc #1
    tay
    lda (PTR_SRC),y
    sta fc_screen_id

    ; Left screen col 0 in VRAM: 8 - incoming_col_idx
    lda #8
    sec
    sbc incoming_col_idx
    sta fc_vram_col0

    jsr check_single_screen_flame

@skip_left_screen
    ; 2. Incoming Screen: exists if level_tail_cols == 0 and level_screen_pos < lab_total_screens
    lda level_tail_cols
    bne @done_collision

    lda level_screen_pos
    cmp lab_total_screens
    bcs @done_collision

    ; Incoming screen can only reach col 18 if incoming_col_idx >= 30 (48 - 30 = 18)
    lda incoming_col_idx
    cmp #30
    bcc @done_collision

    ; Re-fetch pointer in case PTR_SRC was clobbered
    ldx current_level_idx
    lda labyrinths_screens_lo,x
    sta PTR_SRC
    lda labyrinths_screens_hi,x
    sta PTR_SRC+1

    ldy level_screen_pos
    lda (PTR_SRC),y
    sta fc_screen_id

    ; Incoming screen col 0 in VRAM: 48 - incoming_col_idx
    lda #48
    sec
    sbc incoming_col_idx
    sta fc_vram_col0

    jsr check_single_screen_flame

@done_collision
    ; Restore ZP pointers
    pla
    sta PTR_DST+1
    pla
    sta PTR_DST
    pla
    sta PTR_SRC+1
    pla
    sta PTR_SRC
    rts
.endp

; ==============================================================================
; check_single_screen_flame
; Checks all objects on fc_screen_id with VRAM offset fc_vram_col0
; ==============================================================================
.proc check_single_screen_flame
    ldx fc_screen_id
    cpx #WORLD_SCREENS_COUNT
    bcc @valid_screen
    rts

@valid_screen
    lda screens_obj_count,x
    sta fc_obj_total
    bne @has_objs
    rts

@has_objs
    ; Self-modifying operand setup: set absolute base addresses for LDA abs,Y
    lda screens_codes_lo,x
    sta @fetch_code + 1
    lda screens_codes_hi,x
    sta @fetch_code + 2

    lda screens_coords_lo,x
    sta @fetch_coords + 1
    lda screens_coords_hi,x
    sta @fetch_coords + 2

    lda #0
    sta fc_obj_idx

@obj_loop
    ; --- Check if already destroyed ---
    ldx fc_screen_id
    lda screen_destroyed_offsets,x
    sta ZP_TMP

    lda fc_obj_idx
    lsr
    lsr
    lsr
    clc
    adc ZP_TMP
    tax                         ; X = byte offset in screen_obj_destroyed

    lda fc_obj_idx
    and #$07
    tay                         ; Y = bit index (0..7)

    lda screen_obj_destroyed,x
    and fc_bit_mask_tbl,y
    beq @not_destroyed
    jmp @next_obj               ; Already destroyed -> skip!

@not_destroyed
    ; --- Fetch packed coordinates and object code (4 cycles each!) ---
    ldy fc_obj_idx
@fetch_coords
    lda $FFFF,y                 ; Target address modified above
    sta fc_cur_packed_xy

    ; Unpack Y: ((packed_xy >> 5) & 7) * 2 = (packed_xy >> 4) & $0E
    lsr
    lsr
    lsr
    lsr
    and #$0E
    sta fc_cur_obj_y

    ; Fetch code & size
@fetch_code
    lda $FFFF,y                 ; Target address modified above
    tax

    ; Only objects with blocking=true (bit 0) can be destroyed by fire
    lda obj_type_flags,x
    and #$01
    beq @skip_to_next

    lda obj_type_width,x
    sta fc_cur_obj_w
    lda obj_type_height,x
    sta fc_cur_obj_h

    ; If width or height is 0, skip
    lda fc_cur_obj_w
    beq @skip_to_next
    lda fc_cur_obj_h
    bne @check_vert

@skip_to_next
    jmp @next_obj

@check_vert
    ; --- Fast Vertical Overlap Test ---
    ; Condition: fc_cur_obj_y <= fc_flame_row_max AND fc_cur_obj_y + fc_cur_obj_h > fc_flame_row_min
    lda fc_cur_obj_y
    cmp fc_flame_row_max_p1
    bcs @skip_to_next           ; Top edge below flame bottom -> no overlap

    clc
    adc fc_cur_obj_h
    cmp fc_flame_row_min
    bcc @skip_to_next           ; Bottom edge above flame top -> no overlap
    beq @skip_to_next

    ; --- Horizontal Overlap Test ---
    ; Unpack X: (packed_xy & $1F) * 2
    lda fc_cur_packed_xy
    and #$1F
    asl
    sta fc_cur_obj_x

    ; Signed addition: cur_vram_x = cur_vram_col0 + cur_obj_x
    clc
    adc fc_vram_col0
    sta fc_cur_vram_x

    ; Check if cur_vram_x is positive or negative
    bpl @x_positive

    ; cur_vram_x is negative (-31..-1)
    ; Since cur_vram_x < 0 <= flame_col_max, it passes left bound test automatically.
    ; Test right edge: cur_vram_x + cur_obj_w > FLAME_COL_MIN (10)
    clc
    adc fc_cur_obj_w
    bmi @skip_to_next           ; Right edge still off-screen to left -> no overlap
    cmp #FLAME_COL_MIN
    bcc @skip_to_next
    beq @skip_to_next
    jmp @object_hit

@x_positive
    ; cur_vram_x is positive (0..47)
    ; Test left bound: cur_vram_x <= fc_flame_col_max
    cmp fc_flame_col_max_p1
    bcs @skip_to_next           ; Object too far to the right -> no overlap

    ; Test right edge: cur_vram_x + cur_obj_w > FLAME_COL_MIN (10)
    clc
    adc fc_cur_obj_w
    cmp #FLAME_COL_MIN
    bcc @skip_to_next
    beq @skip_to_next

@object_hit
    ; --------------------------------------------------------------------------
    ; TIER 4: Destroy Object Instance
    ; --------------------------------------------------------------------------
    ; 1. Mark as destroyed in bitmask
    ldx fc_screen_id
    lda screen_destroyed_offsets,x
    sta ZP_TMP
    lda fc_obj_idx
    lsr
    lsr
    lsr
    clc
    adc ZP_TMP
    tax
    lda fc_obj_idx
    and #$07
    tay
    lda screen_obj_destroyed,x
    ora fc_bit_mask_tbl,y
    sta screen_obj_destroyed,x

    ; 2. Erase from GAME_ACTION_VRAM
    jsr erase_cur_object

@next_obj
    inc fc_obj_idx
    lda fc_obj_idx
    cmp fc_obj_total
    bcc @obj_loop_jmp

    rts

@obj_loop_jmp
    jmp @obj_loop
.endp

; ==============================================================================
; erase_cur_object
; Clears fc_cur_obj_w * fc_cur_obj_h cells in GAME_ACTION_VRAM to $00
; ==============================================================================
.proc erase_cur_object
    lda #0
    sta fc_erase_r

@row_loop
    lda fc_cur_obj_y
    clc
    adc fc_erase_r
    cmp #11
    bcs @erase_done             ; Beyond row 10
    tax                         ; X = row (0..10)

    lda vram_row_offsets_lo,x
    sta PTR_DST
    lda vram_row_offsets_hi,x
    sta PTR_DST+1

    lda #0
    sta fc_erase_c

@col_loop
    lda fc_cur_vram_x
    clc
    adc fc_erase_c
    bmi @skip_cell              ; < 0
    cmp #48
    bcs @skip_cell              ; >= 48
    tay
    lda #0
    sta (PTR_DST),y             ; Clear cell in GAME_ACTION_VRAM to background $00

    cpy #8
    bne @chk_col9
    sta blocking_col8,x
    jmp @skip_cell
@chk_col9
    cpy #9
    bne @skip_cell
    sta blocking_col9,x

@skip_cell
    inc fc_erase_c
    lda fc_erase_c
    cmp fc_cur_obj_w
    bcc @col_loop

    inc fc_erase_r
    lda fc_erase_r
    cmp fc_cur_obj_h
    bcc @row_loop

@erase_done
    rts
.endp

; ==============================================================================
; BLOCKING COLUMN MANAGEMENT & STREAMING (High RAM)
; Dragon is horizontally locked at dragon_x = 64 (VRAM columns 8 and 9).
; Instead of shifting a 528-byte buffer (which took >5,000 cycles and caused stutter),
; we only maintain the 2 active columns (22 bytes total: blocking_col8 & col9).
; Coarse scroll step updates these columns in ~200 cycles (96% faster!).
; ==============================================================================

; init_blocking_cols
; Initializes blocking_col8 (from Screen 0, col 4) and blocking_col9 (from Screen 0, col 5).
; Primes dragon_stream_col = 6, dragon_stream_screen = 0.
.proc init_blocking_cols
    ; Screen 0 of current level labyrinth
    ldx current_level_idx
    lda labyrinths_screens_lo,x
    sta PTR_SRC
    lda labyrinths_screens_hi,x
    sta PTR_SRC+1
    ldy #0
    lda (PTR_SRC),y
    tax                         ; X = screen index (0..WORLD_SCREENS_COUNT-1)

    lda screens_blocking_lo,x
    sta dragon_stream_ptr
    sta PTR_SRC
    lda screens_blocking_hi,x
    sta dragon_stream_ptr+1
    sta PTR_SRC+1

    ; Dragon at start is over col 4 (col 8 in VRAM) and col 5 (col 9 in VRAM)
    ; Next column to stream into col 9 is col 6!
    lda #0
    sta dragon_stream_screen
    lda #6
    sta dragon_stream_col

    ; Copy column 4 into blocking_col8 and column 5 into blocking_col9 for all 11 rows
    ldx #0
@row_loop
    ldy #4
    lda (PTR_SRC),y
    sta blocking_col8,x
    ldy #5
    lda (PTR_SRC),y
    sta blocking_col9,x

    lda PTR_SRC
    clc
    adc #40
    sta PTR_SRC
    bcc @no_c
    inc PTR_SRC+1
@no_c
    inx
    cpx #11
    bcc @row_loop
    rts
.endp

; shift_blocking_cols
; Shifts col 9 into col 8, and streams 11 rows of column dragon_stream_col into col 9.
; Total execution time: ~200 cycles (< 2 scanlines!).
.proc shift_blocking_cols
    ; 1. Shift col 9 into col 8 (11 rows)
    ldx #10
@shift_loop
    lda blocking_col9,x
    sta blocking_col8,x
    dex
    bpl @shift_loop

    ; 2. Check if end of labyrinth reached
    lda dragon_stream_screen
    cmp lab_total_screens
    bcc @do_stream
    jmp @stream_blank

@do_stream

    ; 3. Stream 11 rows of column dragon_stream_col into blocking_col9
    lda dragon_stream_ptr
    sta PTR_SRC
    lda dragon_stream_ptr+1
    sta PTR_SRC+1

    ldy dragon_stream_col
    lda (PTR_SRC),y
    sta blocking_col9 + 0
    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta blocking_col9 + 1
    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta blocking_col9 + 2
    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta blocking_col9 + 3
    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta blocking_col9 + 4
    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta blocking_col9 + 5

    ; Advance PTR_SRC by 240 (6 * 40)
    lda PTR_SRC
    clc
    adc #240
    sta PTR_SRC
    bcc @ptr_no_c
    inc PTR_SRC+1
@ptr_no_c
    ldy dragon_stream_col
    lda (PTR_SRC),y
    sta blocking_col9 + 6
    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta blocking_col9 + 7
    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta blocking_col9 + 8
    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta blocking_col9 + 9
    tya
    clc
    adc #40
    tay
    lda (PTR_SRC),y
    sta blocking_col9 + 10

    ; 4. Advance column index
    inc dragon_stream_col
    lda dragon_stream_col
    cmp #40
    bcc @done

    ; Reached 40 -> advance to next screen
    lda #0
    sta dragon_stream_col
    inc dragon_stream_screen
    lda dragon_stream_screen
    cmp lab_total_screens
    bcs @done

    ; Update dragon_stream_ptr to next screen
    ldx current_level_idx
    lda labyrinths_screens_lo,x
    sta PTR_SRC
    lda labyrinths_screens_hi,x
    sta PTR_SRC+1
    ldy dragon_stream_screen
    lda (PTR_SRC),y
    tax
    lda screens_blocking_lo,x
    sta dragon_stream_ptr
    lda screens_blocking_hi,x
    sta dragon_stream_ptr+1
    rts

@stream_blank
    lda #0
    ldx #10
@blank_loop
    sta blocking_col9,x
    dex
    bpl @blank_loop

@done
    rts
.endp

; Compatibility equates
init_blocking_vram          = init_blocking_cols
shift_blocking_vram_left    = shift_blocking_cols

; ==============================================================================
; check_dragon_blocking_collision
; Ultra-fast O(1) direct check of blocking_col8 and blocking_col9 (~35 cycles).
; Dragon spans scanlines dragon_y .. dragon_y + 25 at VRAM columns 8..9.
; Returns:
;   Carry SET (SEC) = Collision with blocking tile detected -> CRASH!
;   Carry CLEAR (CLC) = No blocking collision (decor or clear air) -> PASS!
; Clobbers: A, X
; ==============================================================================
.proc check_dragon_blocking_collision
    ; Dragon spans scanlines dragon_y .. dragon_y + 25
    ; Action playfield starts at scanline 34
    ; rel_start = dragon_y - 34
    ; rel_end   = dragon_y + 25 - 34 = dragon_y - 9
    ; row = rel / 16 (4 right shifts)
    lda dragon_y
    sec
    sbc #34
    bcs @rel_start_pos
    lda #0
@rel_start_pos
    lsr
    lsr
    lsr
    lsr
    sta dc_dragon_row_min

    lda dragon_y
    sec
    sbc #9
    bcs @rel_end_pos
    lda #0
@rel_end_pos
    lsr
    lsr
    lsr
    lsr
    cmp #11
    bcc @row_max_ok
    lda #10
@row_max_ok
    clc
    adc #1
    sta dc_dragon_row_max_p1

    ldx dc_dragon_row_min
@chk_row
    lda blocking_col8,x
    ora blocking_col9,x
    bne @collision_hit
    inx
    cpx dc_dragon_row_max_p1
    bcc @chk_row

    clc
    rts

@collision_hit
    sec
    rts
.endp


