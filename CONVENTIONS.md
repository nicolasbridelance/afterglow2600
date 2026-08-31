# CONVENTIONS.md

## Nommage
- Labels asm préfixés par jeu : `bo_` (breakout), `jp_` (jumper), `oc_` (octopus) — évite les collisions entre kernels assemblés dans le même `.bin`
- Constantes en MAJUSCULES ; variables page zéro préfixées `zp_`

## Commentaires
- Chemin critique (boucle scanline) : `; N cycles, position X, doit finir @Y-Z` — obligatoire, vérifié par `tools/cycle_linter.py`, jamais laissé à l'appréciation
- Logique ARM : commentaires "pourquoi", pas "quoi" — la marge de cycles y rend déjà le code lisible sans glose
- En-tête de fichier : bloc court "pourquoi ce fichier / ce qu'il possède", pas une description exhaustive

## Commits — Conventional Commits, adapté au projet
Format : `<type>(<lane/porte>): <description>`
Types : `feat`, `fix`, `spike`, `docs`, `chore`, `refactor`

Exemples :
- `spike(0.1): mesure cycles bus-stuffing + GRP0 sur ligne partagée`
- `feat(proto4): kernel score 4 chiffres`
- `docs(adr): documente choix bus stuffing vs DPC+`

## Branches
Trunk-based. Une branche courte par spike/proto (`spike-0-1-bus-stuffing`, `proto-4-score-kernel`). Merge seulement si la Definition of Done est cochée (voir `backlog.md`).

## ADR — Architecture Decision Records
Va dans `docs/adr/NNNN-titre.md` toute décision qui a nécessité un arbitrage réel ("on sacrifie X pour Y") — pas un simple choix d'implémentation. Format dans `docs/adr/0000-template.md`.
Règle de tri : si tu peux écrire "conséquence : on sacrifie ___", c'est un ADR. Sinon, un commentaire de code suffit.

## Protocole IA
Voir `backlog.md` § Protocole IA — le repo est la mémoire de l'agent entre les sessions, pas sa documentation.
