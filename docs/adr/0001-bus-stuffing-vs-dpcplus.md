# 0001 — Bus stuffing comme driver bas niveau, pas DPC+/CDFJ seul

**Statut :** accepté
**Date :** cahier des charges v1

## Contexte
Le projet vise une densité graphique jugée impossible à l'époque sur Atari 2600. Le choix du driver bas niveau détermine directement le budget de cycles disponible par écriture TIA.

## Options considérées
- DPC+/CDFJ seul — plus simple, précédent plus large dans la scène homebrew
- Bus stuffing — écriture TIA en 3 cycles vs ~5-6 en 6507 pur

## Décision
Bus stuffing retenu comme driver bas niveau principal.

## Conséquences
- Gain : c'est le levier principal de densité graphique — raison d'être du projet
- Sacrifice : timing extrêmement serré (fenêtres de quelques cycles), support Stella partiel selon version, dépendance à une cartouche Harmony/Melody ou UnoCart 2600
- Implication directe : nécessite le Spike 0 (bus stuffing + sprite natif mobile sur la même ligne) avant tout engagement d'architecture — voir cahier des charges 9.2
