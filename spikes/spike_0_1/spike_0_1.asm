; spike_0_1.asm — Spike 0.1 : bus stuffing + sprite natif mobile, même scanline.
; Code de mesure jetable, PAS un kernel livré (hors de la porte AGENTS.md sur /games/*/kernel_*.asm).
;
; Question posée : peut-on interrompre une séquence d'écritures bus-stuffées (A=$FF préchargé,
; STA <registre TIA zéro-page> = 3 cycles, l'ARM Harmony/Melody substituant l'octet réel sur le
; bus de données à chaque cycle d'écriture — technique confirmée par Big Mess o' Wires,
; "Atari 2600 Hardware Acceleration", 2023) pour repositionner/rafraîchir un sprite natif
; (HMOVE + GRP0), sans dépasser le budget de 76 cycles/ligne NTSC, et avec quelle marge ?
;
; Limite assumée : ceci prouve la structure et le budget de cycles, pas le comportement réel
; du firmware ARM (qui doit suivre la séquence d'écritures pour savoir quel octet stuffer) —
; ça reste à confirmer sur Stella cycle-exact ou hardware réel (voir backlog.md, Lane 1).

    processor 6502
    include "vcs.h"

    seg code
    org $F000

Reset:
    sei
    cld
    ldx #$FF
    txs
    lda #0
ClearMem:
    sta 0,x
    dex
    bne ClearMem

    lda #$10
    sta HMP0        ; motion fine du sprite natif, réglée AVANT le HMOVE de la ligne testée

FrameLoop:
    ; --- VSYNC : 3 lignes ---
    lda #2
    sta VSYNC
    sta WSYNC
    sta WSYNC
    sta WSYNC
    lda #0
    sta VSYNC

    ; --- VBLANK : ~37 lignes, minuteur RIOT (simplification pour ce spike) ---
    lda #43
    sta TIM64T
    lda #2
    sta VBLANK
WaitVblank:
    lda INTIM
    bne WaitVblank
    sta WSYNC
    lda #0
    sta VBLANK
    sta WSYNC       ; ligne de transition dédiée, pour que SpikeLine démarre à position 0 exacte

    ; --- Ligne instrumentée : contenu du Spike 0.1 ---
    lda #$FF                        ; 2 cycles, position 0, doit finir @0-2   (baseline bus-stuffing)
SpikeLine:
    sta HMOVE                       ; 3 cycles, position 2, doit finir @2-5   (motion sprite natif — doit être la 1re écriture après WSYNC)
    sta PF0                         ; 3 cycles, position 5, doit finir @5-8   (bus-stuffed : brique rangée octet 1)
    sta PF1                         ; 3 cycles, position 8, doit finir @8-11  (bus-stuffed : brique rangée octet 2)
    sta PF2                         ; 3 cycles, position 11, doit finir @11-14 (bus-stuffed : brique rangée octet 3)
    sta COLUP0                      ; 3 cycles, position 14, doit finir @14-17 (bus-stuffed : teinte ligne, hue-shift FRC)
    lda #$3C                        ; 2 cycles, position 17, doit finir @17-19 (rupture de séquence : vraie frame du sprite natif)
    sta GRP0                        ; 3 cycles, position 19, doit finir @19-22 (écriture NATIVE, pas bus-stuffée — point critique à valider ARM réel)
    lda #$FF                        ; 2 cycles, position 22, doit finir @22-24 (reprise du stuffing : recharge A=$FF)
    sta PF0                         ; 3 cycles, position 24, doit finir @24-27 (bus-stuffed : rangée suivante, octet 1)
    sta PF1                         ; 3 cycles, position 27, doit finir @27-30
    sta PF2                         ; 3 cycles, position 30, doit finir @30-33
    sta COLUP0                      ; 3 cycles, position 33, doit finir @33-36
    sta WSYNC                       ; 3 cycles, position 36, doit finir @36-39 (fin de ligne — marge restante volontaire)

    ; --- Reste de la zone visible : lignes de remplissage (hors mesure) ---
    ldx #190
FillLines:
    sta WSYNC
    dex
    bne FillLines

    ; --- OVERSCAN : ~30 lignes ---
    lda #35
    sta TIM64T
WaitOverscan:
    lda INTIM
    bne WaitOverscan
    sta WSYNC

    jmp FrameLoop

    org $FFFC
    .word Reset
    .word Reset
