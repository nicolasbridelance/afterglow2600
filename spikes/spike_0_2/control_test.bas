 set kernel DPC+

 asm
; --- temoin : PAS d'appel ARM, juste 20 NOP (40 cycles attendus) ---
 lda #255
 sta TIM1T
 REPEAT 20
 nop
 REPEND
 lda INTIM
 sta temp1

FrameLoop
 lda #2
 sta VSYNC
 sta WSYNC
 sta WSYNC
 sta WSYNC
 lda #0
 sta VSYNC

 lda #43
 sta TIM64T
 lda #2
 sta VBLANK
WaitVblank
 lda INTIM
 bne WaitVblank
 sta WSYNC
 lda #0
 sta VBLANK

 lda #$1e
 sta COLUPF
 lda temp1
 ldx #80
DisplayLines
 sta WSYNC
 sta PF1
 dex
 bne DisplayLines
 lda #0
 sta PF1

 ldx #90
FillLines
 sta WSYNC
 dex
 bne FillLines

 lda #35
 sta TIM64T
WaitOverscan
 lda INTIM
 bne WaitOverscan
 sta WSYNC

 jmp FrameLoop
end
