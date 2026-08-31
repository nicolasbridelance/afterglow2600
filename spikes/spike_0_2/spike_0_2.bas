 set kernel DPC+

 asm
; --- trois mesures independantes dans le MEME binaire, meme banque ---
 lda #255
 sta TIM1T
 lda #$ff
 sta CALLFUNCTION
 lda INTIM
 sta temp1
 lda TIMINT
 and #$40
 sta temp4

 lda #255
 sta TIM64T
 lda #$ff
 sta CALLFUNCTION
 lda INTIM
 sta temp2
 lda TIMINT
 and #$40
 sta temp5

 lda #255
 sta T1024T
 lda #$ff
 sta CALLFUNCTION
 lda INTIM
 sta temp3
 lda TIMINT
 and #$40
 sta temp6

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
 ldx #40
Band1
 sta WSYNC
 sta PF1
 dex
 bne Band1
 lda #0
 sta PF1
 ldx #10
Gap1
 sta WSYNC
 dex
 bne Gap1

 lda temp2
 ldx #40
Band2
 sta WSYNC
 sta PF1
 dex
 bne Band2
 lda #0
 sta PF1
 ldx #10
Gap2
 sta WSYNC
 dex
 bne Gap2

 lda temp3
 ldx #40
Band3
 sta WSYNC
 sta PF1
 dex
 bne Band3
 lda #0
 sta PF1

 ldx #10
Gap3
 sta WSYNC
 dex
 bne Gap3

; --- bande 4 : drapeaux TIMINT overflow (bit0=TIM1T,bit1=TIM64T,bit2=T1024T), $E0 si aucun ---
 lda #0
 ldy temp4
 beq skip4
 ora #1
skip4
 ldy temp5
 beq skip5
 ora #2
skip5
 ldy temp6
 beq skip6
 ora #4
skip6
 ora #$E0
 ldx #40
Band4
 sta WSYNC
 sta PF1
 dex
 bne Band4
 lda #0
 sta PF1

 ldx #40
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
