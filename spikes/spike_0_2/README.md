> ⚠️ SUPERSEDED — voir [`PIVOT_INSTRUCTIONS.md`](../../PIVOT_INSTRUCTIONS.md). Le projet a abandonné l'architecture ARM/DPC+/CDFJ+ (2026-08-31). Conservé comme preuve de la décision de pivot, ne bloque plus rien.

# Spike 0.2 — Coût réel d'un aller-retour ACE (6507 → ARM → 6507)

Code de mesure jetable, comme Spike 0.1 — pas un kernel livré.

## Ce qui a été construit

Un vrai ROM DPC+ (32K, driver ARM réel `DPCplus.arm` — précompilé, licence CC0,
fourni avec l'extension VS Code `chunkypixel.atari-dev-studio` déjà recommandée
pour ce projet, `out/bin/compilers/bB/includes/DPCplus.arm`), pas une simulation :

1. `custom_main.c` : fonction ARM minimale (`int main(void) { return 0; }`),
   compilée avec `arm-none-eabi-gcc` (cible `arm7tdmi`, thumb) via le boot/linker
   glue fourni par la même extension (`includes/custom/src/custom.S` +
   `custom.boot.lds`) — remplace l'exemple "multisprite" fourni par défaut.
2. `spike_0_2.bas` : programme batari Basic (`set kernel DPC+`) qui déclenche
   3 fois `STA CALLFUNCTION` (valeur `$FF`), chacune encadrée par un chronométrage
   RIOT différent (`TIM1T`, `TIM64T`, `T1024T`) pour mesurer le nombre de cycles
   6507 écoulés pendant l'aller-retour. Résultat affiché comme un motif binaire
   sur `PF1` (barres claires/sombres), lu depuis une capture d'écran Stella
   headless (`xvfb-run` + `xdotool key F12`).
3. `control_test.bas` : témoin de validation de la méthode (20 NOP = 40 cycles
   attendus) — a mesuré 44, écart cohérent avec la latence de synchronisation
   RIOT documentée. La méthode elle-même est donc fiable.

Toolchain complète utilisée (pas encore dans `.devcontainer` — voir note plus bas) :
`wasmtime` (exécute le compilateur bB, distribué en WebAssembly) + `arm-none-eabi-gcc`
+ les binaires bB/DASM bundlés dans l'extension VS Code + Stella headless (déjà
disponible, voir backlog.md § Protocole IA / Émulation) + `xdotool` (capture
d'écran pilotée, le mode "continuous snapshot" de Stella n'étant pas exposé en CLI).

## Résultat : Stella ne peut PAS répondre à cette question

Les trois mesures (`TIM1T`, `TIM64T`, `T1024T`) donnent des résultats mutuellement
incohérents (~10 cycles, ~64+ cycles, ~1024+ cycles) — pas du bruit de mesure,
mais la conséquence directe d'un choix de modélisation de Stella, confirmé en
lisant son propre code source (cloné depuis
[stella-emu/stella](https://github.com/stella-emu/stella), commit
`0969155380391f874bd960c944a52bc3d4ec71e7`) :

```cpp
// src/emucore/CartDPCPlus.cxx, case 254/255 de callFunction() :
// call with IRQ driven audio, no special handling needed at this
// time for Stella as ARM code "runs in zero 6507 cycles".
```

Stella exécute le code ARM custom **sans lui faire coûter le moindre cycle 6507**
— `STA CALLFUNCTION` a le coût fixe d'un store absolu (4 cycles) et rien de plus,
quelle que soit la complexité de la fonction ARM appelée. Les "mesures" obtenues
ne reflètent donc que la latence de synchronisation du timer RIOT utilisé pour
sonder, pas un vrai coût d'aller-retour — c'est un artefact de mesure, pas un
signal.

Sur le hardware réel (Harmony/Melody), ce coût est non nul : le driver ARM bourre
le bus de données avec des NOP pendant qu'il exécute (SpiceWare, *DPC+ARM - Part 7*),
donc le 6507 est bien mis en attente un nombre de cycles proportionnel au travail
ARM réel — juste pas modélisé par Stella.

## Conclusion pour la Porte 0

**Ce chiffre reste inconnu**, et ce n'est pas un manque d'effort : c'est une limite
dure de l'outillage disponible (même constat que le scintillement CRT en 5.2/9.1,
backlog.md § Protocole IA — "Limite dure, pas de tooling qui la contourne"). Deux
voies possibles pour la lever, ni l'une ni l'autre tentée ici :
- **Hardware réel** (Lane 1) + oscilloscope/logic analyzer sur le bus de données,
  ou un programme de mesure similaire à celui-ci mais lu sur cartouche Harmony réelle.
- **Désassemblage du driver ARM** (`DPCplus.arm`, binaire brut sans symboles) pour
  compter manuellement les cycles ARM de sa boucle de dispatch/NOP-stuffing, puis
  convertir en équivalent 6507 via le ratio d'horloge (~70 MHz ARM vs ~1,19 MHz
  6507, facteur ~58,8×) — faisable en théorie (`arm-none-eabi-objdump` disponible),
  pas tenté : reverse engineering non trivial sans symboles ni documentation du
  binaire.

## Reproduire

Nécessite (non installés dans `.devcontainer` — ajout à évaluer si ce genre de
spike ARM redevient utile) : `wasmtime`, `arm-none-eabi-gcc`, `xdotool`, et les
fichiers `includes/` de l'extension `chunkypixel.atari-dev-studio` (déjà présents
dans tout Codespace qui suit `.vscode/extensions.json`).
