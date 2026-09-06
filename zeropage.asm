; ==============================================================================
; ZEROPAGE.ASM — Zero Page Equates ($80-$FF)
; User application area on Atari 8-bit XL/XE
; ==============================================================================

PTR_SRC     = $80       ; 16-bit pointer: source address (e.g. text)
PTR_DST     = $82       ; 16-bit pointer: destination address (e.g. VRAM)
ZP_TMP      = $84       ; 8-bit temporary scratchpad
