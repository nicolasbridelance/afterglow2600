; spike_frc.asm — Spike FRC (cahier_des_charges.md §5.3, §9.2.2 pt.4) : bascule de table de
; teintes en vblank, par code auto-modifiant, sans coût supplémentaire dans la boucle scanline.
; Code de mesure jetable, PAS un kernel livré (hors de la porte AGENTS.md sur /games/*/kernel_*.asm).
;
; Question posée : la piste privilégiée par §5.3 ("un simple changement de pointeur de table
; en vblank, le kernel scanline lit toujours 'la table active' sans savoir laquelle c'est")
; tient-elle cycle par cycle ? Deux affirmations à vérifier séparément :
;   1. Le coût de la bascule elle-même (vblank) est négligeable face au budget disponible
;      (~2000-2700 cycles/frame, §6) — trivial à montrer, mais à chiffrer précisément.
;   2. La lecture dans la boucle scanline ne coûte RIEN de plus selon la table active — pas
;      seulement "à peu près pareil", un coût strictement identique quel que soit l'octet
;      patché à l'exécution.
;
; Mécanisme retenu : code auto-modifiant. `ReadColor` est un `LDA <table>,Y` fixe ; seul son
; octet de poids fort (adresse ReadColor+2) est réécrit en vblank pour pointer vers Table0 ou
; Table1. Le corps de la boucle scanline (opcode $B9, mode d'adressage absolu,Y) est identique
; à l'exécution, qu'importe quelle table est active — c'est le point que ce spike vérifie
; mécaniquement, pas juste "à l'oeil".
;
; Contrainte de conception à documenter, pas seulement à respecter ici : Table0 et Table1
; doivent chacune tenir dans une seule page mémoire pour l'offset Y utilisé (poids faible de
; l'adresse de base + Y max < $100), sous peine d'un cycle de pénalité de franchissement de
; page sur `LDA abs,Y` (5 cycles au lieu de 4) — indépendant de la table active, donc ça ne
; casserait pas l'égalité de coût entre tables, mais casserait le budget scanline si négligé.
; Ce spike utilise des tables volontairement petites (8 entrées, une par rangée de briques,
; §12.1) pour illustrer le cas réel sans avoir à forcer un alignement de page explicite.
;
; Limite assumée : ceci prouve le mécanisme et le budget de cycles pour UNE frame simulée
; (bascule appelée une fois, lue une fois) — pas l'alternance réelle sur 60 Hz continu ni le
; jugement perceptif du scintillement obtenu (hors de portée d'un spike de cycles, voir
; backlog.md § Protocole IA — jugement humain / Lane 1 / CRT réel).

    processor 6502
    include "vcs.h"

    seg.u Variables
    org $80
FRCToggle   ds 1            ; 0 ou 1 — index de la table active

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

FrameLoop:
    ; --- VSYNC : 3 lignes ---
    lda #2
    sta VSYNC
    sta WSYNC
    sta WSYNC
    sta WSYNC
    lda #0
    sta VSYNC

    ; --- VBLANK : ~37 lignes, minuteur RIOT (simplification, comme spike_0_1) ---
    lda #43
    sta TIM64T
    lda #2
    sta VBLANK
WaitVblank:
    lda INTIM
    bne WaitVblank
    sta WSYNC                       ; frontière de segment : fin de l'attente RIOT brute

    ; --- Segment instrumenté 1 : bascule FRC + patch du kernel (contenu du Spike FRC) ---
    lda FRCToggle                   ; 3 cycles, position 0, doit finir @0-3
    eor #1                          ; 2 cycles, position 3, doit finir @3-5
    sta FRCToggle                   ; 3 cycles, position 5, doit finir @5-8
    tax                             ; 2 cycles, position 8, doit finir @8-10
    lda TableHiByToggle,X           ; 4 cycles, position 10, doit finir @10-14 (table 2 entrées, pas de branchement)
    sta ReadColor+2                 ; 4 cycles, position 14, doit finir @14-18 (patch : octet fort de l'opérande LDA abs,Y)
    lda #0                          ; 2 cycles, position 18, doit finir @18-20
    sta VBLANK                      ; 3 cycles, position 20, doit finir @20-23
    sta WSYNC                       ; 3 cycles, position 23, doit finir @23-26 (fin de segment — budget vblank total ~2000-2700c, voir §6)

    ; --- Segment instrumenté 2 : lecture dans la boucle scanline (contenu du Spike FRC) ---
    ldy #0                           ; 2 cycles, position 0, doit finir @0-2
ReadColor:
    lda Table0,Y                     ; 4 cycles, position 2, doit finir @2-6 (opérande haut patché en vblank ci-dessus — coût $B9 abs,Y fixe, indépendant de la valeur patchée)
    sta COLUPF                       ; 3 cycles, position 6, doit finir @6-9
    sta WSYNC                        ; 3 cycles, position 9, doit finir @9-12 (fin de ligne — marge restante volontaire)

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

    ; --- Tables de teintes, une entrée par rangée de briques (§12.1 : dégradé par rangée) ---
    ; Petites et non alignées sur page volontairement (voir note de conception en tête de
    ; fichier) : $08 + 7 < $100 pour les deux tables, aucun franchissement de page possible.
Table0:
    .byte $02, $04, $06, $08, $0A, $0C, $0E, $10   ; teinte "paire" par rangée, illustrative
Table1:
    .byte $03, $05, $07, $09, $0B, $0D, $0F, $11   ; teinte "impaire" par rangée, illustrative

TableHiByToggle:
    .byte >Table0, >Table1

    org $FFFC
    .word Reset
    .word Reset
