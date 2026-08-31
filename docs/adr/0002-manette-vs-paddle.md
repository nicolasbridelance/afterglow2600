# 0002 — Manette digitale plutôt que paddle pour Casse-briques

**Statut :** accepté — à reconfirmer après Spike 0.1
**Date :** cahier des charges v7, section 12.6

## Contexte
Le Breakout historique utilise un paddle (lecture analogique via INPT0-3). Le critère de sélection des jeux (12.1) impose une manette digitale 4 directions + 1 bouton, commune aux trois jeux du moteur mutualisé.

## Options considérées
- Paddle — fidèle à l'original, mais usage isolé dans le portfolio de jeux
- Manette digitale — cohérente avec Le Jumper et Octopus

## Décision
Manette digitale retenue.

## Conséquences
- Gain : mutualisation de `/engine/input.asm` sans double driver
- Sacrifice : authenticité historique du contrôle de la balle
- Condition de réouverture explicite : si le Spike 0.1 montre que la balle a besoin d'un contrôle plus fin que le digital, cette décision doit être révisée — pas un oubli, une dépendance assumée
