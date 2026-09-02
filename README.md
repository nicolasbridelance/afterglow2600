# Afterglow 2600

**Pousser l'Atari 2600 au maximum de ses capacités matérielles — 100 % 6507/TIA natif, zéro coprocesseur.**

Un moteur mutualisé pour plusieurs jeux à scope contenu, construit avec des techniques modernes jamais accessibles aux développeurs des années 80 : pipeline de rastérisation offline, quantification d'assets en tables TIA, et discipline de comptage de cycles assistée par outil.

## Le projet

- **Flagship** : Casse-briques (Breakout, 1976 — le genre est né sur le matériel Atari d'origine)
- **Vertical slices de validation** : Le Jumper, Octopus (Game & Watch)
- **Cible** : cartouche bankswitchée pure (F8/F6), affichage NTSC, priorité CRT réel

L'accroche n'est pas "dépasser la puce" — c'est *ce qu'un développeur de 1982 aurait fait s'il avait eu le temps, les outils d'itération modernes et une bibliothèque de références culturelles instantanément accessible*.

> **Pivot architectural (2026-08-31)** : abandon de l'architecture ARM/DPC+/CDFJ+/bus-stuffing, retour à un rendu 100 % 6507/TIA natif. La densité graphique vient du playfield asynchrone, du hue-shift/FRC et d'un usage discipliné des objets matériels — pas d'une substitution matérielle. Détail et justification : [`PIVOT_INSTRUCTIONS.md`](PIVOT_INSTRUCTIONS.md).

## Stack technique

| Élément | Choix |
|---|---|
| CPU | MOS 6507 @ 1,19 MHz — 76 cycles/scanline, 262 lignes NTSC |
| Rendu | TIA natif, "racing the beam", playfield asynchrone |
| Assemblage | [DASM](https://dasm-assembler.github.io/) |
| Vérification | `tools/cycle_linter.py` (budget de cycles), Stella headless, pytest |
| Assets | Rastérisation offline → quantification → tables TIA en ROM |

## Structure du repo

```
├── cahier_des_charges.md   # Vision & architecture technique
├── backlog.md              # État d'avancement, portes de décision, méthodo
├── CONVENTIONS.md          # Conventions de code, commits, ADR
├── AGENTS.md / CLAUDE.md   # Instructions pour agents IA
├── PIVOT_INSTRUCTIONS.md   # Décision de pivot architectural
├── docs/adr/               # Architecture Decision Records
├── engine/                 # Références matérielles (vcs.h)
├── spikes/                 # Preuves de concept (0.1, 0.2, FRC…)
├── tools/                  # Outillage (cycle_linter.py…)
└── tests/                  # Tests pytest
```

## Démarrage rapide

```bash
# Assembler un spike
dasm main.asm -f3 -o<jeu>.bin -l<jeu>.lst

# Vérifier le budget de cycles
python3 tools/cycle_linter.py <jeu>.lst

# Tests rasterizer / logique
pytest tools/ tests/

# Vérification structurelle headless (boot sans crash)
xvfb-run -a stella -video software -audio.enabled 0 -logtoconsole 1 -holdreset <jeu>.bin
```

## État d'avancement

- ✅ **Spike 0** — bus-stuffing + sprite natif (résolu par pivot, archivé)
- ✅ **Spike FRC** — bascule de tables de teintes en vblank, vérifiée cycle par cycle
- ⏳ **Proto 1+** — preuve de rendu vecteur, scène statique complète, Casse-briques jouable

Détail complet des lanes, portes et décisions : [`backlog.md`](backlog.md).

## Contraintes non négociables

- Aucune multiplication/division runtime sur le 6507 — tables précalculées ou décalages de bits
- Le kernel d'affichage n'est jamais factorisé entre jeux — chaque jeu a sa propre disposition d'objets matériels
- Score et détection de collision restent côté 6507 (registres CX*), jamais transités par un coprocesseur

## Licence

À définir.
