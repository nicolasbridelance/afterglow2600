# AGENTS.md

Instructions minimales pour tout agent codant sur ce repo (Claude Code, Codex, Cursor...).
Contexte complet : voir `cahier_des_charges.md` (vision/archi) et `backlog.md` (état d'avancement, portes de décision). Ne pas dupliquer ce contenu ici.

## Commandes
- Assembler : `dasm main.asm -f3 -o<jeu>.bin -l<jeu>.lst`
- Vérifier le budget de cycles : `python3 tools/cycle_linter.py <jeu>.lst` (version minimale posée au Spike 0.1 — somme les cycles entre WSYNC ; à étendre avant Proto 1, voir backlog.md)
- Tests rasterizer / logique ARM : `pytest tools/ tests/`
- Vérification structurelle headless (boot sans crash + type de bankswitch détecté) : `xvfb-run -a stella -video software -audio.enabled 0 -logtoconsole 1 -holdreset <jeu>.bin` — ne prouve NI le comportement ARM bus-stuffing (ROM 4K simple, pas un vrai cart DPC+/CDFJ) NI le rendu visuel/scintillement CRT (voir backlog.md § Protocole IA, Émulation)

## Contraintes non négociables (ne jamais enfreindre silencieusement)
- Aucune multiplication/division runtime sur le 6507 — table précalculée ou décalage de bits uniquement
- Toute instruction dans une boucle scanline porte une annotation `; N cycles, position X, doit finir @Y-Z`
- Le kernel d'affichage (`kernel_*.asm`) n'est jamais factorisé entre jeux, même si ça semble plus propre — chaque jeu a sa propre disposition d'objets matériels
- Score et détection de collision restent côté 6507 (registres CX*), jamais transités par l'ARM

## Ne jamais modifier sans porte franchie
- `/games/breakout/kernel_breakout.asm` — rien tant que le résultat du Spike 0.1 n'est pas écrit dans `backlog.md`
- `vcs.h` — référence figée (constantes registres TIA/RIOT), ne pas "améliorer"

## Style
Voir `CONVENTIONS.md` (nommage, commentaires, commits, branches, ADR).

## Après toute modification
Mettre à jour `backlog.md` (portes franchies, décisions). C'est la seule mémoire persistante du projet entre deux sessions d'agent.
