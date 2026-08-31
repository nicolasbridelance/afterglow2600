# Cahier des charges technique
## Atari 2600 poussée au maximum matériel — moteur mutualisé, jeux à scope contenu
**Statut :** Draft v7 — pivot validé, revue technique externe intégrée, moteur musical adaptatif spécifié, écrans/transitions/juice ajoutés, kernel de score spécifié, représentation des briques tranchée, direction artistique posée, Spike 0 requis avant Proto 1
**Destinataire :** Lead dev / équipe technique

---

## 1. Contexte & vision

Objectif : produire un ou plusieurs jeux Atari 2600 exploitant des techniques modernes (jamais accessibles aux développeurs des années 80) pour obtenir une densité visuelle jugée impossible à l'époque sur ce matériel — sans aucune extension qui changerait le CPU principal ou l'écran cible (TV NTSC standard).

**Pivot de scope (v1 → v2) :** le concept initial (un écran de combat JRPG unique, portrait de boss figé) a été remplacé par une approche délibérément plus "bordée" : des classiques arcade au ruleset minimal et déjà éprouvé (Casse-briques en priorité, Le Jumper et Octopus/Game & Watch en validation légère), choisis précisément parce qu'ils n'ont aucune inconnue de design à défricher. Toute l'énergie de l'équipe va sur l'optimisation et le rendu, pas sur l'invention de règles. Casse-briques a en plus une résonance particulière : c'est un genre né sur le matériel Atari d'origine (Breakout, 1976) — le reprendre avec nos techniques, c'est la maison qui pousse son propre jeu là où il n'avait jamais pu aller.

**Future-proofing sans scope creep :** le moteur est pensé dès le départ pour supporter plusieurs jeux (voir section 12), mais chaque jeu au-delà du premier est traité comme une **vertical slice volontairement mince** (un niveau, pas un jeu complet) — l'objectif est de valider que le socle partagé tient sur des genres différents, pas de livrer trois jeux finis.

**Référence explicite non visée :** aucun portage de jeu existant. Objectif = même densité visuelle perçue que nos techniques permettent, pas fidélité à un titre précis.

---

## 2. Plateforme cible

| Élément | Choix | Justification |
|---|---|---|
| Console | Atari 2600 NTSC | Cible historique, raster 262 lignes/60 Hz |
| Cartouche | Harmony/Melody (ou UnoCart 2600) | Seules cartouches supportant bus stuffing + ACE en pratique aujourd'hui |
| Driver bas niveau | Bus Stuffing (pas DPC+/CDFJ seul) | Écriture TIA en 3 cycles vs ~5-6 en 6507 pur — c'est le levier principal de densité graphique |
| Coprocesseur | ARM7TDMI-S LPC2103 @ 70 MHz, 32 Ko flash, 8 Ko RAM | Logique de jeu, génération procédurale, rastérisation runtime |
| Affichage cible principal | **CRT réel** | Les techniques d'entrelacement/FRC ne sont validées de façon fiable que sur tube cathodique |
| Affichage secondaire (dégradé) | Stella (émulateur) / LCD | Support partiel du bus stuffing selon version ; artefacts de synchro documentés sur écrans plats modernes |

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
Table statique en ROM (contenu figé) ─── OU ─── recalcul par l'ARM
                                              (contenu procédural, entre deux tours)
        │
        ▼
Streaming vers TIA via bus stuffing (affichage temps réel, 3 cycles/écriture)
```

### 4.2 Deux couches superposées

| Couche | Résolution effective | Usage | Technique |
|---|---|---|---|
| Playfield | 160×192 (résolution "douce") | Masses, dégradés larges, aura, drapé | Recalcul par ligne, pas d'entrelacement nécessaire |
| Sprites bus-stuffés | 96×192 (12 tuiles × 8px, entrelacé pair/impair) | Détails fins : visage, armes, symboles | Bus stuffing + entrelacement, précédent validé (démo RPG SpiceWare/AtariAge) |

#### 4.2.1 Décision : représentation des briques (correction d'une ambiguïté non résolue)

Le chiffre "playfield natif 40×192" (section 3) cache un piège : nativement, ce sont 20 bits reflétés ou dupliqués sur la moitié droite de l'écran, pas 40 valeurs indépendantes — obtenir une brique asymétrique demande une technique dédiée. Un ouvrage de référence directement pertinent pour Casse-briques existe et n'était pas encore cité : *Making Games for the Atari 2600* (Steven Hugg) consacre un chapitre entier ("Asynchronous Playfields: Bricks") à exactement ce problème, en construisant un jeu façon Breakout comme cas d'étude.

**Décision retenue, à deux paliers :**

| Palier | Technique | Ce qu'elle donne | Dépendance |
|---|---|---|---|
| **Principal** | Briques portées par la couche sprites bus-stuffées (4.2, déjà établie) | Forme *et* couleur riche par brique (hue-shift/FRC complet, cf. 12.1) | Dépend du Spike 0 (9.2, point 1) — la balle/raquette natives partagent les mêmes lignes que les briques bus-stuffées |
| **Repli** | Playfield asynchrone (réécriture mi-ligne de `PF0/1/2`, technique du chapitre 21 de Hugg) | Forme asymétrique correcte, native, aucune dépendance au bus stuffing | Couleur limitée à 1-2 teintes par ligne de playfield (pas de richesse par brique individuelle) |

Autrement dit : **le risque n°1 du Spike 0 s'applique pleinement à la grille de briques**, pas seulement aux sprites — la revue externe avait raison de le signaler comme flou, et la réponse est qu'il n'y a pas de contournement gratuit. Si le Spike 0 échoue, le repli existe (le jeu reste jouable, asymétrique, mais renonce à la richesse chromatique par brique qui est pourtant le cœur de l'ambition du projet) — mais c'est un vrai renoncement esthétique à anticiper, pas une simple bascule technique transparente.

### 4.3 Précédents techniques à étudier avant implémentation

- **Démo "RPG" (SpiceWare, forum AtariAge)** : preuve de concept validée en matériel réel — 12 couleurs/scanline sur un affichage 96×192 en tuiles, via bus stuffing + entrelacement pair/impair. Base de départ pour notre couche sprite.
- **Démo "128 Chronocolour" (même équipe)** : tentative d'aller jusqu'à 128 teintes par pixel via alternance de trames — jugée impraticable en usage réel à cause du scintillement. À ne pas reproduire telle quelle ; sert de garde-fou sur la limite haute du FRC.
- ***Making Games for the Atari 2600* (Steven Hugg), chapitre "Asynchronous Playfields: Bricks"** : référence directe pour le palier de repli de 4.2.1, construite précisément sur un jeu façon Breakout.

### 4.4 Détection de collision — approche recommandée

**Décision : s'appuyer sur les registres matériels (section 3.1), pas sur du calcul logiciel ARM.** Pour Casse-briques, deux collisions à détecter par frame : balle-brique et balle-raquette. Si la balle est un missile TIA et la raquette un player, `CXM0P` donne directement balle-vs-raquette. Si les briques sont portées par le playfield, `CXM0FB` donne balle-vs-brique(s) en un seul read. Ça évite tout aller-retour ARM pour une opération que le matériel fait gratuitement — les latches s'accumulent pendant l'affichage et se lisent en une passe pendant le vblank suivant, avant le `CXCLR`.

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
- **Score volontairement découplé de l'ARM, pour éviter une dépendance inutile au Spike 2.** La détection de collision est matérielle, pas ARM (décision de 4.4) — le score doit rester un compteur BCD strictement **côté 6507**, incrémenté directement à la lecture des latches de collision en vblank, sans jamais transiter par l'ARM. Une revue externe avait signalé un risque de dépendance au coût inconnu de l'aller-retour ACE (Spike 2, section 9.2) en supposant le score lié à la physique ARM (section 7) — ce risque est réel *si* on implémente naïvement, mais évitable par construction : le score n'a besoin d'aucune donnée calculée côté ARM, seulement du fait qu'une collision a eu lieu, déjà disponible côté 6507.
- **Budget de cycles distinct** : ces lignes n'ont aucun rapport avec le kernel de briques (bus stuffing) — c'est un troisième budget à documenter séparément, pas une extension du premier.

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

### 5.3 Mécanisme de bascule FRC — non détaillé, à spiker (voir 9.2)

Point ouvert signalé par la revue externe du document : le FRC suppose de basculer entre 2 (ou N) tables de teintes d'une frame réelle à l'autre. Piste privilégiée : la bascule se fait **une fois par frame, en vblank**, via un simple changement de pointeur de table (l'index de table active passe de 0 à 1 dans une variable page zéro) — le kernel d'affichage lit toujours "la table active" sans savoir laquelle c'est, donc la boucle scanline elle-même ne coûte rien de plus. Le seul coût ajouté est dans le vblank, où le budget est large (section 6). **Cette piste n'est pas encore vérifiée cycle par cycle** — c'est l'objet du spike FRC (section 9.2, point 4) avant Proto 2.

---

## 6. Cadence de mise à jour — principe statique/dynamique

**Généralisation suite au pivot v2 :** la règle n'est plus "tour par tour = image figée" (spécifique au concept JRPG initial), mais un principe plus large qui s'applique à tous nos jeux, y compris ceux en temps réel continu :

> **Les techniques coûteuses (FRC, entrelacement, hue-shift poussé) ne s'appliquent qu'aux éléments visuels qui ne changent pas d'une frame à l'autre. Les éléments qui bougent en continu utilisent un rendu simple et sûr, sans entrelacement.**

Application par jeu :
- **Casse-briques** : la grille de briques est statique (elle ne change que quand une brique disparaît) → budget FRC/hue-shift complet. La balle et la raquette bougent chaque frame → rendu sprite natif standard, aucune technique d'entrelacement dessus (sous peine de réintroduire exactement le scintillement qu'on cherche à éviter sur un objet qui bouge).
- **Le Jumper** : les plateformes individuelles ne changent pas de complexité visuelle une fois positionnées, mais le défilement vertical les fait techniquement "bouger" à l'écran → nécessite une analyse dédiée en Proto Jumper, le principe ne s'applique pas tel quel.
- **Octopus/Game & Watch** : le décor de fond est statique, les segments qui s'allument/s'éteignent sont ponctuels → bon candidat pour le traitement riche sur le fond, simple sur les segments actifs.

Budget de calcul disponible pendant les phases où l'affichage reste identique frame après frame (menu, attente, scène figée) : de l'ordre de plusieurs centaines de milliers de cycles 6507 (zones vblank/overscan cumulées) + plusieurs dizaines de millions de cycles ARM par seconde d'attente — largement suffisant pour la logique de jeu, sans optimisation extrême nécessaire côté ARM. Ce budget reste disponible même dans un jeu temps réel, pendant les frames où rien de nouveau n'a besoin d'être recalculé.

---

## 7. Logique de jeu (côté ARM / ACE)

Usage par jeu candidat (voir section 12 pour le détail des règles) :

- **Casse-briques** : physique de rebond de la balle (angles, collisions briques/raquette), génération procédurale de layouts de niveaux
- **Le Jumper** : génération procédurale de la colonne de plateformes (types, espacement, seed déterministe)
- **Octopus/Game & Watch** : gestion du cycle de rotation des bras et des fenêtres de passage, difficulté progressive

Principe commun : tout calcul qui n'a pas besoin d'être resynchronisé à la ligne près part sur l'ARM plutôt que sur le 6507 — la marge de cycles y est telle que la généricité ne coûte quasiment rien (contrairement au kernel d'affichage, voir section 12.3).

Le contenu **figé** (arrière-plans, tables de sprites) doit être rastérisé une fois pour toutes au moment de la compilation de la ROM, pas recalculé à l'exécution — coût runtime nul pour ces éléments.

---

## 8. Outils & toolchain proposés

- Assembleur 6507 : DASM (ou cc2600 si l'équipe préfère un sous-ensemble C)
- Émulateur de développement/debug : Stella (version récente requise pour le support bus stuffing)
- Validation finale : matériel réel (cartouche Harmony/Melody) + CRT
- Pipeline offline de rastérisation vecteur → table TIA : à développer en interne (script Python probable, à partir d'assets vectoriels sources)

---

## 9. Risques identifiés

| Risque | Impact | Mitigation proposée |
|---|---|---|
| Scintillement inacceptable sur écrans modernes (LCD/OLED) | Démo injouable hors CRT | Mode de repli à densité réduite pour émulateur/écran plat |
| Timing bus stuffing extrêmement serré (fenêtres de quelques cycles) | Bugs difficiles à diagnostiquer, dev lent | S'appuyer sur driver existant de la communauté plutôt que ré-implémenter from scratch ; prévoir temps de mise au point important (le précédent RPG demo a demandé plusieurs itérations documentées) |
| Support Stella incomplet pour bus stuffing selon version | Dev/debug ralenti sans matériel réel | Prévoir accès matériel réel (Harmony cart) tôt dans le projet |
| Sur-promesse sur le nombre de teintes perçues | Attentes non tenues | Valider empiriquement sur prototype avant de communiquer un chiffre |

### 9.1 Leviers de réduction du scintillement (à arbitrer)

| Levier | Principe | Gain | Sacrifice | Décision |
|---|---|---|---|---|
| Entrelacement propre (vs scintillement naïf) | Chevauchement des bords de lignes entre trames paire/impaire | Détail vertical préservé, oscillation bien mieux masquée à l'œil | Timing driver plus complexe à coder (décalage demi-ligne) | **Retenu** |
| Réduction du nombre de lignes affichées (<262) | Fréquence de rafraîchissement effective augmentée (jusqu'à ~80 Hz testé) | Scintillement nettement amélioré | Signal hors standard NTSC : rejeté par la plupart des écrans modernes (image qui roule/se scinde), risque de compatibilité majeur | **Écarté** |
| Réduction des paliers FRC (3-4 → 2) | Cycle de mélange plus court, 30 Hz effectif | Scintillement perçu réduit | Palette perçue plus pauvre, moins de teintes intermédiaires | **Combiné avec les autres, à doser en Proto 3** |
| Masses solides plutôt que détail fin à haute fréquence spatiale | Le scintillement est quasi invisible sur grandes tuiles pleines, bien plus visible sur textures à petits points | Réduction perçue forte sans coût technique supplémentaire | Moins de texture fine, rendu plus "posterisé" | **Retenu** — cohérent avec la direction artistique silhouette-first (section 5.1) |

**Arbitrage retenu pour le Proto 2/3 :** combiner entrelacement propre + paliers FRC réduits + priorité aux masses solides. La réduction du nombre de lignes affichées est explicitement écartée en raison du risque de compatibilité avec les écrans modernes, documenté dans les précédents étudiés.

### 9.2 Spikes techniques obligatoires avant Proto 1 (bloquants, pas des détails d'implémentation)

Une revue externe du document a identifié des inconnues qui ne sont pas de la paperasse mais de la physique du timing — à lever *avant* de committer sur l'architecture, pas pendant. Sans ces réponses, le Proto 1 risque de démarrer sur des hypothèses fausses.

| # | Spike | Question à trancher | Pourquoi c'est bloquant |
|---|---|---|---|
| 1 | **Bus stuffing + sprite natif mobile, même ligne** | La démo RPG (référence section 4.3) prouve le bus stuffing sur écran statique. Casse-briques a besoin de bus stuffing (grille) **et** de sprites natifs mobiles (balle, raquette) **sur les mêmes scanlines**. Est-ce que `STA GRP0`/`STA HMOVE` pour positionner la balle casse la fenêtre de timing du bus stuffing sur cette ligne ? Aucun précédent documenté ne combine les deux. | **Le plus critique des cinq.** S'il échoue, toute l'architecture 4.2 (deux couches superposées) doit être repensée avant d'aller plus loin |
| 2 | **Coût réel d'un aller-retour ACE (6507 → ARM → 6507)** | La section 6 dit "budget largement suffisant" mais ne chiffre jamais le coût de l'aller-retour lui-même. **Ce chiffre n'est pas connu à ce stade** — aucune source consultée ne le documente avec précision. | Si le coût fixe est de l'ordre de 15-20 cycles, appeler l'ARM en plein kernel d'affichage (pas juste en vblank) devient inenvisageable — ça change le découpage logique/rendu |
| 3 | **Fidélité Stella sur la combinaison bus stuffing + sprite natif** | Le support "partiel" de Stella pour le bus stuffing seul est déjà noté (section 2). Rien ne dit s'il est fiable sur la combinaison du point 1 | Risque de développer et valider aveuglément sur émulateur, puis de tout casser à la première session sur cartouche réelle |
| 4 | **Mécanisme de bascule FRC** | Détaillé en 5.3 — piste identifiée (changement de pointeur en vblank) mais jamais vérifiée cycle par cycle | Un fragment de kernel isolé sur 8bitworkshop (section 11.1) doit mesurer ça avant Proto 2 |
| 5 | **Paddle vs manette** | Tranché en 12.6 — mais dépend du résultat du spike 1 si la balle finit par nécessiter un contrôle plus fin que le digital | Change le driver input et le feel du jeu, donc idéalement tranché avant que le pipeline d'input mutualisé (12.2) ne soit figé |

**Recommandation :** les spikes 1 et 2 sont ceux qui peuvent remettre en cause l'architecture retenue (pas juste des détails d'implémentation) — à faire trancher explicitement par le lead dev/CTO avant tout commit sur Proto 1. Les spikes 3-5 peuvent se paralléliser avec le début du Proto 1 sans le bloquer.

---

## 10. Jalons proposés

**Spike 0 — avant tout le reste :** lever les points 1 et 2 de la section 9.2 (bus stuffing + sprite natif combinés, coût réel d'un aller-retour ACE). Décision lead dev/CTO requise sur ces deux points avant de lancer Proto 1 — un résultat négatif sur le point 1 implique de revoir l'architecture 4.2.

**Socle partagé (avant tout jeu spécifique) :**
1. **Proto 1 — Preuve de rendu vecteur** : une forme simple (cercle + dégradé radial) rastérisée offline, affichée via bus stuffing, comparée visuellement à la technique "programmer art" d'origine
2. **Proto 2 — Scène statique complète** : deux couches (playfield + sprites), hue-shifting + dithering, FRC à 2 paliers
3. **Proto 3 — FRC poussé** : montée à 3-4 paliers, validation scintillement sur CRT réel

**Vertical slice flagship :**
4. **Proto 4 — Casse-briques jouable minimal** : raquette + balle + une grille de briques complète, physique de rebond côté ARM, application du principe statique/dynamique (section 6)

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
| Émulateur / debug | **Stella** (version récente, requise pour le support bus stuffing) | Débogueur intégré cycle-exact : breakpoints, pas-à-pas, inspection registres TIA/RIOT en direct |
| Validation finale | Matériel réel (Harmony/Melody) + CRT | Seule validation fiable pour l'entrelacement et le FRC (cf. section 9) |
| Contrôle de version | Git | Fichiers texte purs (.asm/.h), workflow standard |

### 11.2 Organisation des fichiers

Pas un monolithe : convention multi-fichiers assemblés en un seul `.bin` par DASM via `.include`.

```
/engine                      → mutualisé entre tous les jeux (voir 12.3)
    vcs.h                    → constantes registres TIA/RIOT (fixe, ne change jamais)
    macro.h                  → macros communes (init RAM, etc.)
    bus_stuffing_driver.asm  → écriture TIA 3 cycles, générique
    input.asm                → lecture joystick/bouton, anti-rebond
    vblank_scaffold.asm      → gestion timer, structure de boucle de frame
/games
    /breakout
        kernel_breakout.asm  → boucle d'affichage bas niveau spécifique (bus stuffing, WSYNC, FRC sur la grille de briques)
        logic_breakout.asm   → physique balle/raquette (côté ARM, ACE)
        data_breakout.asm    → layouts de niveaux
    /jumper
        kernel_jumper.asm    → défilement vertical, positionnement plateformes
        logic_jumper.asm     → génération procédurale (ARM)
    /octopus
        kernel_octopus.asm   → cycle des bras, fenêtres de passage
        logic_octopus.asm    → timing et difficulté (ARM)
/tools
    rasterizer.py            → pipeline offline vecteur → table TIA (hors ROM finale)
main.asm                     → point d'entrée, sélectionne le jeu à assembler
```

Principe directeur : **séparer le moteur (générique, mutualisé, stable) du contenu et du kernel d'affichage (spécifiques à chaque jeu, non partagés)** — détaillé en section 12.3. Le kernel d'affichage n'est PAS générique : c'est un choix assumé pour ne pas payer de coût d'indirection dans la boucle critique (voir 12.3 pour le détail de l'arbitrage).

### 11.3 Discipline d'optimisation (à appliquer dès le Proto 1)

- Annoter chaque instruction critique avec son coût cumulé en cycles (convention `; 3 cycles, position 38, doit finir @37-43`), comme observé dans les kernels bus-stuffing existants — c'est la seule façon fiable de vérifier qu'un kernel tient dans son budget avant de le tester
- Variables chaudes (compteurs de boucle, pointeurs de table, état de tour) en page zéro systématiquement — 1 cycle de moins par accès qu'en adressage absolu
- Tables indexées alignées sur 256 octets pour éviter la pénalité de franchissement de page (+1 cycle imprévisible)
- Aucune multiplication/division runtime — le 6507 n'en a pas nativement ; tout passe par table précalculée ou décalage de bits
- Code auto-modifiant réservé aux kernels les plus tendus (affichage), jamais à la logique de jeu côté ARM où la marge de cycles est large
- Le débogueur Stella sert à *vérifier* le comptage manuel, pas à s'y substituer — un kernel qui déborde silencieusement d'une ligne sur l'autre est un bug qu'on veut éviter d'avoir à diagnostiquer après coup

---

## 12. Sélection de jeux & architecture moteur mutualisé

### 12.1 Pourquoi ces trois jeux

Critère de sélection explicite : ruleset déjà entièrement spécifié ailleurs (aucune invention de design requise), manette 2600 compatible (4 directions + 1 bouton — élimine d'office tout ce qui demanderait tactile/gyroscope/micro), et pertinence pour démontrer nos techniques de rendu.

| Jeu | Ruleset | Pourquoi il sert le projet |
|---|---|---|
| **Casse-briques** (flagship) | Raquette 1 axe, balle rebondissante, grille de briques à détruire | Genre né sur Atari (Breakout, 1976) — boucle historique forte. Grille de briques = terrain idéal pour le hue-shift/FRC (chaque rangée un dégradé de teinte propre) |
| **Le Jumper** | Un seul axe de liberté (gauche/droite), auto-rebond vertical infini, aucun game over | Vitrine pour la génération procédurale côté ARM plutôt que pour la densité couleur pure |
| **Octopus** (Game & Watch) | Bras rotatifs à cycle régulier, fenêtres de passage à lire au timing | Résonance directe avec notre propre technique de bus stuffing (fenêtres de cycles précises) |

### 12.2 Ce qui est mutualisable, ce qui ne l'est pas

| Composant | Mutualisable ? | Raison |
|---|---|---|
| Driver bus stuffing (écriture TIA 3 cycles) | ✅ Oui | Mécanique bas niveau générique, indépendante de ce qui s'affiche |
| Pipeline de rastérisation offline (vecteur → table TIA) | ✅ Oui | Outil de contenu, pas de logique de jeu |
| Runtime ARM / ACE (logique, procédural) | ✅ Oui | Budget de cycles si large que la généricité n'y coûte quasiment rien |
| Lecture input (joystick + bouton, anti-rebond) | ✅ Oui | Coût trivial à partager |
| Scaffolding vblank/overscan | ✅ Oui | Boilerplate commun à tout jeu 2600 |
| Conventions mémoire (page zéro, format de table) | ✅ Oui | Cohérence d'équipe, zéro coût runtime |
| **Kernel d'affichage** (boucle scanline par scanline) | ❌ Non — bespoke par jeu | Chaque jeu a une disposition d'objets radicalement différente : grille pleine largeur statique (Casse-briques) vs défilement vertical continu (Jumper) vs objets à positions fixes qui s'allument/s'éteignent (Octopus). Une abstraction générique ajouterait de l'indirection dans une boucle qui doit déjà tenir en 73 cycles/ligne — ça sacrifierait exactement la densité qu'on cherche à obtenir |

**Principe d'arbitrage :** tout ce qui est hors du chemin critique d'affichage (ARM, outils offline, scaffolding) se mutualise sans réserve. Tout ce qui touche à la boucle WSYNC-critique reste cousu main, jeu par jeu.

### 12.3 Cible visuelle : correction de référence

La comparaison initiale visait la "Game & Watch Collection" Nintendo DS (2006) — vérification faite, ce titre reproduit fidèlement le LCD monochrome d'origine (y compris l'effet de rémanence), donc ce n'est pas notre cible pour les dégradés de couleur.

La bonne référence est la série **Game & Watch Gallery** (Game Boy/GBC), qui proposait un "Mode Moderne" avec nouveaux graphismes couleur — c'est ce mode-là qui correspond à l'ambition visuelle, à dépasser avec hue-shift + FRC plutôt que la palette 4 teintes de la Game Boy.

**Garde-fou explicite pour Octopus :** le Mode Moderne de Game & Watch Gallery était souvent perçu comme moins bon que l'original malgré (ou à cause de) l'enrichissement visuel — preuve que pour un jeu de timing pur, la lisibilité du signal (la fenêtre de passage, le rythme) prime sur la richesse graphique. Sur ce jeu spécifiquement, la densité couleur ne doit jamais se faire au détriment de la clarté du timing — c'est un critère de validation du Proto 6, pas une option esthétique.

### 12.4 Roadmap & scope

- **Casse-briques** : vertical slice complète et jouable (Proto 4) — c'est le jeu qui reçoit le plus d'investissement
- **Le Jumper / Octopus** : vertical slices volontairement minces (Proto 5/6, section 10) — objectif de validation du socle mutualisé, pas de jeu fini. Pas de système de score complet, pas de progression, pas de contenu au-delà d'un seul cycle de gameplay
- Aucun engagement à développer les trois jusqu'au bout dans ce cahier des charges — la décision de pousser Jumper et/ou Octopus au-delà de la vertical slice se prend après retour d'expérience sur Casse-briques

### 12.5 Budget mémoire/ROM à anticiper

- Banking déjà couvert par le choix Harmony/CDFJ (32 Ko flash côté ARM) — pas de contrainte de taille bloquante à court terme pour ces rulesets
- Réserver dès le Proto 4 une carte d'allocation de la page zéro (quelles adresses sont réservées à l'état de jeu, au RNG, aux pointeurs actifs) pour éviter les collisions entre les différents kernels de jeu et entre devs qui toucheront le code en parallèle

### 12.6 Décision : paddle ou manette pour Casse-briques

Divergence identifiée par la revue externe : le Breakout historique utilise un paddle (potentiomètre, lecture analogique via `INPT0-3`, section 3.1), alors que le critère de sélection posé en 12.1 impose une manette digitale 4 directions + 1 bouton, commune aux trois jeux.

**Décision retenue : manette digitale, pas paddle.** Raison : le paddle casserait la mutualisation de l'input posée en 12.2 (`✅ Oui` pour "lecture input") — Le Jumper et Octopus n'ont aucun usage d'un paddle, et faire cohabiter deux drivers d'input dans `/engine/input.asm` réintroduirait exactement le genre d'indirection qu'on refuse pour le kernel d'affichage. On sacrifie l'authenticité historique du contrôle pour la cohérence d'architecture — arbitrage assumé, pas un oubli. **À reconfirmer après le Spike 0** : si le point 1 (9.2) montre que la balle a besoin d'un contrôle plus fin que ce que permet le digital, cette décision devra être révisée.

### 12.7 Budget de cycles — exemple chiffré illustratif (non validé matériel)

Demandé par la revue externe : un exemple concret plutôt que des affirmations qualitatives ("largement suffisant"). **À prendre comme cadre de calcul pour le Spike 0, pas comme chiffre confirmé** — seul un test réel (Stella cycle-exact ou matériel) validera ces ordres de grandeur.

| Poste (par scanline dans la zone de jeu) | Coût estimé | Cumul sur 73 cycles utiles |
|---|---|---|
| `STA WSYNC` (resynchronisation) | 3 cycles | 3 |
| Écriture bus-stuffée d'une brique (1 registre couleur/forme) | 3 cycles | selon nombre de briques sur la ligne |
| Mise à jour position balle (lecture + `STA HMP0`/`STA RESP0` si sprite natif) | ~6-9 cycles | à ajouter une seule fois par frame concernée, pas par ligne |
| Mise à jour position raquette (lecture input + `STA HMP1`) | ~6-9 cycles | idem, hors chemin critique de la ligne balle |
| Marge restante pour hue-shift/FRC sur la ligne | *(73 − reste)* | à mesurer, c'est la vraie question du Spike 0 point 1 |

La ligne "marge restante" est l'inconnue centrale : si le coût conjoint bus-stuffing + sprite natif dépasse 73 cycles sur une ligne qui contient à la fois des briques ET la balle, il faut soit réduire la densité couleur sur ces lignes précises, soit garantir que balle et briques ne se chevauchent jamais sur la même ligne par construction du layout (contrainte de design plutôt que prouesse technique — option à garder sous le coude si le Spike 0 est défavorable).

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

- **Repère de faisabilité réaliste (sans bus stuffing)** : les titres 2600 récents de Champ Games (*Zoo Keeper*, *Mappy*, *Super Cobra Arcade*, *Turbo Arcade*) — c'est le plancher que nos techniques doivent dépasser, pas un objectif en soi
- **Style graphique recommandé pour la génération IA : affiche WPA / gravure sur bois (linocut)** — silhouettes fortes, aplats de couleur francs, palette volontairement restreinte, pas de dégradé fin ni de texture délicate. C'est le style qui survit le mieux à une réduction brutale vers 3-4 teintes, bien mieux qu'un rendu photoréaliste ou peint en glacis
- **Référence narrative** : l'art du cabinet d'arcade Breakout original (1976), thème carcéral — à consulter avant de rédiger les prompts, pas à citer de mémoire

#### 12.10.5 Gabarit de prompt (pour la génération IA, 4.7)

Structure recommandée, à adapter par asset : **[sujet] + "bold flat color shapes, strong silhouette, WPA poster illustration, linocut style" + "limited palette of [3-4 teintes nommées du thème A ou B]" + "no fine gradients, no fine linework, thick graphic outlines, high contrast"**.

Exemple pour la scène "évasion" du Thème A : *"A prison wall breaking open to reveal a warm sunrise horizon beyond, bold flat color shapes, strong silhouette, WPA poster illustration, linocut style, limited palette of ochre, warm grey and sky blue, no fine gradients, no fine linework, thick graphic outlines, high contrast."*

**Rappel de discipline (4.7)** : ne jamais juger le résultat en pleine résolution/pleine couleur — toujours après passage dans le script de quantification, sur Stella ou CRT.

---

## 13. Références consultées

- Forum AtariAge — fil "Bus Stuffing Demos" (SpiceWare et al.), incluant démo RPG et démo 128 Chronocolour
- Big Mess o' Wires — articles sur l'accélération matérielle Atari 2600 (bus stuffing, ACE, Harmony/CDFJ)
- Wikipedia — spécifications matérielles Atari 2600 (résolution, TIA, 6507)
- Documentation communautaire "Atari 2600 Programming for Newbies" (timing TIA/6502)
- GitHub chunkypixel/atari-dev-studio, 8bitworkshop.com — toolchain de développement moderne
- Nintendo Life, MobyGames, Super Mario Wiki, Retro Replay — vérification factuelle Game & Watch Collection (DS) vs Game & Watch Gallery (GB/GBC)
- Spécifications matérielles TIA (registres collision CX*, audio AUDC/AUDF/AUDV, paddle INPT0-3) — classic-games.com/atari2600, problemkaputt.de (Nocash specs), Grokipedia
- Big Mess o' Wires — détail technique du mécanisme de bus stuffing ($FF + pull-down data bus)
- Spécifications audio TIA (AUDC/AUDF/AUDV, 2 voix) — qotile.net Music and Sound Programming Guide, midibox.org, TIA Technical Manual (archive.org)
- Comparaison matérielle Game Boy (4 canaux + enveloppes matérielles) — Pan Docs (gbdev.io), GbdevWiki — pour calibrer honnêtement l'ambition "niveau Link's Awakening"
- Repères historiques des œuvres du domaine public retenues : *12 Variations sur "Ah vous dirai-je, Maman" K.265* (Mozart, 1785), Passacaille en sol mineur de la Sonate du Rosaire (Biber, c. 1676), Inventions à 2 voix BWV 772-786 (Bach)
- "Juice It or Lose It" (Martin Jonasson & Petri Purho, 2012) — principe de référence pour la section 12.9 (réponse synchronisée multi-canal à un impact unique)
- Technique du "48-pixel kernel"/6-digit score display (NUSIZ, VDEL) — forums AtariAge, masswerk.at (RC2018 Refraction writeup), bumbershootsoft.wordpress.com, Nocash 2k6 specs
- *Making Games for the Atari 2600* (Steven Hugg) — chapitre "Asynchronous Playfields: Bricks", référence directe pour la représentation des briques (4.2.1)
- Wikipedia, StrategyWiki, Fandom — thème carcéral de l'art du cabinet d'arcade Breakout original (1976), base de la direction artistique (12.10.1)

---

*Document à faire relire par le lead dev avant lancement du Proto 1. Toute divergence entre les chiffres ci-dessus et un comportement observé en émulateur/matériel réel doit être remontée pour mise à jour de ce cahier des charges.*
