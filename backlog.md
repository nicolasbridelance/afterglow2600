# Backlog de démarrage — Atari 2600 / Casse-briques
Légende : 🔴 bloqué · 🟡 prêt à démarrer · 🟢 fait · ⚪ pas commencé

---

## Lane 0 — Spikes bloquants (rien après ne démarre sans porte validée)
- 🟡 Spike 0.1 — Bus stuffing + sprite natif mobile, même scanline
  - Sortie attendue : oui/non + marge de cycles mesurée
  - Si non → réouvrir architecture 4.2 avant toute autre lane
  - **Mesure du 2026-08-31** (`spikes/spike_0_1/spike_0_1.asm`, vérifié mécaniquement par `tools/cycle_linter.py`) : une séquence bus-stuffée (PF0/PF1/PF2/COLUP0, technique confirmée par [Big Mess o' Wires — Atari 2600 Hardware Acceleration](https://www.bigmessowires.com/2023/01/23/atari-2600-hardware-acceleration/), $FF préchargé + `STA` zéro-page = 3 cycles/écriture) interrompue par un repositionnement/rafraîchissement de sprite natif (`HMOVE` + `GRP0`) tient en **39 cycles sur 76 disponibles/ligne NTSC — marge de 37 cycles**. Structurellement viable et assemblé sans erreur (DASM `-f3`).
    - **Mise à jour 2026-08-31 (Stella headless confirmé disponible)** : `spike_0_1.bin` boot proprement sous Stella (`xvfb-run`, voir § Protocole IA / Émulation) — type de bankswitch "4K" correctement détecté, aucun crash. Mais ce ROM est une cartouche 4K simple, PAS un vrai DPC+/CDFJ+ARM : Stella n'y exécute donc aucun vrai bus-stuffing (les `STA` écrivent littéralement l'octet de `A`, sans substitution ARM). **Non prouvé ici** : le comportement réel du firmware ARM Harmony/Melody face à une écriture native (`GRP0`) intercalée dans une séquence bus-stuffée qu'il doit suivre pour savoir quel octet substituer. Stella émule bien DPC+/CDFJ (cœur ARM Thumbulator) — un futur spike construit comme vrai ROM CDFJ+ pourrait lever cette limite précise sans attendre le hardware réel, mais ce n'est pas un effort trivial (driver ARM, header bankswitch) et n'a pas été tenté ici. Hardware réel (Lane 1) reste nécessaire dans tous les cas pour le scintillement/persistance CRT (jugement humain, pas automatisable). Verdict à considérer comme "structurellement oui (DASM + Stella), comportement ARM bus-stuffing réel non vérifié" plutôt qu'un oui/non définitif.
- ⚪ Spike 0.1b (optionnel, non bloquant) — construire `spike_0_1` en vrai ROM CDFJ+ (driver ARM + header bankswitch) pour vérifier sous Stella (émulation ARM Thumbulator) le comportement réel du bus-stuffing face à une écriture native intercalée, sans attendre le hardware réel. Piste identifiée le 2026-08-31 — **mise à jour même jour** : le pipeline nécessaire (bB+wasmtime+arm-none-eabi-gcc+driver DPC+/CDFJ réel) a depuis été construit et prouvé fonctionnel pour Spike 0.2 (`spikes/spike_0_2/`), donc ce n'est plus "effort non trivial, pas tenté" mais une extension directe de ce qui existe déjà — reste non tenté faute d'avoir été demandé, pas faute de faisabilité
- 🟡 Spike 0.2 — Coût réel d'un aller-retour ACE (6507 → ARM → 6507)
  - Sortie attendue : coût fixe en cycles
  - Si >15-20 cycles → revoir découpage logique/rendu (section 6)
  - **Mesure du 2026-08-31** (`spikes/spike_0_2/`, détail complet dans son README) : mécanisme confirmé (`STA CALLFUNCTION` avec `A=$FF`, driver ARM bourre le bus de NOP pendant l'exécution — SpiceWare, *DPC+ARM Part 7*). Un vrai ROM DPC+ 32K avec une fonction ARM custom compilée (`arm-none-eabi-gcc`, driver `DPCplus.arm` de l'extension `chunkypixel.atari-dev-studio`) a été construit et exécuté sous Stella headless pour mesurer le coût réel.
  - **Résultat : chiffre non obtenu — limite dure de l'outillage, pas un échec de méthode.** En lisant le code source de Stella (`stella-emu/stella`, `src/emucore/CartDPCPlus.cxx`, commit `0969155`), la fonction `callFunction()` traite explicitly l'appel ARM comme s'exécutant "in zero 6507 cycles" — Stella ne modélise AUCUN coût de cycle 6507 pour l'aller-retour ACE, quelle que soit la fonction appelée. Les mesures faites (chronométrage RIOT TIM1T/TIM64T/T1024T autour de l'appel) donnent des résultats mutuellement incohérents (~10 / ~64+ / ~1024+ cycles) précisément parce qu'il n'y a rien de réel à mesurer côté émulateur — confirmé par un témoin de méthode qui, lui, mesure juste (20 NOP → 44 cycles lus, cohérent).
  - **Sur hardware réel, ce coût existe et reste inconnu.** Deux voies non tentées pour le lever : session hardware réelle (Lane 1) avec instrumentation, ou désassemblage manuel du driver ARM (binaire sans symboles, `arm-none-eabi-objdump` disponible mais reverse engineering non trivial).
  - **Conséquence pratique immédiate** : ne PAS appeler l'ARM en plein kernel d'affichage tant que ce chiffre n'est pas confirmé sur hardware réel — traiter l'hypothèse pessimiste (>15-20 cycles, section 6) comme active par défaut.
- ⚪ **Porte 0 — Sign-off lead dev/CTO explicite** sur 0.1 et 0.2, daté et écrit
  - Rien en Lane 2 (Proto 1+) ne démarre avant cette porte

## Lane 1 — Dépendances externes (en parallèle dès maintenant, pas en fin de projet)
- ⚪ Identifier 2-3 contacts scène homebrew (AtariAge) avec cartouche Harmony/Melody + vrai CRT
- ⚪ Confirmer leur dispo pour tests réguliers (pas juste au build final)
- ⚪ Décision "priorité CRT vs Stella récent" (section 2) — actuellement non tranchée dans le cahier des charges, à trancher avant Proto 2 (FRC/entrelacement en dépendent)

## Lane 2 — Socle moteur (après Porte 0)
- ⚪ Proto 1 — Preuve de rendu vecteur (bus stuffing seul)
- ⚪ Proto 2 — Scène statique complète (2 couches, FRC 2 paliers)
  - Sous-item : Spike FRC (9.2 pt.4) — bascule table en vblank, à vérifier cycle par cycle avant ce proto
- ⚪ Proto 3 — FRC poussé (3-4 paliers, validation scintillement CRT réel via Lane 1)

## Lane 3 — Vertical slice flagship
- ⚪ Proto 4 — Casse-briques jouable minimal
  - Physique balle/raquette (ARM)
  - Grille de briques — palier principal (sprites bus-stuffés) ou repli (playfield asynchrone) selon résultat Spike 0.1
  - Kernel score 4 chiffres (4.6.3)
  - Audio Proto 4 (piste A ou B à trancher, table de transformations)
  - Juice Proto 4 (hit-stop, flash, squash)
  - Spike 5 — paddle vs manette, à reconfirmer si Spike 0.1 impose un contrôle plus fin

## Lane 4 — Vertical slices de validation (après retour d'expérience Casse-briques)
- ⚪ Proto 5 — Le Jumper (une colonne)
- ⚪ Proto 6 — Octopus (un cycle)

## Lane 5 — Extensions (hors scope tant que Lane 3 n'est pas bouclée)
- ⚪ Multiplexage de sprites, HMOVE fine, FRC dithering temporel
- ⚪ Mode canon musical, second thème in-game
- ⚪ Débris de brique, tremblement d'écran

---

## Méthodologie (solo dev)

### Cadence
Pas de sprints calendaires — un sprint suppose un découpage arbitraire du temps, alors qu'ici la progression est gouvernée par des portes binaires (spike réussi/échoué), pas par des semaines. Rythme recommandé à la place :
- **Check-in de 5 min en début de session** : relire ce backlog, noter où on s'est arrêté et pourquoi. Sans ça, chaque reprise après une pause coûte du temps à reconstruire le contexte — coût invisible en solo, personne ne le voit sauf toi.
- **Log daté par porte franchie**, pas par jour travaillé. Un journal quotidien génère du bruit ; un journal de décisions reste utile dans 6 mois.

### Régime de test (pas de tests unitaires classiques ici — asm cycle-critique ne s'y prête pas)
1. **Comptage manuel de cycles** (déjà posé en 11.3) — check avant tout commit touchant la boucle scanline
2. **Stella cycle-exact** — oracle de vérification, jamais substitut au comptage manuel (règle déjà dans le doc, à ne pas relâcher parce qu'on est pressé)
3. **Capture de référence versionnée** (screenshot Stella) à chaque proto validé — comparaison avant/après pour toute modif du kernel d'affichage, seule façon de détecter une régression visuelle silencieuse
4. **Session hardware réelle budgétée** — pas à chaque commit, mais à chaque porte franchie en Lane 2/3 (Proto 2, 3, 4), via les contacts de la Lane 1

**Definition of Done par kernel** : comptage manuel bon + confirmé par Stella + pas de régression vs capture de référence + (pour les protos majeurs) passé sur au moins une session hardware.

### Conventions de code
Ce qui existe déjà (11.2 organisation fichiers, 11.3 discipline d'optimisation) reste la base. À ajouter, dans un fichier séparé **`CONVENTIONS.md`** (pas dans le cahier des charges, qui est un doc de vision/architecture — pas de règles du quotidien) :
- **Nommage** : préfixer les labels par jeu (`bo_`, `jp_`, `oc_`) pour éviter les collisions entre kernels assemblés dans le même `.bin`
- **Commits git** : préfixer par lane/porte (ex. `[spike0.1] mesure cycles bus-stuffing+GRP0`) — utile même en solo pour retrouver "à quel commit le Spike 0 a été validé"
- **Branches** : trunk-based, une branche courte par spike/proto, merge seulement si la Definition of Done ci-dessus est cochée
- **Commentaires** : format `; N cycles, position X, doit finir @Y-Z` obligatoire sur tout le chemin critique (déjà posé en 11.3) ; côté ARM, commentaires "pourquoi" plutôt que "quoi", la marge de cycles y rend le code plus lisible en prose

### Qui décide
En solo, tu es lead dev **et** CTO — la porte 0 (section 9.2) n'a personne d'autre pour la signer. La valeur du process n'est pas d'avoir un tiers qui valide, c'est d'avoir une **trace écrite** qui empêche de refaire un arbitrage déjà tranché ou d'oublier pourquoi. Ce backlog + le cahier des charges + `CONVENTIONS.md` jouent ce rôle : chaque porte franchie doit être actée par une ligne écrite (ici ou en commit), pas seulement "su" dans ta tête.

---

## Protocole IA (si le solo dev est un modèle IA, pas un humain)

Différence structurante : pas de mémoire entre sessions. Le repo n'est pas la documentation du process, il *est* la mémoire — toute décision non écrite ici n'existe pas à la session suivante.

- **Comptage de cycles** : annotation obligatoire (11.3) + **vérifié mécaniquement**, pas seulement à l'œil. Outil : `tools/cycle_linter.py` — parse le listing DASM, somme les cycles entre `WSYNC`, fait autorité sur le comptage manuel (version minimale posée au Spike 0.1, à étendre avant Proto 1). (DASM n'était PAS présent par défaut dans le sandbox malgré ce qu'affirmait une version antérieure de cette ligne — installé via `apt-get install dasm` le 2026-08-31, persistance assurée par `.devcontainer/devcontainer.json`.)
- **Commentaires** : pas de pense-bête ligne à ligne (relecture à froid systématique, peu importe le délai) — bloc "pourquoi ce fichier / ce qu'il possède" en tête de fichier pour orientation rapide.
- **Tests** : pytest classique pour le rasterizer offline et la logique ARM extraite en fonctions pures ; le kernel 6507 est vérifié par le linter de cycles, pas par des tests unitaires au sens classique.
- **Émulation** : DASM permet l'assemblage et la vérification structurelle (registres, tables, budget de cycles). **Mise à jour 2026-08-31** : Stella *est* disponible via apt (`stella` + `xvfb`) et tourne bien headless dans ce sandbox (`xvfb-run -a stella -video software -audio.enabled 0 -holdreset <bin>` — testé sur `spike_0_1.bin`, boot propre, type de bankswitch correctement détecté "4K (4K Atari)", aucun crash). Contredit l'affirmation précédente de cette ligne ("non packagé") — vérifié en pratique plutôt que reconduit tel quel.
  - Ce que ça prouve : le ROM est structurellement valide au sens Stella (pas seulement DASM), il boot sans opcode illégal ni erreur fatale.
  - Ce que ça NE prouve PAS (pour l'instant) : le comportement du firmware ARM Harmony/Melody sur du bus-stuffing réel — nos spikes sont assemblés en ROM 4K simple, pas en vrai cartouche DPC+/CDFJ+ARM. Stella émule bien DPC+/CDFJ (cœur ARM Thumbulator) ; construire un vrai ROM CDFJ+ pour un futur spike est donc une voie plausible pour lever cette limite précise — pas tentée ici, effort non trivial (driver ARM, header bankswitch).
  - Capture d'écran / scintillement CRT automatisé : pas câblé — le mode "continuous snapshot" de Stella est un raccourci clavier runtime (aucun réglage persistant trouvé dans `stella.sqlite3`), pas un simple flag CLI. Faisable via injection de touche X11 (`xdotool`) mais pas fait ici ; de toute façon la persistance phosphore reste un jugement humain (point suivant).
- **Limite dure, pas de tooling qui la contourne** : le scintillement et la persistance phosphore CRT (5.2/9.1) ne sont pas évaluables depuis une capture d'écran statique, aussi bonne soit la vérification structurelle. Le jugement perceptif reste porté par l'humain / les contacts Lane 1 — capacité manquante, pas processus manquant.
- **Portes de décision** (Porte 0 notamment) : signées par l'humain, pas par l'IA — ce sont des décisions de possession du projet, pas des faits vérifiables par le code.

---

## Journal de décisions ouvertes (à trancher, pas à laisser dériver)
| Décision | Statut | Porte |
|---|---|---|
| CRT vs Stella récent en priorité dev | ⚪ non tranché | avant Proto 2 |
| Piste musicale A ou B pour Proto 4 | ⚪ non tranché | pendant Proto 4 |
| Paddle vs manette | 🟢 tranché (manette) | à reconfirmer post Spike 0.1 |
| Palier briques (sprite vs playfield) | 🔴 dépend de Spike 0.1 | après Porte 0 |

---
*Mettre à jour ce fichier à chaque porte franchie ou décision tranchée — c'est le journal de vérité du projet, pas le cahier des charges figé.*
