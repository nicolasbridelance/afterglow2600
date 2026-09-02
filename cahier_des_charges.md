# Cahier des charges technique
## Atari 2600 poussée au maximum matériel — moteur mutualisé, jeux à scope contenu
**Statut :** Draft v8 — **pivot architectural 2026-08-31 : abandon ARM/DPC+/CDFJ+/bus stuffing, retour 100% 6507/TIA natif, zéro coprocesseur.** Détail et justification complète : `PIVOT_INSTRUCTIONS.md` à la racine du repo. Ce draft réécrit toutes les sections qui supposaient le coprocesseur — la mécanique de densité graphique change de nature (voir §2 et §4.2), pas seulement la logique de jeu. **Réconcilié le 2026-08-31 avec une révision v8 concurrente produite en parallèle par une autre session** (l'utilisateur a fait réécrire le document des deux côtés sans le savoir) — les apports jugés solides de cette version parallèle (reformulation du pitch en §1, note DPC/Activision en §2, correction de l'ambition per-rangée vs per-brique en §4.2/§9/§12.10.4, mesures inlinées en §9.2, nuance kernel déroulé vs en boucle en §12.7) ont été intégrés ici plutôt que de laisser deux documents diverger.
**Destinataire :** Lead dev / équipe technique

---

## 1. Contexte & vision

Objectif : produire un ou plusieurs jeux Atari 2600 exploitant des techniques modernes (jamais accessibles aux développeurs des années 80 — méthodologie de conception, outillage de rastérisation offline, discipline de comptage de cycles assistée par outil) pour obtenir une densité visuelle jugée ambitieuse pour ce matériel — sans aucune extension qui changerait le CPU principal ou l'écran cible (TV NTSC standard).

**Note post-pivot (2026-08-31) :** cette phrase de cadrage n'a pas changé depuis la v1, mais son application l'a désormais rattrapée. Les drafts précédents (v2 à v7) ciblaient une cartouche Harmony avec coprocesseur ARM7TDMI pour la technique de bus stuffing — un microcontrôleur sorti en 2010, avec un cœur dont le premier exemplaire (ARM1) date de 1985, donc postérieur de 8 ans à la console visée, exécutant du code que la scène 6507 d'époque n'a jamais eu accès à. C'était une contradiction avec cette section, pas une extension conforme. Le pivot ferme cette contradiction : voir `PIVOT_INSTRUCTIONS.md`. Conséquence directe à assumer : la densité graphique visée redevient bornée par ce que le 6507 seul peut écrire par ligne (§2, §4.2) — moins spectaculaire que ce que le bus stuffing promettait sur le papier, mais c'est la version du projet qui honore réellement l'accroche "poussée au maximum matériel".

**Reformulation du pitch, pas seulement un aveu de perte.** Le vrai cœur du projet n'a jamais été "silicium impossible en 1977" — c'est "personne n'a pris le temps de pousser aussi loin, avec les outils d'itération et les références culturelles disponibles aujourd'hui". Le FRC, le hue-shift, le kernel de score 48-pixel, le playfield asynchrone, le moteur musical : tout ça est du logiciel pur, exécutable sur une cartouche de 1982, et rien de tout ça n'a jamais dépendu de l'ARM. Deux capacités survivent intégralement au pivot et restent la vraie source de valeur ajoutée 2026 : le pipeline de génération d'assets (raster IA → quantification → table TIA, inexistant avant 2022-2024) et le processus de conception lui-même — croiser un diviseur de fréquence TIA grossier avec une passacaille de Biber, retrouver le thème carcéral oublié du Breakout de 1976, vérifier chaque affirmation technique plutôt que la supposer. Objectif reformulé : **ce qu'un développeur de 1982 aurait fait s'il avait eu le temps, les outils d'itération modernes, et une bibliothèque de références culturelles instantanément accessible** — pas une revendication de dépasser la puce elle-même. Ça n'annule pas le recul de densité assumé ci-dessus (§2, §4.2, §9) ; ça dit juste que ce recul touche une partie de l'ambition, pas tout le projet.

**Pivot de scope (v1 → v2) :** le concept initial (un écran de combat JRPG unique, portrait de boss figé) a été remplacé par une approche délibérément plus "bordée" : des classiques arcade au ruleset minimal et déjà éprouvé (Casse-briques en priorité, Le Jumper et Octopus/Game & Watch en validation légère), choisis précisément parce qu'ils n'ont aucune inconnue de design à défricher. Toute l'énergie de l'équipe va sur l'optimisation et le rendu, pas sur l'invention de règles. Casse-briques a en plus une résonance particulière : c'est un genre né sur le matériel Atari d'origine (Breakout, 1976) — le reprendre avec nos techniques, c'est la maison qui pousse son propre jeu là où il n'avait jamais pu aller.

**Future-proofing sans scope creep :** le moteur est pensé dès le départ pour supporter plusieurs jeux (voir section 12), mais chaque jeu au-delà du premier est traité comme une **vertical slice volontairement mince** (un niveau, pas un jeu complet) — l'objectif est de valider que le socle partagé tient sur des genres différents, pas de livrer trois jeux finis.

**Référence explicite non visée :** aucun portage de jeu existant. Objectif = même densité visuelle perçue que nos techniques permettent, pas fidélité à un titre précis.

---

## 2. Plateforme cible

| Élément | Choix | Justification |
|---|---|---|
| Console | Atari 2600 NTSC | Cible historique, raster 262 lignes/60 Hz |
| Cartouche | Bankswitchée pure — **F6 (16 Ko, 4 banques)** par défaut, F8 (8 Ko, 2 banques) si un jeu tient dedans | Schéma standard, aucun coprocesseur embarqué ; le choix exact F6 vs F8 se fait jeu par jeu selon le budget ROM réel (§12.5), pas figé au niveau moteur |
| Cartouche de test hardware | Harmony/Melody, utilisée uniquement comme **flash cart générique** (charge n'importe quel `.bin` F6/F8 sans graver d'EPROM) | Outil pratique de la scène homebrew, indépendant du coprocesseur ARM qu'elle embarque par ailleurs — on ne l'utilise plus pour ses capacités DPC+/CDFJ/ACE |
| Driver bas niveau | Écriture TIA native (`LDA`/`STA` 6507 pur) | Plus de bus stuffing (mécanisme intrinsèquement dépendant du coprocesseur — voir note ci-dessous) ; la densité vient de la technique de playfield asynchrone (§4.2) et de l'usage disciplé des objets matériels, pas d'une substitution matérielle sur écriture |
| Coprocesseur | **Aucun** | Abandonné au pivot du 2026-08-31 — voir `PIVOT_INSTRUCTIONS.md` |
| Affichage cible principal | **CRT réel** | Les techniques d'entrelacement/FRC ne sont validées de façon fiable que sur tube cathodique |
| Affichage secondaire (dégradé) | Stella (émulateur) / LCD | Émulation cycle-exacte standard, aucune dépendance à un support de bus stuffing (plus utilisé) ; artefacts de synchro documentés sur écrans plats modernes pour l'entrelacement/FRC |

**Pourquoi le bus stuffing disparaît, pas seulement l'ARM :** le bus stuffing n'est pas un algorithme qu'on aurait pu réimplémenter en pur 6507 — c'est un mécanisme *matériel* où le coprocesseur de la cartouche intercepte le cycle d'écriture et substitue un octet sur le bus de données, indépendamment de ce que l'instruction `STA` porte réellement dans l'accumulateur (mécanisme documenté par Big Mess o' Wires, cf. §13). Sans coprocesseur, un `STA` écrit exactement l'octet qu'on y a mis — pour afficher une valeur différente à chaque écriture (le cas d'usage central de la couche sprite bus-stuffée de l'ancien §4.2), il faut revenir à la paire `LDA table,X` + `STA` classique, plus coûteuse en cycles. Voir §4.2 pour la conséquence sur l'architecture de rendu et §4.1/§12.10.4 pour la conséquence sur l'ambition de densité.

**Note pour référence future, si l'envie d'un assist matériel d'époque revient** : la seule vraie puce d'assistance produite en série pour une cartouche 2600 est le **DPC d'Activision (1983, David Crane, Pitfall II)** — un ASIC dédié d'époque, pas un ARM. Piste explicitement non retenue pour l'instant (nouvel outillage à défricher), mais correcte historiquement si un "mode ambition" est un jour souhaité — contrairement au coprocesseur ARM abandonné ici, celui-là ne contredirait pas §1.

**Décision à valider par le lead dev :** développement prioritaire pour CRT + Stella récent, avec un mode de repli (moins de paliers FRC, moins de densité) pour affichage moderne.

---

## 3. Contraintes matérielles dures (non négociables)

- CPU principal : MOS 6507 @ 1,19 MHz
- 262 scanlines/frame (NTSC) : 3 vsync + 37 vblank + 192 affichage + 30 overscan
- 76 cycles 6507 par scanline (228 color-clocks TIA ÷ 3) ; 73 cycles utiles si synchro par WSYNC
- Pas de framebuffer : chaque ligne est générée en temps réel ("racing the beam")
- Objets matériels natifs par ligne : 2 sprites (players), 2 missiles, 1 balle, 1 playfield
- Playfield natif : résolution 40×192 (chaque "pixel" = 4 color-clocks)
- Palette native : 128 teintes disponibles instantanément

Ces chiffres définissent le budget de calcul/affichage disponible à chaque ligne et ne peuvent pas être contournés — seulement exploités plus intelligemment.

### 3.1 Registres matériels additionnels identifiés (absents de la v1/v2 initiale)

**Détection de collision matérielle** — la TIA détecte nativement les collisions entre les 6 objets (2 joueurs, 2 missiles, balle, playfield) et les stocke dans 8 registres en lecture seule à $30-$37 (`CXM0P`, `CXM1P`, `CXP0FB`, `CXP1FB`, `CXM0FB`, `CXM1FB`, `CXBLPF`, `CXPPMM`), remis à zéro par un strobe sur `CXCLR` ($2C). Ces latches se lisent typiquement en vblank, une fois toutes les collisions de la frame déjà survenues.

**Audio TIA** — 2 canaux indépendants, chacun piloté par 3 registres : `AUDC0/1` (forme d'onde/contrôle), `AUDF0/1` (fréquence), `AUDV0/1` (volume). Absent du scope actuel, voir section 4.5.

**Lecture paddle** — les ports `INPT0-3` sont dédiés à la lecture de potentiomètre (décharge de condensateur, entrée analogique), distincts du protocole de lecture manette digitale. Voir décision section 12.6.

---

## 4. Architecture de rendu

### 4.1 Pipeline global

```
Asset source (vecteur : courbes, dégradés, silhouettes)
        │
        ▼
Rastérisation OFFLINE (build time, sur PC)
   → résolution des courbes par scanline
   → génération table de registres TIA (forme + couleur par ligne)
        │
        ▼
Table statique en ROM (contenu figé — seul chemin, plus de recalcul procédural
runtime coûteux : voir §7 pour ce que la génération procédurale devient sur 6507 pur)
        │
        ▼
Écriture native TIA (6507, `LDA`/`STA` — playfield asynchrone pour les briques,
objets matériels standard pour les éléments mobiles, voir §4.2)
```

Différence structurante avec les drafts précédents : plus de branche "recalcul par l'ARM entre deux tours" — tout le contenu qui variait dynamiquement doit maintenant soit être précalculé en table (discipline déjà posée en §11.3, qui s'applique donc plus largement qu'avant), soit être généré par un algorithme assez léger pour tourner sur le 6507 pendant le vblank/overscan (§6, §7).

### 4.2 Une seule couche de densité, plus une superposition — le playfield asynchrone devient le chemin principal

Les drafts v2-v7 empilaient deux couches : un playfield natif "doux" (160×192) et une couche de sprites bus-stuffés (96×192, détail fin) qui portait l'essentiel de la richesse visuelle. **Cette deuxième couche n'existe plus** — elle dépendait entièrement du bus stuffing (§2). Ce qui était documenté comme le **palier de repli** en 4.2.1 (draft v7) devient le **seul chemin** :

| Couche | Résolution effective | Usage | Technique |
|---|---|---|---|
| Playfield asynchrone | 40×192 natif, réécrit mi-ligne (`PF0/1/2`) pour casser la symétrie gauche/droite | Grille de briques, masses, dégradés larges | Réécriture native `PF0/1/2` en cours de ligne — technique du chapitre "Asynchronous Playfields: Bricks" de *Making Games for the Atari 2600* (Steven Hugg), voir §4.3 |
| Objets matériels natifs | 2 players, 2 missiles, 1 balle (§3) | Raquette, balle, débris (extension) | `GRP0/1`, `HMOVE`/`RESP`, techniques standard — plus de contrainte de coexistence avec une couche bus-stuffée sur la même ligne, cette question (ancien Spike 0 point 1) est éteinte par construction |

**Conséquence assumée sur l'ambition visuelle, précisée après relecture de l'ambition d'origine.** L'ambition posée dès §12.1 a toujours été "chaque **rangée** un dégradé de teinte propre" — une richesse *par ligne de briques*, pas par brique individuelle. C'est le palier "principal" du draft v7 (hue-shift/FRC complet *par brique*, via le précédent SpiceWare) qui avait fait glisser l'ambition au-delà de ce que §12.1 promettait réellement. Le playfield asynchrone seul reste donc **presque intégralement compatible avec l'ambition d'origine** (un dégradé par rangée) — ce n'est pas le renoncement total que la première rédaction de ce paragraphe laissait entendre.

Ce qui est réellement perdu, et qu'il ne faut pas non plus minimiser : l'embellissement per-brique du draft v7, et le multiplicateur de coût lui-même — une écriture native (`LDA table,Y`/`STA`, §12.7) coûte structurellement plus cher qu'une écriture bus-stuffée, donc moins de changements de couleur tiennent par ligne dans tous les cas. Ce qui reste pleinement disponible pour compenser : hue-shift/FRC *par ligne* (§5.2/5.3, mécanisme indépendant du bus stuffing), dithering spatial, et la direction artistique silhouette-first (§5.1) qui a toujours traité le détail fin comme secondaire à la masse.

#### 4.2.1 Ce point est résolu par le pivot, pas seulement discuté

Le contenu de cet ancien sous-titre ("représentation des briques : deux paliers") est maintenant fondu dans le tableau ci-dessus — il n'y a plus deux paliers à arbitrer selon un spike, il y a un seul chemin. Historique de la décision et des spikes qui l'ont éclairée (Spike 0.1, 0.1b) : `backlog.md` Lane 0 et `PIVOT_INSTRUCTIONS.md`.

### 4.3 Précédents techniques à étudier avant implémentation

- **Démo "RPG" (SpiceWare, forum AtariAge)** — *référence historique, plus applicable directement* : preuve de concept en matériel réel de 12 couleurs/scanline via bus stuffing + entrelacement pair/impair. Reposait sur le coprocesseur abandonné au pivot (§2) ; conservée ici comme repère de ce qu'un vrai hardware acceleration permettait, pas comme base de notre couche de rendu.
- **Démo "128 Chronocolour" (même équipe)** : tentative d'aller jusqu'à 128 teintes par pixel via alternance de trames — jugée impraticable en usage réel à cause du scintillement. Toujours pertinente : c'est un garde-fou sur la limite haute du FRC (§5.2), mécanisme indépendant du bus stuffing.
- ***Making Games for the Atari 2600* (Steven Hugg), chapitre "Asynchronous Playfields: Bricks"** — **référence centrale du draft actuel**, plus seulement un repli : construite précisément sur un jeu façon Breakout, c'est la technique qui porte maintenant toute la couche de densité (§4.2).

### 4.4 Détection de collision — approche recommandée

**Décision : s'appuyer sur les registres matériels (section 3.1), pas sur du calcul logiciel.** Pour Casse-briques, deux collisions à détecter par frame : balle-brique et balle-raquette. Si la balle est un missile TIA et la raquette un player, `CXM0P` donne directement balle-vs-raquette. Si les briques sont portées par le playfield, `CXM0FB` donne balle-vs-brique(s) en un seul read. Ça évite tout calcul explicite pour une opération que le matériel fait gratuitement — les latches s'accumulent pendant l'affichage et se lisent en une passe pendant le vblank suivant, avant le `CXCLR`. Post-pivot, cette décision n'est plus seulement "la plus prudente" (elle évitait un aller-retour ARM au coût alors inconnu) — elle est la seule option qui existe, puisqu'il n'y a plus d'ARM vers qui aller.

**Limite à valider en Proto 4** : les registres disent *qu'il y a eu* collision, pas *où* précisément sur la ligne — pour identifier *quelle* brique a été touchée quand plusieurs sont sur la même ligne, il faudra probablement croiser avec la position X connue de la balle au moment du strobe. À concevoir pendant le Proto 4, pas avant — ce n'est pas bloquant pour le reste de l'architecture.

### 4.5 Son — moteur musical adaptatif

Angle mort identifié à l'origine : zéro ligne sur l'audio dans les versions précédentes de ce document, alors que 2 canaux TIA sont disponibles (`AUDC0/1`, `AUDF0/1`, `AUDV0/1` — voir section 3.1). Ce qui suit remplace le scope minimal initial (deux bruitages génériques) par une architecture complète, conçue spécifiquement pour contourner la limite de 2 canaux plutôt que la subir.

#### 4.5.1 Principe directeur : le bruitage n'est jamais un son séparé

Décision structurante : au lieu de faire lutter "musique" et "bruitage" pour les 2 mêmes canaux (ce que ferait un vol de canal classique), **chaque événement de gameplay est une transformation appliquée à la note du thème en cours**, jamais un son indépendant plaqué par-dessus. Ça élimine le conflit à la racine plutôt que de le gérer.

#### 4.5.2 Répartition des canaux

- **Canal 1 — socle harmonique fixe** : une basse obstinée qui boucle sans interruption, jamais dérangée par les événements de jeu. Coût : quelques écritures AUDF par temps.
- **Canal 2 — voix réactive** : porte le thème musical, dont la *lecture* (pas le contenu) se déforme temporairement selon les événements de gameplay, via des tables précalculées parallèles à la table du thème.

#### 4.5.3 Deux pistes sélectionnables (A/B — clin d'œil à la convention d'époque)

Sélection via le switch console "Game Select" (registre `SWCHB`, déjà croisé en 3.1 pour son bit noir&blanc) — exactement la convention Atari d'origine pour proposer deux variantes de jeu, réutilisée ici pour deux ambiances musicales. Les deux œuvres sont dans le domaine public (aucune question de droits, cohérent avec la stratégie de sourcing déjà posée) :

| | Piste A | Piste B |
|---|---|---|
| Œuvre | *Ah vous dirai-je, Maman*, 12 Variations K.265 — Mozart (1785) | Passacaille en sol mineur (Sonate du Rosaire) — Biber (c. 1676) |
| Canal 1 | Basse d'Alberti (accord arpégé fondamentale-quinte-tierce-quinte, boucle rapide) | Ostinato à 4 notes descendantes (sol-fa-mi♭-ré), boucle fixe, aucune progression harmonique à gérer |
| Canal 2 | Thème + variations de Mozart, sélectionnées selon l'état du jeu | Ligne virtuose de Biber, dont l'escalade naturelle de la pièce colle directement à la montée de tension en fin de partie |
| Pourquoi ce choix | Familiarité mélodique maximale (le thème est universellement reconnu) | Techniquement encore plus simple à porter (pas de changement d'accord sur canal 1) et dramaturgiquement déjà pensée pour l'escalade |

**Rejeté après étude, pour référence future :** une fugue de Bach (Prélude et Fugue n°10) a été écartée — une fugue tire sa substance de l'indépendance de 3-4 voix, ce que la réduction à 2 canaux détruit précisément. Voir 12.8 pour l'alternative retenue comme piste d'extension.

#### 4.5.4 Tables de transformation — catalogue complet des événements

Chaque événement déclenche la lecture d'une table parallèle à la table du thème (même longueur, une entrée par note), jamais un calcul à la volée (interdit de toute façon par la discipline d'optimisation, section 11.3). Deux familles de transformation : **tonale** (décalage de hauteur — pour les événements "musicaux") et **timbrale** (changement de forme d'onde via `AUDC` — pour les événements "d'impact"), afin que l'oreille distingue instantanément le type d'événement sans effort.

| Événement | Famille | Transformation | Scope |
|---|---|---|---|
| Rebond raquette | Tonale | +8 (octave), 2 temps, retour auto à la table normale | Proto 4 |
| Rebond mur | Tonale | +4 (quinte), 1 temps — même famille que le rebond raquette mais distinguable à l'oreille | Proto 4 |
| Casse brique | Timbrale | Bascule `AUDC` vers bruit sur la note courante, décroissance rapide de `AUDV` | Proto 4 — **le grand absent identifié, à corriger** |
| Balle perdue (vie restante) | Tonale | Motif descendant 2-3 notes, ne stoppe **pas** le séquenceur (distinct du game over terminal) | Proto 4 |
| Lancement de balle (service) | Tonale | Glissando ascendant (balayage rapide d'`AUDF`) juste avant la reprise normale du thème | Proto 4 |
| Bonus | Tonale | Trille (voisin supérieur ou inférieur du degré courant) | Proto 4 |
| Game over | Tonale | Cadence fixe Fa-Sol-Do (3 notes), **arrête le séquenceur** — terminal par construction, canal 1 résout sur la tonique en même temps | Proto 4 |
| Combo/enchaînement | Tonale | Montée de pitch progressive à chaque brique cassée sans perdre la balle (1 palier par brique, remis à zéro à la perte) | Extension (12.8) — lien direct avec le juice (12.9) |
| Mur/niveau terminé | Tonale | Petite fanfare ascendante résolutive, distincte du bonus | Extension (12.8) |
| Alerte near-miss (balle proche du bas) | Timbrale | Grondement bas, `AUDC` bruit grave en boucle tant que la balle reste en zone de danger | Extension (12.8) |

**Priorité par défaut si plusieurs événements se chevauchent** (à ajuster à l'oreille en Proto 4) : game over > balle perdue > mur terminé > bonus > combo > casse brique > rebond raquette > rebond mur > lancement de balle.

**Caveat de fabrication, réel et non négligeable** : `AUDF` est un diviseur entier grossier (32 valeurs). Un décalage de hauteur (octave, quinte) ne tombe pas toujours sur une valeur de diviseur valide, surtout dans le grave — chaque paire note/décalage de chaque table doit être vérifiée à l'oreille et figée à la main, pas calculée. C'est un travail de copiste à budgéter comme tel dans le planning, pas seulement du code.

#### 4.5.5 Sélection de variation — deux déclencheurs distincts

- **Anti-répétition** (éviter d'entendre toujours les 6 mêmes mesures) : compteur simple — toutes les N boucles du thème, avance d'une variation dans une liste ordonnée
- **Accompagnement de tension** (ex. 30 dernières secondes = version la plus virtuose/énervée de la piste) : test d'état de jeu (chrono ou briques restantes) qui **force** une variation spécifique, prioritaire sur la rotation anti-répétition

#### 4.5.6 Scope Proto 4 vs extension

Proto 4 : une piste (A ou B, à trancher lors du prototypage), socle + thème + les tables de transformation marquées "Proto 4" ci-dessus + les 2 déclencheurs de variation. Le mode canon et le mode "second thème" (Bach) sont documentés en 12.8 comme extensions, pas comme prérequis.

#### 4.5.7 Musique de menu — contraintes différentes, choix distinct

Le menu (Titre/Sélection) n'a pas besoin des "crochets" de transformation réactive (4.5.4) : aucun événement de jeu n'arrive pendant la navigation. Ça change la contrainte de fond : plus besoin qu'un canal reste un socle pur et jamais interrompu — les deux canaux peuvent porter un vrai contrepoint indépendant, sans hiérarchie socle/voix réactive.

**Choix retenu : une Invention à 2 voix de Bach (BWV 772-786), déjà identifiée en 12.8 comme alternative à la fugue écartée en 4.5.3** — repositionnée ici plutôt qu'en mode caché in-game, parce que c'est précisément l'écran qui offre les bonnes contraintes pour l'exploiter sans compromis (écrite nativement pour 2 voix indépendantes, aucune réduction nécessaire). Suggestion par défaut : l'Invention n°1 en ut majeur BWV 772, la plus connue du recueil et la plus immédiatement accueillante — à confirmer à l'oreille en Proto 4, le choix précis de l'Invention n'est pas figé.

**Bruitages de menu**, cohérents avec le principe 4.5.1 (transformation plutôt que son séparé) :
- **Sélection** (déplacement du curseur) : décale la note courante de l'Invention d'un degré dans le sens du déplacement — correspondance directe geste/son plutôt qu'un clic générique
- **Validation** (confirmation) : mini-cadence résolutive non-terminale (contrairement à la cadence game over) qui accompagne la transition vers l'écran de jeu

Les deux sont en scope Proto 4 — coût comparable aux transformations déjà budgétées.

### 4.6 Kernel d'affichage du score

Point resté ouvert depuis la section 9.2 (signalé indirectement par la revue externe) — spécifié ici. Aucune unité matérielle de texte n'existe sur cette machine : le score doit être dessiné avec les mêmes objets (players/missiles/playfield) que le reste du jeu.

#### 4.6.1 La technique de référence : le "48-pixel kernel" (6 chiffres)

Technique documentée et réputée être l'un des kernels les plus exigeants de la scène 2600 :
1. `NUSIZ0`/`NUSIZ1` configurés en "3 copies rapprochées" — chaque player se répète automatiquement 3 fois sur la ligne, à intervalle fixe
2. Player0 positionné décalé de 8 pixels par rapport à player1 (exactement la moitié de l'écart entre copies) — leurs copies s'entrelacent : P0, P1, P0, P1, P0, P1 → 6 emplacements de 8 pixels = 48 pixels = 6 chiffres, avec seulement 2 objets matériels
3. Entre chaque copie, `GRP0`/`GRP1` doivent être réécrits avec le chiffre suivant, au cycle près — le registre `VDEL` (delay vertical) sert de tampon pour que le timing fonctionne : 7 écritures sont nécessaires pour afficher 6 chiffres, la dernière étant une écriture "fantôme" qui applique le chiffre resté en attente

C'est un troisième kernel à part entière, avec sa propre discipline de comptage de cycles (même rigueur qu'en 11.3, mécanisme entièrement différent du bus stuffing).

#### 4.6.2 Ce que ça implique pour notre architecture

- **Partage d'objets, résolu par séparation de lignes** : player0 est déjà la raquette (4.4), player1 est déjà proposé pour les débris de brique (12.9.3, extension). Résolution standard : la bande de score occupe quelques lignes tout en haut de l'écran, *avant* la zone de jeu — pendant ces lignes-là, "player0/player1" signifient "chiffre 1/chiffre 2" ; dès qu'on entre dans la zone de jeu, leur rôle est redéfini en raquette/débris. Pattern valide et courant sur 2600 (l'identité d'un objet matériel n'est pas fixe pour toute la frame), mais explicité ici pour éviter toute confusion en code entre les deux usages de player1. **Détail d'implémentation à ne pas oublier** : ce changement de rôle implique aussi de reprogrammer `NUSIZ0`/`NUSIZ1` (3-copies pour le score → normal pour le jeu) à la frontière entre les deux bandes, pas seulement les registres graphiques `GRP0`/`GRP1`.
- **BCD plutôt que binaire pur** : convertir un score binaire en chiffres décimaux demanderait une division, interdite par la discipline d'optimisation (11.3). Le score doit être stocké directement en BCD (un chiffre décimal par octet/nibble), incrémenté directement par la logique de collision (4.4) — conséquence naturelle d'une règle déjà posée, pas une contrainte nouvelle.
- **Score strictement côté 6507, compteur BCD.** La détection de collision est matérielle (décision de 4.4) — le score s'incrémente directement à la lecture des latches de collision en vblank. Ce point était déjà anticipé comme un risque à éviter dans les drafts précédents (le score ne devait jamais dépendre du coût alors inconnu d'un aller-retour vers l'ARM) ; le pivot ferme la question définitivement puisqu'il n'y a plus d'ARM vers lequel un tel risque pourrait exister.
- **Budget de cycles distinct** : ces lignes n'ont aucun rapport avec le kernel de briques (playfield asynchrone) — c'est un troisième budget à documenter séparément, pas une extension du premier.

#### 4.6.3 Scope recommandé pour le Proto 4

Viser **4 chiffres (2 copies au lieu de 3)** plutôt que le 6-chiffres/48-pixel complet dès le premier jet — timing sensiblement plus simple à maîtriser, cohérent avec la discipline générale d'éviter le scope creep (section 12.1). Le 6-chiffres complet devient un item de polish, pas un prérequis.

### 4.7 Sourcing des assets visuels — décision

Le pipeline 4.1 n'a jamais réellement exigé du vecteur — il a seulement besoin d'une source assez résolue pour être rééchantillonnée par scanline, vecteur ou raster indifféremment. La vraie question n'est donc pas "vecteur ou raster" mais "qui/quoi produit la source". Deux options réelles :

- **Génération raster par IA** (image générée puis passée par un script de quantification/dithering vers la table TIA) — cohérent avec la stratégie déjà retenue pour l'audio (bfxr + domaine public plutôt que composition commandée, section 4.5) : aucun scope creep de commission, itération rapide.
- **Illustrateur·rice freelance** (vecteur ou raster, peu importe pour le pipeline) — plus de contrôle et de fiabilité, mais réintroduit exactement le type de dépense/scope creep qu'on a refusé pour la musique.

**Décision retenue : génération IA raster en premier, validée par un micro-spike avant tout engagement de pipeline** (une image générée, quantifiée, jugée sur Stella/CRT — une session, pas plus, dans le même esprit que le Spike 0 de la section 9.2). L'illustrateur·rice freelance reste un plan B assumé si le micro-spike déçoit, pas le choix par défaut. **Risque à surveiller** : une image générée peut sembler magnifique en pleine résolution et devenir franchement mauvaise une fois brutalement réduite à quelques teintes — ne jamais juger une image générée avant de l'avoir vue *après* quantification, jamais avant.

### 5.1 Direction artistique (corrige le "programmer art" des démos existantes)

- **Hue-shifting** plutôt que simple dégradé de luminance sur une teinte unique (ex. : ombres vers le violet/bleu, hautes lumières vers le jaune/orange)
- **Dithering spatial** pour les transitions entre teintes adjacentes, en complément du dégradé natif
- **Priorité à la silhouette** sur le détail à cette résolution — contraste de valeur fort, formes lisibles
- Contours teintés plutôt que noir pur

### 5.2 Extension perçue de la palette (FRC — Frame Rate Control)

Principe : alterner deux teintes sur un cycle de N frames réelles, avec pondération temporelle — mécaniquement identique au rendu de niveaux de gris par alternance déjà utilisé sur calculatrices graphiques (TI-89 et similaires), généralisé ici à 2 axes (teinte + luminance) plutôt qu'à un seul (noir/blanc).

**Contraintes à respecter impérativement :**
- Le FRC ne fait qu'interpoler entre couleurs déjà présentes dans la palette (aucun élargissement du gamut)
- Limiter à **3-4 paliers de cycle maximum** sur CRT (au-delà, scintillement visible documenté par les précédents)
- Le rythme lent du gameplay (image figée entre les tours) est ce qui rend cette technique utilisable sans pénalité de mouvement — ne pas l'appliquer à du contenu qui bouge frame par frame

Estimation réaliste : ~300-400 teintes perçues distinctes sur CRT bien réglé, à valider empiriquement — **pas un chiffre garanti**, dépend de l'écran et du choix des paires de teintes.

### 5.3 Mécanisme de bascule FRC — vérifié cycle par cycle (voir 9.2)

Point ouvert signalé par la revue externe du document : le FRC suppose de basculer entre 2 (ou N) tables de teintes d'une frame réelle à l'autre. Piste retenue : la bascule se fait **une fois par frame, en vblank**, via du code auto-modifiant — l'octet de poids fort de l'opérande d'un `LDA table,Y` fixe dans le kernel scanline est réécrit en vblank pour pointer vers la table active. Le kernel scanline lit toujours "la table active" sans savoir laquelle c'est : l'opcode exécuté ($B9, `LDA abs,Y`) est structurellement identique quelle que soit la table pointée, donc la boucle scanline elle-même ne coûte rien de plus. Le seul coût ajouté est dans le vblank, où le budget est large (section 6).

**Vérifié mécaniquement le 2026-08-31** (`spikes/spike_frc/`, spike FRC de la section 9.2, point 4) : bascule + patch mesurés à 26 cycles (budget vblank ~2000-2700), lecture scanline patchée à 12 cycles/76 — identique quelle que soit la table active. Contrainte de conception à respecter dans l'implémentation réelle : chaque table doit tenir dans une seule page mémoire pour la plage d'offsets `Y` utilisée (poids faible de l'adresse de base + `Y` max < `$100`), sous peine d'une pénalité de franchissement de page sur `LDA abs,Y` — indépendante de la table active, donc elle ne romprait pas l'égalité de coût entre tables, mais romprait le budget scanline si négligée sur une table qui grossit.

---

## 6. Cadence de mise à jour — principe statique/dynamique

**Généralisation suite au pivot v2 :** la règle n'est plus "tour par tour = image figée" (spécifique au concept JRPG initial), mais un principe plus large qui s'applique à tous nos jeux, y compris ceux en temps réel continu :

> **Les techniques coûteuses (FRC, entrelacement, hue-shift poussé) ne s'appliquent qu'aux éléments visuels qui ne changent pas d'une frame à l'autre. Les éléments qui bougent en continu utilisent un rendu simple et sûr, sans entrelacement.**

Application par jeu :
- **Casse-briques** : la grille de briques est statique (elle ne change que quand une brique disparaît) → budget FRC/hue-shift complet. La balle et la raquette bougent chaque frame → rendu sprite natif standard, aucune technique d'entrelacement dessus (sous peine de réintroduire exactement le scintillement qu'on cherche à éviter sur un objet qui bouge).
- **Le Jumper** : les plateformes individuelles ne changent pas de complexité visuelle une fois positionnées, mais le défilement vertical les fait techniquement "bouger" à l'écran → nécessite une analyse dédiée en Proto Jumper, le principe ne s'applique pas tel quel.
- **Octopus/Game & Watch** : le décor de fond est statique, les segments qui s'allument/s'éteignent sont ponctuels → bon candidat pour le traitement riche sur le fond, simple sur les segments actifs.

**Budget de calcul post-pivot, revu à la baisse et à préciser en Proto 1 :** pendant les phases où l'affichage reste identique frame après frame (menu, attente, scène figée), le budget disponible est celui du vblank + overscan du 6507 seul — de l'ordre de 2000-2700 cycles utilisables par frame (37 lignes vblank + 30 lignes overscan, moins la resynchro WSYNC et le travail d'affichage déjà en cours), répété à 60 Hz. Les drafts précédents ajoutaient à ce chiffre "plusieurs dizaines de millions de cycles ARM par seconde d'attente" — cette marge n'existe plus. Ce n'est **pas un budget négligeable** pour de la logique de jeu simple (un Casse-briques n'a besoin ni de génération procédurale lourde ni de physique flottante), mais **c'est un budget qui doit maintenant être compté comme n'importe quel autre chemin critique** (discipline §11.3), pas traité comme "large donc ignorable" comme le faisait le principe commun de la section 7 dans les drafts ARM. Un jeu temps réel continu (Le Jumper, Octopus) reste protégé par le même principe statique/dynamique — le budget se libère aux frames où rien de nouveau n'a besoin d'être recalculé — mais la marge de confort en moins impose de vérifier ce chiffre tôt (Proto 1), pas de le supposer.

---

## 7. Logique de jeu (côté 6507, hors chemin critique d'affichage)

Toute la logique de jeu tourne désormais sur le 6507, dans les fenêtres vblank/overscan (§6) — il n'y a plus de section "côté ARM" séparée. Ce n'est pas nouveau pour la scène homebrew 2600 : la génération procédurale de niveaux 100% 6507 a un précédent célèbre et bien documenté (*Pitfall!*, Activision 1982, génère ses 255 écrans à la volée via un LFSR 6502 minimal) — l'idée que "procédural = a besoin d'un coprocesseur" n'a jamais été vraie sur cette machine, le pivot revient simplement à cette tradition plutôt que d'y déroger.

Usage par jeu candidat (voir section 12 pour le détail des règles) :

- **Casse-briques** : physique de rebond de la balle — **pas de calcul d'angle en virgule flottante ni de trigonométrie runtime** (interdit par §11.3), mais une table précalculée qui associe une zone d'impact de la raquette (découpée en 4-8 secteurs) à une paire `(HMP0 delta, direction Y)` fixe. Layouts de niveaux : privilégier des layouts **précalculés en ROM** (rastérisés offline comme le reste des assets, §4.1) plutôt qu'une génération procédurale runtime — un Casse-briques n'a pas besoin de variété infinie, et ça évite d'introduire un budget cycles supplémentaire sur un jeu qui n'en avait pas besoin dans les drafts précédents pour d'autres raisons
- **Le Jumper** : génération procédurale de la colonne de plateformes via un **LFSR 6507** (quelques instructions, coût trivial dans le budget vblank de §6) plutôt qu'un algorithme complexe — seed déterministe, table de types de plateformes indexée par les bits de sortie du LFSR
- **Octopus/Game & Watch** : gestion du cycle de rotation des bras et des fenêtres de passage — cadence déjà cyclique par nature (compteurs modulo, pas de génération procédurale), difficulté progressive pilotée par une table de paliers plutôt qu'un calcul

Principe commun, revu : tout calcul qui n'a pas besoin d'être resynchronisé à la ligne près se fait pendant vblank/overscan plutôt que dans la boucle scanline — mais contrairement aux drafts ARM, **ce budget n'est plus "large au point d'ignorer la généricité"** (§6) ; chaque algorithme choisi ici doit rester compatible avec la discipline §11.3 (pas de multiplication/division runtime, tables précalculées ou décalages de bits).

Le contenu **figé** (arrière-plans, tables de sprites, layouts de niveaux) doit être rastérisé une fois pour toutes au moment de la compilation de la ROM, pas recalculé à l'exécution — coût runtime nul pour ces éléments, principe inchangé par le pivot.

---

## 8. Outils & toolchain proposés

- Assembleur 6507 : DASM (ou cc2600 si l'équipe préfère un sous-ensemble C)
- Émulateur de développement/debug : Stella — plus de contrainte de version liée au bus stuffing (mécanisme abandonné, §2), n'importe quelle version récente convient
- Validation finale : matériel réel (cartouche Harmony/Melody utilisée comme flash cart générique, §2) + CRT
- Pipeline offline de rastérisation vecteur → table TIA : à développer en interne (script Python probable, à partir d'assets vectoriels sources)
- **Retiré au pivot** : `arm-none-eabi-gcc` et le driver `DPCplus.arm` (extension `chunkypixel.atari-dev-studio`) ne sont plus nécessaires — cette extension reste utile pour son support DASM/Stella générique (§11.1), mais plus pour sa capacité à compiler du code ARM

---

## 9. Risques identifiés

| Risque | Impact | Mitigation proposée |
|---|---|---|
| Scintillement inacceptable sur écrans modernes (LCD/OLED) | Démo injouable hors CRT | Mode de repli à densité réduite pour émulateur/écran plat |
| **Densité graphique en retrait sur l'embellissement per-brique du draft v7** (nouveau, conséquence directe du pivot — nuance importante : l'ambition *d'origine*, §12.1, "un dégradé par rangée", reste presque intacte, voir §4.2) | Le bus stuffing rendait un embellissement per-brique défendable en chiffres (§2) ; sans lui, le projet utilise la même classe de techniques que les titres 2600 récents déjà cités comme référence de faisabilité (§12.10.4) — mais pour l'ambition *par rangée* posée dès le premier draft, pas grand-chose ne change | Faire porter la différenciation par le playfield asynchrone + FRC/hue-shift/dithering cumulés (§4.2, §5.2) et par la direction artistique/musicale (§4.5, §12.10) plutôt que par un avantage matériel qui n'existe plus — recalibrer le discours de présentation (§12.9.5) en conséquence, sans sur-vendre ni sous-vendre le recul réel |
| Timing playfield asynchrone serré (réécriture `PF0/1/2` mi-ligne) | Bugs difficiles à diagnostiquer, dev lent | Suivre au plus près le chapitre de référence (Hugg, §4.3) plutôt que ré-improviser le timing from scratch ; comptage de cycles outillé (`tools/cycle_linter.py`) dès le premier kernel |
| Sur-promesse sur le nombre de teintes perçues | Attentes non tenues | Valider empiriquement sur prototype avant de communiquer un chiffre |

### 9.1 Leviers de réduction du scintillement (à arbitrer)

| Levier | Principe | Gain | Sacrifice | Décision |
|---|---|---|---|---|
| Entrelacement propre (vs scintillement naïf) | Chevauchement des bords de lignes entre trames paire/impaire | Détail vertical préservé, oscillation bien mieux masquée à l'œil | Timing driver plus complexe à coder (décalage demi-ligne) | **Retenu** |
| Réduction du nombre de lignes affichées (<262) | Fréquence de rafraîchissement effective augmentée (jusqu'à ~80 Hz testé) | Scintillement nettement amélioré | Signal hors standard NTSC : rejeté par la plupart des écrans modernes (image qui roule/se scinde), risque de compatibilité majeur | **Écarté** |
| Réduction des paliers FRC (3-4 → 2) | Cycle de mélange plus court, 30 Hz effectif | Scintillement perçu réduit | Palette perçue plus pauvre, moins de teintes intermédiaires | **Combiné avec les autres, à doser en Proto 3** |
| Masses solides plutôt que détail fin à haute fréquence spatiale | Le scintillement est quasi invisible sur grandes tuiles pleines, bien plus visible sur textures à petits points | Réduction perçue forte sans coût technique supplémentaire | Moins de texture fine, rendu plus "posterisé" | **Retenu** — cohérent avec la direction artistique silhouette-first (section 5.1) |

**Arbitrage retenu pour le Proto 2/3 :** combiner entrelacement propre + paliers FRC réduits + priorité aux masses solides. La réduction du nombre de lignes affichées est explicitement écartée en raison du risque de compatibilité avec les écrans modernes, documenté dans les précédents étudiés.

### 9.2 Spikes techniques (statut post-pivot)

Les drafts précédents listaient 5 spikes bloquants. Les points 1 (bus stuffing + sprite natif, même ligne), 2 (coût aller-retour ACE) et 3 (fidélité Stella sur cette combinaison) portaient tous sur l'interaction entre bus stuffing et objets natifs — **résolus par le pivot lui-même** : la question n'a plus d'objet puisque le bus stuffing est abandonné.

#### 9.2.1 Spikes archivés — ce qui a été mesuré avant que le pivot ne les rende sans objet

Ce travail reste la justification écrite de la décision de pivot, pas du travail perdu — détail complet : `backlog.md` Lane 0, `PIVOT_INSTRUCTIONS.md`.

| # | Spike (ancien) | Ce qui a été trouvé avant le pivot | Statut après pivot |
|---|---|---|---|
| 1 | Bus stuffing + sprite natif mobile, même ligne | **Mesuré structurellement** (`spikes/spike_0_1/`) : une séquence bus-stuffée interrompue par un rafraîchissement de sprite natif tient en 39 cycles sur 76 disponibles — viable en théorie. L'investigation complémentaire (`spike_0_1b`) a ensuite révélé que le type `CDFJ+` n'implémente dans Stella **aucune substitution sur écriture** — le vrai mécanisme vit dans un type `BUS` marqué EXPERIMENTAL, sans driver disponible dans l'outillage utilisé | 🟢 Résolu par pivot — plus d'architecture à double couche à faire coexister (§4.2), l'incertitude d'outillage disparaît avec la technique elle-même |
| 2 | Coût réel d'un aller-retour ACE (6507 → ARM → 6507) | **Non mesurable en émulateur** (`spikes/spike_0_2/`) : Stella traite l'appel ARM comme "zéro cycle 6507" par construction (`CartDPCPlus.cxx`). Un désassemblage manuel complémentaire (`spike_0_2b`) a chiffré une boucle voisine à ≈58 cycles ARM/octet (≈0,99 cycle 6507) — mais ce code ARM 32 bits classique n'est probablement jamais exécuté tel quel par Stella, qui n'émule que du Thumb | 🟢 Résolu par pivot — plus d'ARM vers lequel faire un aller-retour |
| 3 | Fidélité Stella sur la combinaison bus stuffing + sprite natif | Dépendait entièrement du point 1 | 🟢 Résolu par pivot, et mieux que ça : un ROM bankswitché simple est un des cas les mieux supportés par Stella (§2) |
| 5 | Paddle vs manette | Tranché en §12.6 (manette, pour la mutualisation input) | 🟢 Inchangé par le pivot — la clause de reconfirmation portait sur un résultat défavorable du point 1, qui n'est plus applicable |

Sur la qualité de ce travail : mesures structurelles, lecture de code source Stella plutôt que supposition, désassemblage manuel avec ses limites honnêtement notées ("non prouvé ici", "à confirmer dynamiquement") — une investigation rigoureuse, pas une excuse a posteriori pour le pivot.

#### 9.2.2 Dernier spike ouvert avant le pivot — résolu

| # | Spike | Question à trancher | Résultat |
|---|---|---|---|
| 4 | **Mécanisme de bascule FRC** | Détaillé en §5.3 — piste identifiée (code auto-modifiant en vblank) mais jamais vérifiée cycle par cycle | 🟢 **Mesuré le 2026-08-31** (`spikes/spike_frc/`) : bascule+patch 26 cycles (budget vblank ~2000-2700), lecture scanline patchée 12 cycles/76, coût identique quelle que soit la table active. Détail en §5.3. |

Ce spike était notablement plus léger que les précédents : pas de dépendance à du matériel non standard, pas d'ambiguïté d'émulation — juste un comptage de cycles sur un mécanisme entièrement documenté, mesuré par `tools/cycle_linter.py`. Effet de bord : a révélé et corrigé un bug de sous-comptage silencieux dans cet outil sur les instructions en adressage absolu (3 octets) — sans effet sur le résultat déjà publié de Spike 0.1 (§9.2.1). Plus aucun spike bloquant n'est ouvert ; la conception détaillée de Proto 1+ reste la prochaine étape (voir `PIVOT_INSTRUCTIONS.md` §4).

---

## 10. Jalons proposés

**Spike 0 — statut : résolu par pivot** (voir §9.2). **Spike FRC — statut : mesuré le 2026-08-31** (§9.2.2), plus aucun spike bloquant ouvert. Aucun sign-off supplémentaire requis pour démarrer Proto 1 sur le plan architecture — le pivot lui-même *est* la décision lead dev/CTO (`PIVOT_INSTRUCTIONS.md`).

**Socle partagé (avant tout jeu spécifique) :**
1. **Proto 1 — Preuve de rendu vecteur** : une forme simple (cercle + dégradé radial) rastérisée offline, affichée via écriture TIA native (playfield asynchrone, §4.2), comparée visuellement à la technique "programmer art" d'origine
2. **Proto 2 — Scène statique complète** : playfield asynchrone + objets natifs, hue-shifting + dithering, FRC à 2 paliers
3. **Proto 3 — FRC poussé** : montée à 3-4 paliers, validation scintillement sur CRT réel

**Vertical slice flagship :**
4. **Proto 4 — Casse-briques jouable minimal** : raquette + balle + une grille de briques complète, physique de rebond par table précalculée côté 6507 (§7), application du principe statique/dynamique (section 6)

**Vertical slices de validation (scope volontairement mince, cf. section 12) :**
5. **Proto 5 — Le Jumper, une colonne verticale** : défilement, génération procédurale de plateformes, sans système de score/progression complet
6. **Proto 6 — Octopus, un cycle complet** : bras rotatifs + une fenêtre de passage, sans les 5 trésors de la version finale

---

## 11. Environnement & workflow de dev

### 11.1 Stack proposée

| Couche | Outil | Rôle |
|---|---|---|
| IDE | VS Code + extension **Atari Dev Studio** | Éditeur, compilation, lancement émulateur — tout intégré, pas d'allers-retours terminal |
| Assembleur | **DASM** (macro-assembleur 6507) | Inclus dans Atari Dev Studio, standard de facto de la scène homebrew |
| Prototypage rapide | **8bitworkshop** (IDE navigateur) | Utile pour tester un fragment de kernel isolé sans setup local, avant de rapatrier le code dans le projet VS Code |
| Émulateur / debug | **Stella** (version récente ; plus de contrainte de support bus stuffing, §2) | Débogueur intégré cycle-exact : breakpoints, pas-à-pas, inspection registres TIA/RIOT en direct |
| Validation finale | Matériel réel (Harmony/Melody, utilisée comme flash cart générique, §2) + CRT | Seule validation fiable pour l'entrelacement et le FRC (cf. section 9) |
| Contrôle de version | Git | Fichiers texte purs (.asm/.h), workflow standard |

### 11.2 Organisation des fichiers

Pas un monolithe : convention multi-fichiers assemblés en un seul `.bin` par DASM via `.include`.

```
/engine                      → mutualisé entre tous les jeux (voir 12.3)
    vcs.h                    → constantes registres TIA/RIOT (fixe, ne change jamais)
    macro.h                  → macros communes (init RAM, etc.)
    playfield_async.asm      → réécriture mi-ligne PF0/1/2, générique (§4.2)
    input.asm                → lecture joystick/bouton, anti-rebond
    vblank_scaffold.asm      → gestion timer, structure de boucle de frame
/games
    /breakout
        kernel_breakout.asm  → boucle d'affichage bas niveau spécifique (playfield asynchrone, WSYNC, FRC sur la grille de briques)
        logic_breakout.asm   → physique balle/raquette (6507, table précalculée — §7)
        data_breakout.asm    → layouts de niveaux
    /jumper
        kernel_jumper.asm    → défilement vertical, positionnement plateformes
        logic_jumper.asm     → génération procédurale (6507, LFSR — §7)
    /octopus
        kernel_octopus.asm   → cycle des bras, fenêtres de passage
        logic_octopus.asm    → timing et difficulté (6507, table de paliers — §7)
/tools
    rasterizer.py            → pipeline offline vecteur → table TIA (hors ROM finale)
    cycle_linter.py          → vérification mécanique du budget de cycles (§11.3)
main.asm                     → point d'entrée, sélectionne le jeu à assembler
```

Principe directeur : **séparer le moteur (générique, mutualisé, stable) du contenu et du kernel d'affichage (spécifiques à chaque jeu, non partagés)** — détaillé en section 12.3. Le kernel d'affichage n'est PAS générique : c'est un choix assumé pour ne pas payer de coût d'indirection dans la boucle critique (voir 12.3 pour le détail de l'arbitrage).

### 11.3 Discipline d'optimisation (à appliquer dès le Proto 1)

- Annoter chaque instruction critique avec son coût cumulé en cycles (convention `; 3 cycles, position 38, doit finir @37-43`), vérifié mécaniquement par `tools/cycle_linter.py` — c'est la seule façon fiable de vérifier qu'un kernel tient dans son budget avant de le tester
- Variables chaudes (compteurs de boucle, pointeurs de table, état de tour) en page zéro systématiquement — 1 cycle de moins par accès qu'en adressage absolu
- Tables indexées alignées sur 256 octets pour éviter la pénalité de franchissement de page (+1 cycle imprévisible)
- Aucune multiplication/division runtime — le 6507 n'en a pas nativement ; tout passe par table précalculée ou décalage de bits
- Code auto-modifiant réservé aux kernels les plus tendus (affichage), toujours à éviter dans la logique de jeu (§7) où le code reste plus facile à relire à froid que le gain de cycles ne le justifie
- Post-pivot, cette discipline s'applique désormais **aussi à la logique de jeu** (§7), pas seulement au kernel d'affichage — le budget vblank/overscan n'est plus assez large pour se permettre de l'ignorer (§6)
- Le débogueur Stella sert à *vérifier* le comptage manuel, pas à s'y substituer — un kernel qui déborde silencieusement d'une ligne sur l'autre est un bug qu'on veut éviter d'avoir à diagnostiquer après coup

---

## 12. Sélection de jeux & architecture moteur mutualisé

### 12.1 Pourquoi ces trois jeux

Critère de sélection explicite : ruleset déjà entièrement spécifié ailleurs (aucune invention de design requise), manette 2600 compatible (4 directions + 1 bouton — élimine d'office tout ce qui demanderait tactile/gyroscope/micro), et pertinence pour démontrer nos techniques de rendu.

| Jeu | Ruleset | Pourquoi il sert le projet |
|---|---|---|
| **Casse-briques** (flagship) | Raquette 1 axe, balle rebondissante, grille de briques à détruire | Genre né sur Atari (Breakout, 1976) — boucle historique forte. Grille de briques = terrain idéal pour le hue-shift/FRC (chaque rangée un dégradé de teinte propre) |
| **Le Jumper** | Un seul axe de liberté (gauche/droite), auto-rebond vertical infini, aucun game over | Vitrine pour la génération procédurale légère côté 6507 (LFSR, §7) plutôt que pour la densité couleur pure |
| **Octopus** (Game & Watch) | Bras rotatifs à cycle régulier, fenêtres de passage à lire au timing | Résonance directe avec la discipline de timing à la ligne près que le playfield asynchrone impose déjà (§4.2) |

### 12.2 Ce qui est mutualisable, ce qui ne l'est pas

| Composant | Mutualisable ? | Raison |
|---|---|---|
| Driver playfield asynchrone (réécriture mi-ligne PF0/1/2) | ✅ Oui | Mécanique bas niveau générique (§4.2), indépendante du contenu affiché — remplace l'ancien driver bus stuffing |
| Pipeline de rastérisation offline (vecteur → table TIA) | ✅ Oui | Outil de contenu, pas de logique de jeu |
| Logique de jeu (physique, procédural — §7) | ⚠️ Partiellement | Chaque jeu tourne son propre `logic_*.asm` sur 6507 (plus de runtime commun côté ARM, §7) ; ce qui reste mutualisable, ce sont des **routines** isolées (un LFSR générique, un helper de lookup table), pas un runtime partagé |
| Lecture input (joystick + bouton, anti-rebond) | ✅ Oui | Coût trivial à partager |
| Scaffolding vblank/overscan | ✅ Oui | Boilerplate commun à tout jeu 2600 |
| Conventions mémoire (page zéro, format de table) | ✅ Oui | Cohérence d'équipe, zéro coût runtime |
| **Kernel d'affichage** (boucle scanline par scanline) | ❌ Non — bespoke par jeu | Chaque jeu a une disposition d'objets radicalement différente : grille pleine largeur statique (Casse-briques) vs défilement vertical continu (Jumper) vs objets à positions fixes qui s'allument/s'éteignent (Octopus). Une abstraction générique ajouterait de l'indirection dans une boucle qui doit déjà tenir en 73 cycles/ligne — ça sacrifierait exactement la densité qu'on cherche à obtenir |

**Principe d'arbitrage, revu post-pivot :** tout ce qui est hors du chemin critique d'affichage (outils offline, scaffolding, routines de logique isolées) se mutualise sans réserve. Tout ce qui touche à la boucle WSYNC-critique reste cousu main, jeu par jeu — et depuis le pivot, la logique de jeu elle-même (§7) doit être comptée en cycles comme le reste, donc elle aussi bespoke par jeu plutôt qu'un runtime générique.

### 12.3 Cible visuelle : correction de référence

La comparaison initiale visait la "Game & Watch Collection" Nintendo DS (2006) — vérification faite, ce titre reproduit fidèlement le LCD monochrome d'origine (y compris l'effet de rémanence), donc ce n'est pas notre cible pour les dégradés de couleur.

La bonne référence est la série **Game & Watch Gallery** (Game Boy/GBC), qui proposait un "Mode Moderne" avec nouveaux graphismes couleur — c'est ce mode-là qui correspond à l'ambition visuelle, à dépasser avec hue-shift + FRC plutôt que la palette 4 teintes de la Game Boy.

**Garde-fou explicite pour Octopus :** le Mode Moderne de Game & Watch Gallery était souvent perçu comme moins bon que l'original malgré (ou à cause de) l'enrichissement visuel — preuve que pour un jeu de timing pur, la lisibilité du signal (la fenêtre de passage, le rythme) prime sur la richesse graphique. Sur ce jeu spécifiquement, la densité couleur ne doit jamais se faire au détriment de la clarté du timing — c'est un critère de validation du Proto 6, pas une option esthétique.

### 12.4 Roadmap & scope

- **Casse-briques** : vertical slice complète et jouable (Proto 4) — c'est le jeu qui reçoit le plus d'investissement
- **Le Jumper / Octopus** : vertical slices volontairement minces (Proto 5/6, section 10) — objectif de validation du socle mutualisé, pas de jeu fini. Pas de système de score complet, pas de progression, pas de contenu au-delà d'un seul cycle de gameplay
- Aucun engagement à développer les trois jusqu'au bout dans ce cahier des charges — la décision de pousser Jumper et/ou Octopus au-delà de la vertical slice se prend après retour d'expérience sur Casse-briques

### 12.5 Budget mémoire/ROM à anticiper

- Post-pivot, plus de 32 Ko de flash ARM en filet de sécurité — le budget réel est celui d'une cartouche bankswitchée F6 (16 Ko, 4 banques de 4 Ko) par défaut, ou F8 (8 Ko, 2 banques) si un jeu y tient (§2). À vérifier concrètement dès que les tables d'assets (rastérisation offline, §4.1) et les layouts précalculés (§7) existent — ROM plus contrainte qu'avec l'ARM, donc budget à suivre activement, pas à considérer acquis
- Réserver dès le Proto 4 une carte d'allocation de la page zéro (quelles adresses sont réservées à l'état de jeu, au RNG, aux pointeurs actifs) pour éviter les collisions entre les différents kernels de jeu et entre devs qui toucheront le code en parallèle

### 12.6 Décision : paddle ou manette pour Casse-briques

Divergence identifiée par la revue externe : le Breakout historique utilise un paddle (potentiomètre, lecture analogique via `INPT0-3`, section 3.1), alors que le critère de sélection posé en 12.1 impose une manette digitale 4 directions + 1 bouton, commune aux trois jeux.

**Décision retenue : manette digitale, pas paddle.** Raison : le paddle casserait la mutualisation de l'input posée en 12.2 (`✅ Oui` pour "lecture input") — Le Jumper et Octopus n'ont aucun usage d'un paddle, et faire cohabiter deux drivers d'input dans `/engine/input.asm` réintroduirait exactement le genre d'indirection qu'on refuse pour le kernel d'affichage. On sacrifie l'authenticité historique du contrôle pour la cohérence d'architecture — arbitrage assumé, pas un oubli. **Statut post-pivot :** la clause de reconfirmation portait sur un résultat défavorable du Spike 0 point 1 (9.2), qui n'a plus lieu d'être puisque ce spike est résolu par pivot. Décision considérée stable ; à revalider en Proto 4 sur sensation de jeu réelle si besoin, plus sur une contrainte technique désormais éteinte.

### 12.7 Budget de cycles — exemple chiffré illustratif (non validé matériel), recalculé post-pivot

Cette section changeait déjà de nature avec le pivot : sans bus stuffing, une écriture qui doit varier (une brique différente d'une ligne à l'autre) redevient une paire `LDA table,Y` + `STA` classique plutôt qu'un simple `STA` (§2). **À prendre comme cadre de calcul pour le Proto 1, pas comme chiffre confirmé** — seul un test réel (Stella cycle-exact ou matériel, via `tools/cycle_linter.py` pour le comptage mécanique) validera ces ordres de grandeur.

| Poste (par scanline dans la zone de jeu) | Coût estimé | Cumul sur 73 cycles utiles |
|---|---|---|
| `STA WSYNC` (resynchronisation) | 3 cycles | 3 |
| Réécriture asynchrone d'un registre de playfield — **deux styles de kernel possibles, coût différent** : (a) déroulé/auto-modifiant, `LDA #valeur` (2 cycles) + `STA PF0/1/2` (3 cycles), valeurs figées à la compilation par le rasterizer offline (§4.1), autorisé par §11.3 pour les kernels d'affichage ; (b) en boucle, `LDA table,Y` (4 cycles) + `STA` (3 cycles), plus flexible pour du contenu qui varie réellement d'une frame à l'autre | ~5 cycles/registre (a) ou ~7 cycles/registre (b) | selon le style de kernel retenu et le nombre de registres réécrits pour casser la symétrie sur cette ligne (typiquement 1-3, voir §4.2) — le style (a) convient à la grille de briques (statique entre deux ruptures de brique), le style (b) serait nécessaire pour un contenu réellement dynamique ligne à ligne |
| Mise à jour position balle (lecture + `STA HMP0`/`STA RESP0` si sprite natif) | ~6-9 cycles | à ajouter une seule fois par frame concernée, pas par ligne |
| Mise à jour position raquette (lecture input + `STA HMP1`) | ~6-9 cycles | idem, hors chemin critique de la ligne balle |
| Marge restante pour hue-shift/FRC sur la ligne | *(73 − reste)* | à mesurer en Proto 1 |

**Différence structurante avec le draft v7 :** l'ancienne ligne "marge restante" posait une question binaire (le Spike 0 point 1 passe ou casse). Cette question n'existe plus — il n'y a plus deux mécanismes à faire coexister sur la même ligne (§4.2). La question qui reste est plus ordinaire : quel style de kernel choisir (a ou b ci-dessus) et combien de registres de playfield peut-on se permettre de réécrire par ligne avant d'empiéter sur la marge FRC/hue-shift — un calibrage de densité normal à trancher en Proto 1, pas un risque d'architecture.

### 12.8 Pistes d'extension post-vertical-slice (ambition, non bloquant)

Cinq axes identifiés comme sous-exploités dans le scope actuel — à ne considérer qu'après une vertical slice Casse-briques fonctionnelle (Proto 4), jamais avant :

- **Multiplexage de sprites** (technique homebrew connue, popularisée par Pitfall II) : rejouer les registres `GRP0`/`GRP1` à mi-ligne pour afficher plus de deux objets indépendants que les "2 players natifs" ne le permettent — pourrait donner plus de briques traitées en sprite plutôt que tout faire porter au playfield
- **HMOVE fine positioning** (résolution demi-color-clock) : pour un mouvement de balle plus fluide que le pas natif — trick avancé, distinct du HMOVE basique déjà prévu en 12.7
- **FRC par dithering temporel non-binaire** (matrice de Bayer étalée sur plusieurs frames plutôt qu'alternance simple 50/50) : pourrait sortir plus de teintes intermédiaires perçues que l'augmentation du nombre de paliers actuel (qui coûte du scintillement, section 9.1) — alternative à explorer avant de pousser les paliers FRC au-delà de 3-4
- **Mode canon ("Offrande Musicale")** : mode secret/bonus où les 2 canaux deviennent des voix égales en imitation stricte (canal 2 imite canal 1 avec un délai fixe) plutôt que la hiérarchie socle/voix réactive de 4.5.2 — clin d'œil à L'Offrande Musicale de Bach (le *Canon per Tonos*, qui module d'un ton à chaque boucle). Incompatible avec les transformations réactives de 4.5.4 pendant qu'il est actif : un second moteur de lecture à part entière, pas une table de plus — clairement hors scope Proto 4
- **Second thème "mode difficile"** : les Inventions à deux voix de Bach (BWV 772-786) ont été identifiées comme alternative à la fugue écartée en 4.5.3 — **repositionnées en 4.5.7 comme musique de menu**, l'écran qui offre justement les bonnes contraintes pour les exploiter sans compromis. Reste ouvert : une deuxième piste in-game (mode difficile) au-delà des pistes A/B si le besoin se confirme après la vertical slice

Ces cinq pistes ne remettent pas en cause l'architecture retenue en 12.2-12.4 — elles en repoussent l'ambition, une fois le socle validé.

### 12.9 Écrans, transitions & juice

#### 12.9.1 Écrans prévus

| Écran | Contenu | Traitement |
|---|---|---|
| Titre/Sélection | Choix de piste A/B (`SWCHB`, 4.5.3), musique de menu (4.5.7) | Scène figée → budget FRC/hue-shift maximal (principe statique/dynamique, section 6) |
| Jeu | Écran principal | Contraintes du principe statique/dynamique — playfield riche, objets mobiles sobres |
| Transition de niveau | Si plusieurs layouts de briques | Fondu simple, voir 12.9.2 |
| Game Over | Cadence musicale (4.5.4) | Scène figée → même traitement riche que le Titre |

#### 12.9.2 Transitions

Fondu par balayage de `COLUBK` sur une table de valeurs précalculée — même logique offline que le pipeline vecteur→table du 4.1, coût négligeable, pas de calcul runtime.

#### 12.9.3 Juice — principe et déclinaison matérielle

Principe (popularisé par la conférence "Juice It or Lose It", 2012) : un seul impact déclenche plusieurs réponses synchronisées, jamais un événement isolé — déjà appliqué implicitement à la musique en 4.5.1. Généralisation naturelle : le même strobe de collision (4.4) déclenche en parallèle une transformation son **et** une transformation visuelle.

| Technique | Mécanisme matériel | Scope |
|---|---|---|
| Hit-stop | Geler l'avancement du jeu 2-4 frames sur impact fort, continuer d'afficher | Proto 4 — coût nul |
| Flash couleur | `COLUBK`/`COLUPF` sur teinte vive pendant 1 frame | Proto 4 — infra couleur déjà en place |
| Squash de la balle | `NUSIZ0` temporaire sur rebond | Proto 4 |
| Tremblement d'écran | Décalage HMOVE de quelques color-clocks sur tous les objets, 2-3 frames | Extension — dépend du levier HMOVE fine positioning (12.8), non encore validé |
| Débris de brique | Emprunt temporaire de `missile1`/`player1` (libres tant qu'aucune autre mécanique ne les utilise), 2-3 frames | Extension |

#### 12.9.4 Point désormais spécifié

Le "pop" visuel du score à l'incrément dépend d'un kernel d'affichage du score — **spécifié en 4.6** (technique du 48-pixel kernel, scope recommandé 4 chiffres pour le Proto 4). Le "pop" lui-même (réaction visuelle à l'incrément, ex. flash bref du chiffre modifié) reste un raffinement de juice à ajouter une fois le kernel de base fonctionnel.

#### 12.9.5 Note de posture : pipeline de capture et présentation

Le "wow" perçu dépend autant de la présentation que de la technique — la preuve qui convainc est la capture sur vrai matériel (CRT réel), pas l'émulateur, et le son mérite d'être mis en avant à égalité avec l'image dans toute démo/trailer (un thème de Mozart ou Biber reconnaissable sortant d'une puce à 2 canaux surprend plus universellement qu'un dégradé de couleur, dont peu de gens ont l'intuition des limites réelles). À traiter comme un livrable de fin de projet, pas comme un à-côté — pas de détail technique supplémentaire à ce stade.

### 12.10 Direction artistique — charte graphique

Rôle de cette section : fixer un vocabulaire visuel assez précis pour générer des prompts cohérents (sourcing IA, 4.7), pas un moodboard vague. Chaque choix ci-dessous est fait pour survivre la quantification vers la palette TIA, pas pour être beau en pleine résolution.

#### 12.10.1 Concept directeur : le mur qui cache une évasion

L'accroche retenue (déjà évoquée en discussion, formalisée ici) : la grille de briques n'est pas un obstacle abstrait, c'est **un mur de prison** — chaque brique cassée révèle un fragment de l'image peinte en dessous (aura, ciel, horizon), jusqu'à ce que le mur entier tombe et révèle la scène complète. Ce n'est pas une idée gratuite : le Breakout de 1976 avait déjà, dans l'art du cabinet d'arcade d'origine, un thème d'évasion de prison — un détenu qui défonce le mur de sa cellule à coups de masse pour s'échapper. On ne invente pas un thème, on ramène au premier plan celui que le jeu portait déjà et que presque personne ne connaît.

Conséquences concrètes :
- Le layout des briques par niveau doit correspondre à une **zone masquée d'une image source unique**, pas à un pattern arbitraire — le script de rastérisation (4.1) échantillonne l'image "évasion" derrière la position de chaque brique
- La raquette est un **maillet/barre**, pas une plaque générique — clin d'œil direct à l'imagerie du cabinet d'origine
- La balle est une **pierre/gravat**, pas un point neutre

#### 12.10.2 Deux ambiances, calées sur les pistes A/B (4.5.3)

Le choix musical A/B devient aussi un choix visuel — cohérence transversale plutôt que deux systèmes indépendants qui coïncident par hasard.

| | Thème A (jour) | Thème B (nuit) |
|---|---|---|
| Musique | Mozart K.265 — clair, enjoué | Biber, Passacaille — sombre, tendu |
| Scène révélée | Sortie vers un ciel/horizon chaud, évasion "réussie" | Évasion nocturne, clair de lune, plus dramatique |
| Teintes dominantes | Ocre, grès chaud (mur), bleu ciel réservé à la zone révélée, un accent chaud rare (rouge/rose) | Indigo/bleu-violet (mur), gris-bleu, un seul accent chaud rare (ambre — torche/lune) |

#### 12.10.3 Discipline de palette

Rappel de 5.1 : silhouette avant détail, hue-shift plutôt que simple luminance. Ajout pour le sourcing IA : la palette TIA s'organise en ~16 teintes de base × ~8 paliers de luminance chacune — la discipline de curation consiste à **choisir 3-4 teintes de base par thème (A ou B), jamais plus**, et à travailler les paliers de luminance à l'intérieur de ce choix restreint pour le dégradé/hue-shift. Une image qui pioche dans 8 teintes de base différentes aura l'air "chargée" quelle que soit la qualité de l'exécution — la retenue sur le nombre de teintes de base est ce qui distingue "beau" de "chargé", pas la richesse des paliers à l'intérieur.

#### 12.10.4 Références utiles

- **Repère de faisabilité réaliste, désormais notre propre classe de technique** : les titres 2600 récents de Champ Games (*Zoo Keeper*, *Mappy*, *Super Cobra Arcade*, *Turbo Arcade*) n'utilisent pas de bus stuffing — dans les drafts précédents, c'était "le plancher que le bus stuffing devait dépasser". Post-pivot, on est dans la même famille de contraintes qu'eux (100% 6507/TIA natif) pour l'écriture brute. Nuance à garder en tête (§4.2) : l'ambition *par rangée* posée dès §12.1 n'a jamais dépendu du bus stuffing, donc elle reste pleinement de notre ressort — ce qui rejoint leur classe de technique, c'est l'embellissement per-brique du draft v7, pas le projet entier. La différenciation vient de la combinaison playfield asynchrone + FRC/hue-shift/dithering cumulés (§4.2, §5.2) et de la direction artistique/musicale (ci-dessous, §4.5), un terrain où ces titres n'ont pas particulièrement investi
- **Style graphique recommandé pour la génération IA : affiche WPA / gravure sur bois (linocut)** — silhouettes fortes, aplats de couleur francs, palette volontairement restreinte, pas de dégradé fin ni de texture délicate. C'est le style qui survit le mieux à une réduction brutale vers 3-4 teintes, bien mieux qu'un rendu photoréaliste ou peint en glacis
- **Référence narrative** : l'art du cabinet d'arcade Breakout original (1976), thème carcéral — à consulter avant de rédiger les prompts, pas à citer de mémoire

#### 12.10.5 Gabarit de prompt (pour la génération IA, 4.7)

Structure recommandée, à adapter par asset : **[sujet] + "bold flat color shapes, strong silhouette, WPA poster illustration, linocut style" + "limited palette of [3-4 teintes nommées du thème A ou B]" + "no fine gradients, no fine linework, thick graphic outlines, high contrast"**.

Exemple pour la scène "évasion" du Thème A : *"A prison wall breaking open to reveal a warm sunrise horizon beyond, bold flat color shapes, strong silhouette, WPA poster illustration, linocut style, limited palette of ochre, warm grey and sky blue, no fine gradients, no fine linework, thick graphic outlines, high contrast."*

**Rappel de discipline (4.7)** : ne jamais juger le résultat en pleine résolution/pleine couleur — toujours après passage dans le script de quantification, sur Stella ou CRT.

---

## 13. Références consultées

- `PIVOT_INSTRUCTIONS.md` (racine du repo) et `backlog.md` Lane 0 — décision et justification complète du pivot architectural du 2026-08-31 (abandon ARM/DPC+/CDFJ+/bus stuffing), y compris les spikes 0.1/0.1b/0.2/0.2b qui ont contribué à l'éclairer
- Forum AtariAge — fil "Bus Stuffing Demos" (SpiceWare et al.), incluant démo RPG et démo 128 Chronocolour — *référence historique, technique abandonnée au pivot (§2), conservée pour la limite haute du FRC (§4.3)*
- Big Mess o' Wires — articles sur l'accélération matérielle Atari 2600 (bus stuffing, ACE, Harmony/CDFJ) — *référence historique, mécanisme abandonné (§2), utile pour comprendre pourquoi le bus stuffing n'était pas séparable de l'ARM*
- Wikipedia — spécifications matérielles Atari 2600 (résolution, TIA, 6507)
- Documentation communautaire "Atari 2600 Programming for Newbies" (timing TIA/6502)
- GitHub chunkypixel/atari-dev-studio, 8bitworkshop.com — toolchain de développement moderne
- Nintendo Life, MobyGames, Super Mario Wiki, Retro Replay — vérification factuelle Game & Watch Collection (DS) vs Game & Watch Gallery (GB/GBC)
- Spécifications matérielles TIA (registres collision CX*, audio AUDC/AUDF/AUDV, paddle INPT0-3) — classic-games.com/atari2600, problemkaputt.de (Nocash specs), Grokipedia
- Big Mess o' Wires — détail technique du mécanisme de bus stuffing ($FF + pull-down data bus) — *référence historique, voir note ci-dessus*
- Spécifications audio TIA (AUDC/AUDF/AUDV, 2 voix) — qotile.net Music and Sound Programming Guide, midibox.org, TIA Technical Manual (archive.org)
- Comparaison matérielle Game Boy (4 canaux + enveloppes matérielles) — Pan Docs (gbdev.io), GbdevWiki — pour calibrer honnêtement l'ambition "niveau Link's Awakening"
- Repères historiques des œuvres du domaine public retenues : *12 Variations sur "Ah vous dirai-je, Maman" K.265* (Mozart, 1785), Passacaille en sol mineur de la Sonate du Rosaire (Biber, c. 1676), Inventions à 2 voix BWV 772-786 (Bach)
- "Juice It or Lose It" (Martin Jonasson & Petri Purho, 2012) — principe de référence pour la section 12.9 (réponse synchronisée multi-canal à un impact unique)
- Technique du "48-pixel kernel"/6-digit score display (NUSIZ, VDEL) — forums AtariAge, masswerk.at (RC2018 Refraction writeup), bumbershootsoft.wordpress.com, Nocash 2k6 specs
- *Making Games for the Atari 2600* (Steven Hugg) — chapitre "Asynchronous Playfields: Bricks", référence directe pour la représentation des briques (4.2.1)
- Wikipedia, StrategyWiki, Fandom — thème carcéral de l'art du cabinet d'arcade Breakout original (1976), base de la direction artistique (12.10.1)

---

*Document à faire relire par le lead dev avant lancement du Proto 1. Toute divergence entre les chiffres ci-dessus et un comportement observé en émulateur/matériel réel doit être remontée pour mise à jour de ce cahier des charges.*
