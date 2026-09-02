# Spike FRC — bascule de table de teintes en vblank

Seul spike réellement ouvert après le pivot du 2026-08-31 (`PIVOT_INSTRUCTIONS.md`,
`cahier_des_charges.md` §5.3/§9.2.2). Investigation, pas un kernel livré. Détail dans
`backlog.md` (Lane 2, sous-item Spike FRC).

## Question posée

§5.3 propose une piste : basculer une fois par frame, en vblank, entre deux tables de
teintes via un simple changement de pointeur — le kernel scanline "lit toujours la table
active sans savoir laquelle c'est", donc la boucle scanline elle-même ne coûterait rien de
plus. Cette piste n'avait jamais été vérifiée cycle par cycle.

## Mécanisme testé

Code auto-modifiant plutôt qu'indirection via pointeur zéro page (une indirection
`LDA (ptr),Y` coûterait 5 cycles au lieu de 4 pour `LDA abs,Y`, ce qui aurait ajouté un
coût constant à *chaque* lecture — pas ce que §5.3 promettait). À la place :
`ReadColor: LDA Table0,Y` est une instruction fixe ; seul son octet de poids fort
(`ReadColor+2`) est réécrit en vblank pour pointer vers `Table0` ou `Table1`. L'opcode
exécuté dans la boucle scanline ($B9, `LDA abs,Y`) est structurellement identique quelle
que soit la table active.

## Résultat (mesuré par `tools/cycle_linter.py` sur `spike_frc.lst`)

| Segment | Contenu | Cycles | Budget | Marge |
|---|---|---|---|---|
| Bascule + patch (vblank) | `EOR`/table 2 entrées/patch `ReadColor+2` | 26 | ~2000-2700/frame (§6) | confortable |
| Lecture scanline (patchée) | `LDA Table0,Y` / `STA COLUPF` / `WSYNC` | 12 | 76/ligne (NTSC) | 64 |

Les deux affirmations de §5.3 sont confirmées mécaniquement :
1. Le coût de la bascule (26 cycles) est négligeable face au budget vblank.
2. Le coût de la lecture scanline (12 cycles, dont 4 pour l'accès à la table) est fixe —
   l'opcode `LDA abs,Y` ne dépend pas de la valeur patchée dans son opérande, seulement de
   son mode d'adressage. Rien à payer de plus selon la table active.

**Contrainte de conception à ne pas perdre en implémentation réelle** : `Table0` et
`Table1` doivent chacune tenir dans une seule page mémoire pour la plage d'offsets `Y`
utilisée (poids faible de l'adresse de base + `Y` max < `$100`), sous peine d'un cycle de
pénalité de franchissement de page sur `LDA abs,Y` (5 au lieu de 4) — indépendant de la
table active donc ça ne romprait pas l'égalité de coût entre tables, mais romprait le
budget scanline si la table grossit sans y penser. Ce spike utilise des tables volontairement
petites (8 entrées, une par rangée de briques, §12.1) pour ne pas avoir à le vérifier
explicitement ; à re-mesurer si le nombre de rangées augmente.

Assemblage propre (`dasm spike_frc.asm -f3`) et boot Stella headless confirmé sans crash,
type de bankswitch "4K" correctement détecté (`xvfb-run -a stella -video software
-audio.enabled 0 -logtoconsole 1 -holdreset spike_frc.bin`) — vérification structurelle
uniquement, ce spike ne prétend pas juger le scintillement réel (jugement humain / CRT
réel, hors de portée, voir `backlog.md` § Protocole IA).

## Effet de bord : bug trouvé et corrigé dans `tools/cycle_linter.py`

En annotant ce spike, `cycle_linter.py` a d'abord rapporté des `MISMATCH` sur des positions
qui semblaient pourtant correctes à la main. Cause : sa regex de parsing du listing DASM
exigeait une tabulation immédiatement après le dernier octet listé, mais DASM insère un
espace supplémentaire sur les lignes à 3 octets (adressage absolu, ex. `LDA table,X`,
`STA addr`) avant cette tabulation — absent sur les lignes à 2 octets (zero-page, immédiat).
Résultat : toute instruction en adressage absolu était **silencieusement ignorée** du
comptage, sans avertissement, ce qui aurait pu masquer un dépassement de budget sur un vrai
kernel qui en contient. Corrigé (regex + test de régression `test_parse_lst_reads_absolute_addressing_line`
dans `tests/test_cycle_linter.py`) ; le résultat déjà publié de Spike 0.1 (39/76 cycles)
n'était pas affecté — son segment mesuré n'utilisait que des instructions zero-page.

## Fichiers

- `spike_frc.asm` — source DASM (`-f3`)
- `spike_frc.lst` — listing assemblé, vérifié par `tools/cycle_linter.py`
- `spike_frc.bin` — ROM 4K assemblée, boot Stella headless confirmé
