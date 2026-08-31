> ⚠️ SUPERSEDED — voir [`PIVOT_INSTRUCTIONS.md`](../../PIVOT_INSTRUCTIONS.md). Le projet a abandonné l'architecture ARM/DPC+/CDFJ+ (2026-08-31). Conservé comme preuve de la décision de pivot, ne bloque plus rien.

# Spike 0.2b — désassemblage de `DPCplus.arm` pour chiffrer un coût ARM en cycles 6507

Investigation, pas un kernel livré. **Résultat partiel mais concret : la
boucle continue de fast-fetch/bus-stuffing a été localisée, désassemblée et
chiffrée manuellement — pas la boucle CALLFUNCTION explicitement visée par le
libellé backlog.md, qui reste à faire si utile.**

## Méthode

Binaire : `out/bin/compilers/bB/includes/DPCplus.arm` (extension
`chunkypixel.atari-dev-studio`, CC0, même fichier utilisé pour Spike 0.2),
3072 octets, sans en-tête ELF ni symboles. Désassemblage avec
`arm-none-eabi-objdump -D -b binary -marm` (mode ARM 32 bits — testé aussi en
mode Thumb forcé, résultat incohérent/beaucoup d'instructions invalides ;
le mode ARM 32 bits produit un désassemblage cohérent sur les ~700 instructions,
avec table de vecteurs d'exception classique en tête et adresses de
périphériques `0x40000xxx` plausibles pour une famille TI Stellaris/Tiva —
voir § Limite ci-dessous pour ce que ça implique).

## Ce qui a été trouvé : la boucle de dispatch fast-fetch/bus-stuffing

Boucle centrale à `0x24c` (voir dump complet, adresses relatives au fichier) :
lit un registre 16 bits à `[r5+22]` qui reflète (a priori) l'état courant du
bus 6507, décode quel "data fetcher" servir, écrit l'octet à fournir dans
`[r5+21]`, puis boucle en attente active (spin sur `[r5+22]`) jusqu'au cycle
6507 suivant. C'est la boucle qui alimente aussi bien le fast-fetch (DPC+/CDF)
que le bus-stuffing (BUS) — le firmware réel semble partager la même
infrastructure pour les deux, décodant **par adresse bus courante**, pas par
position dans une séquence attendue (`cmp`/jump-table sur `r2`, valeur relue à
chaque itération depuis `[r5+22]`, pas de compteur de séquence séparé trouvé).
C'est la pièce qui informe directement Spike 0.1b (voir son README) : rien
dans cette boucle ne dépend d'un ordre attendu d'écritures, donc une écriture
native intercalée sur une adresse non surveillée devrait être transparente.

## Comptage de cycles (chemin "lecture datastream", le cas de spike_0_1.asm)

Timings ARM7TDMI standard (data processing 1S, LDR mot/octet 1S+1N+1I, STR 2N,
branchement pris 2S+1N, branchement non pris 1S — hypothèse S=N=I=1 cycle,
flash/RAM 0 wait-state, cohérente avec un petit microcontrôleur ; pas vérifiée
contre une datasheet précise du chip réel).

| Étape | Instructions (`0x24c`→`0x288`) | Cycles |
|---|---|---|
| Décodage + dispatch + lecture + écriture de l'octet à stuffer | 16 instructions (`ldrh`, `tst`, `beq` non pris, `cmp`, `and`, `ldrcc` condition échouée, `sub`, `cmp`, `movcc`, `add`, `ldrb`, `strb`×2, `tst`, `cmpeq`, `beq` non pris) | **22** |
| Boucle d'attente active (`0x28c`-`0x298`), par itération non-sortante | `ldrh`(3) + `cmp`(1) + `beq` pris(3) | 7/itération |
| Sortie de boucle d'attente | `ldrh`(3) + `cmp`(1) + `beq` non pris(1) + `b` inconditionnel(3) | 8 |

Total par cycle 6507 servi ≈ `22 + 7×K + 8 = 30 + 7K`, où `K` = nombre
d'itérations d'attente active nécessaires.

Avec le ratio d'horloge déjà cité dans backlog.md (~70 MHz ARM / ~1,19 MHz
6507 ≈ **58,8×**) : `K = (58,8 − 30) / 7 ≈ 4,1` → `K = 4` cycles d'attente
entiers, donnant un total de **58 cycles ARM par octet servi** — à moins de
1,4 % du ratio théorique (58,8). Cette convergence n'est pas garantie a priori
(le calcul de `K` est indépendant du chiffre 58,8 avant d'être comparé à lui) —
elle sert de recoupement de cohérence, pas de preuve indépendante.

## Conclusion chiffrée

**≈58 cycles ARM ≈ 0,99 cycle 6507 par octet fast-fetché/bus-stuffé** — la
boucle est conçue pour consommer quasiment exactement un cycle 6507, ni plus
ni moins. Traduit en 6507 : **le mécanisme n'ajoute aucun cycle supplémentaire
au-delà du timing déjà prévu de l'instruction (`STA`/`STY` zéro-page = 3
cycles)**. C'est cohérent avec la réputation du bus-stuffing dans la
communauté homebrew ("coût zéro" comparé à une écriture normale), et confirme
structurellement (pas cycle-exact, voir limite ci-dessous) que Spike 0.1 n'a
pas à revoir son budget de 39/76 cycles pour cette raison.

## Ce qui n'a PAS été fait

Le libellé backlog.md visait spécifiquement la boucle **CALLFUNCTION** (l'appel
de fonction ARM ponctuel mesuré côté timing par Spike 0.2, pas la boucle
fast-fetch continue trouvée ici). Une zone candidate a été repérée
(`0x638`-`0x790`, un dispatcher avec `push`/`mov lr,pc`/`b` vers `0x764`,
lecture d'une table via `[r6+... ]`) mais **pas tracée en détail ni chiffrée**
— la boucle fast-fetch trouvée est plus directement utile à Spike 0.1b, donc
priorisée. À reprendre séparément si le coût CALLFUNCTION précis redevient
bloquant (il ne l'est pas pour la Porte 0 tant que l'hypothèse pessimiste de
Spike 0.2, section 6, reste respectée).

## Limite : ce désassemblage n'est probablement pas ce que Stella exécute

Point important trouvé en cours de route, pas anticipé au départ : le code
désassemblé ci-dessus est du **ARM 32 bits classique** (table de vecteurs
`MOV PC, #imm`, immédiats, adressage direct) — cohérent et sensé sur ~700
instructions, avec des adresses de périphériques (`0x40000xxx`) qui
correspondent à l'espace mémoire périphérique typique d'un microcontrôleur TI
Stellaris/Tiva. Mais **Thumbulator** (le cœur d'émulation ARM de Stella,
`src/emucore/Thumbulator.hxx/.cxx`) n'émule QUE le jeu d'instructions **Thumb**
(16 bits) — confirmé en lisant l'en-tête du fichier et en cherchant tout
support ARM 32 bits (aucun trouvé). Autrement dit : **ce firmware ARM 32 bits
réel n'est très probablement jamais exécuté par Stella** — Stella réimplémente
son comportement nativement en C++ (`readFromDatastream`, `busOverdrive`,
`myFastFetch`, déjà documentés dans Spike 0.1b) plutôt que de l'exécuter, sans
doute précisément parce que Thumbulator ne sait pas faire tourner du code ARM
32 bits. Ce que Stella exécute réellement en Thumbulator (les fonctions
CALLFUNCTION custom, comme `custom_main.c` de Spike 0.2, compilées
`-mthumb`) est une zone séparée du binaire, pas celle analysée ici.

**Conséquence** : le chiffrage de 58 cycles ci-dessus décrit le **firmware réel
tel qu'il tournerait sur un vrai Harmony/Melody** (lecture statique d'un
binaire de production, pas une simulation) — mais ce n'est ni ce que Stella
montre à l'écran, ni vérifiable dynamiquement dans ce sandbox (pas d'exécution
réelle, pas de trace, juste une lecture de désassemblage). Même limite de fond
que Spike 0.2 : la confirmation finale reste conditionnée au hardware réel
(Lane 1) ou, à défaut, à un vrai débogueur ARM capable d'exécuter ce binaire
(non tenté ici — hors scope d'un spike).

## Reproduire

```
arm-none-eabi-objdump -D -b binary -marm \
  out/bin/compilers/bB/includes/DPCplus.arm   # chemin extension chunkypixel.atari-dev-studio
```
Boucle de dispatch : chercher `ldrh` sur un registre à offset `+22` d'un
pointeur, suivi d'un test/dispatch puis d'un `strb` à offset `+21` du même
pointeur — motif répété à `0x24c` et dans chaque handler de la table.
