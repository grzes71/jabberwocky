; ==============================================================================
; ENGINE/CHARSET_ANIM.ASM — Charset Animation Engine
; Target: Atari 800XL / 65XE
; Animates all characters defined in chars/rotated.json and chars/animated.json
; Target Font: GAME_FONT_ADDR ($7400)
; ==============================================================================

    icl 'gen/rotated_chars_global.asm'
    icl 'gen/rotated_chars_proc.asm'

; ==============================================================================
; init_charset_animation
; Resets rotation counters and animation frame state machine on game start/restart
; ==============================================================================
.proc init_charset_animation
    ; Initialize rotated character counters
    .if ANIM_CHAR_COUNT > 0
    ldx #ANIM_CHAR_COUNT-1
@rot_loop
    lda anim_char_speeds,x
    sta anim_char_counters,x
    dex
    bpl @rot_loop
    .endif

    ; Initialize animated character states
    .if NUM_ANIM_CHARS > 0
    ldx #NUM_ANIM_CHARS-1
@anim_loop
    lda #0
    sta animated_char_cur_segment,x
    lda animated_char_init_repeats,x
    sta animated_char_repeat_counter,x
    lda #255
    sta animated_char_cur_frame,x
    lda #1
    sta animated_char_timers,x
    dex
    bpl @anim_loop
    .endif
    rts
.endp

; ==============================================================================
; animate_charset
; Performs in-place 2-bit rotation (Mode 4/5 horizontal pixel shift) on characters
; ==============================================================================
.proc animate_charset
    .if ANIM_CHAR_COUNT > 0
    ; Preserve PTR_SRC on stack
    lda PTR_SRC
    pha
    lda PTR_SRC+1
    pha

    ldx #ANIM_CHAR_COUNT-1
@loop
    ; Decrement counter for character X
    dec anim_char_counters,x
    bne @next_char

    ; Reset counter to character rotation speed
    lda anim_char_speeds,x
    sta anim_char_counters,x

    ; Calculate character address: GAME_FONT_ADDR ($7400) + ID * 8
    lda #0
    sta PTR_SRC+1
    lda anim_char_ids,x
    asl
    rol PTR_SRC+1
    asl
    rol PTR_SRC+1
    asl
    rol PTR_SRC+1

    clc
    sta PTR_SRC
    lda PTR_SRC+1
    adc #>GAME_FONT_ADDR        ; $7400 -> >GAME_FONT_ADDR = $74
    sta PTR_SRC+1

    ; Rotate 8 bytes of character 2 bits left (horizontal shift in Mode 4/5)
    ldy #7
@roll_loop
    lda (PTR_SRC),y
    asl
    adc #0
    asl
    adc #0
    sta (PTR_SRC),y
    dey
    bpl @roll_loop

@next_char
    dex
    bpl @loop

    ; Restore PTR_SRC from stack
    pla
    sta PTR_SRC+1
    pla
    sta PTR_SRC
    .endif
    rts
.endp

; ==============================================================================
; update_animated_charset
; Multi-segment, frame-timed character animation state machine
; Copies 8-byte frame data into GAME_FONT_ADDR ($7400 + ID * 8)
; ==============================================================================
.proc update_animated_charset
    .if NUM_ANIM_CHARS > 0
    ; Preserve ZP pointers on stack
    lda PTR_SRC
    pha
    lda PTR_SRC+1
    pha
    lda PTR_DST
    pha
    lda PTR_DST+1
    pha

    ldx #NUM_ANIM_CHARS-1
@loop
    ; Decrement timer for character X
    dec animated_char_timers,x
    beq @timer_triggered
    jmp @next_char

@timer_triggered
    ; Advance frame index
    lda animated_char_cur_frame,x
    clc
    adc #1
    sta animated_char_cur_frame,x

    ; Set PTR_SRC to seg_num_frames table for character X
    lda animated_char_seg_num_frames_lo,x
    sta PTR_SRC
    lda animated_char_seg_num_frames_hi,x
    sta PTR_SRC+1

    ; Current segment index in Y
    ldy animated_char_cur_segment,x

    ; Number of frames in current segment
    lda (PTR_SRC),y

    ; Compare with current relative frame index
    cmp animated_char_cur_frame,x
    bne @store_frame_directly

    ; If relative_frame_idx == num_frames, segment is done.
    ; Check if repeating segment
    lda animated_char_repeat_counter,x
    beq @next_segment

    ; Repeat segment: decrement repeat counter and restart relative frame at 0
    dec animated_char_repeat_counter,x
    lda #0
    sta animated_char_cur_frame,x
    jmp @get_frame_data

@next_segment
    ; Move to next segment
    lda animated_char_cur_segment,x
    clc
    adc #1
    cmp animated_char_num_segments,x
    bcc @store_segment
    lda #0                      ; Wrap to first segment
@store_segment
    sta animated_char_cur_segment,x
    tay                         ; Y = new segment index

    ; Initialize repeat counter for new segment from char{X}_segment_repeats
    lda animated_char_seg_repeats_lo,x
    sta PTR_SRC
    lda animated_char_seg_repeats_hi,x
    sta PTR_SRC+1
    lda (PTR_SRC),y
    sta animated_char_repeat_counter,x

    ; Reset relative frame index to 0
    lda #0
    sta animated_char_cur_frame,x

@store_frame_directly
    ; relative_frame_idx is valid

@get_frame_data
    ; Y = current segment index
    ldy animated_char_cur_segment,x

    ; Flat frame index = segment_frame_starts[Y] + relative_frame_idx
    lda animated_char_seg_frame_starts_lo,x
    sta PTR_SRC
    lda animated_char_seg_frame_starts_hi,x
    sta PTR_SRC+1
    lda (PTR_SRC),y             ; A = segment_frame_starts[Y]
    clc
    adc animated_char_cur_frame,x
    tay                         ; Y = flat_frame_idx

    ; Set PTR_SRC to durations table for character X
    lda animated_char_durations_lo,x
    sta PTR_SRC
    lda animated_char_durations_hi,x
    sta PTR_SRC+1

    ; Read duration and store to timer
    lda (PTR_SRC),y
    sta animated_char_timers,x

    ; Calculate frame data address: BaseAddress + FlatFrameIndex * 8
    lda #0
    sta PTR_SRC+1
    tya                         ; A = flat_frame_idx
    asl
    rol PTR_SRC+1
    asl
    rol PTR_SRC+1
    asl
    rol PTR_SRC+1
    clc
    adc animated_char_data_lo,x
    sta PTR_SRC
    lda PTR_SRC+1
    adc animated_char_data_hi,x
    sta PTR_SRC+1

    ; Set PTR_DST to destination charset address ($7400 + ID * 8)
    lda animated_char_dest_lo,x
    sta PTR_DST
    lda animated_char_dest_hi,x
    sta PTR_DST+1

    ; Copy 8 bytes from PTR_SRC to PTR_DST
    ldy #7
@copy_loop
    lda (PTR_SRC),y
    sta (PTR_DST),y
    dey
    bpl @copy_loop

@next_char
    dex
    bmi @done_loop
    jmp @loop
@done_loop

    ; Restore ZP pointers from stack
    pla
    sta PTR_DST+1
    pla
    sta PTR_DST
    pla
    sta PTR_SRC+1
    pla
    sta PTR_SRC
    .endif
    rts
.endp

    icl 'gen/animated_chars.asm'
