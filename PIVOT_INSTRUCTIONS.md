# Décision de pivot architectural — abandon ARM/DPC+/CDFJ+

**Date :** 2026-08-31
**Statut :** confirmé par l'utilisateur (Nicolas Bridelance) en session Claude Code, appliqué au repo le même jour.

---

## 1. La décision, et pourquoi

Pivot validé : **abandon de l'architecture Harmony/DPC+/CDFJ+/ARM, retour à une cartouche bankswitchée pure (F8 ou F6), 100% 6507/TIA natif, zéro coprocesseur.**

Raison de fond, pas juste technique : le projet vise "poussée au maximum matériel" comme accroche (une machine de 1977-1989, un développeur d'époque qui va plus loin que ce qu'on croyait possible). Une cartouche Harmony embarque un microcontrôleur ARM sorti en 2010, avec un cœur ARM7TDMI dont le premier exemplaire (ARM1) date de 1985 — postérieur à la sortie de la console de 8 ans, et le firmware ciblé (DPC+/CDFJ+) n'a évidemment aucun équivalent d'époque. Utiliser cette puce pour faire le travail à la place du 6507, c'est trahir l'accroche du projet, pas la réaliser. Ce n'est pas un problème de faisabilité, c'est un problème d'authenticité — formulé ainsi par l'utilisateur : *"le but n'est pas d'utiliser l'Atari comme une prise péritel et brancher une carte graphique 5090 dans une cartouche."*

**Ce que les spikes avaient découvert, indépendamment de cette raison de fond, pointait déjà dans la même direction** : `CDFJ+` n'implémente dans Stella aucune substitution sur écriture (seulement du fast-fetch en lecture), le vrai mécanisme d'écriture vit dans un type `BUS` marqué EXPERIMENTAL sans driver disponible, et le coût d'un aller-retour ACE est structurellement invérifiable en émulateur (Stella traite l'appel comme "zéro cycle 6507"). Le chemin ARM était à la fois le moins authentique et le plus bloqué en outillage. Le pivot résout les deux problèmes d'un coup.

## 2. Ce qui reste valable (pas jeté par le pivot)

- **Le travail de recherche des spikes 0.1/0.1b/0.2/0.2b** : conservé, archivé dans `spikes/`, marqué SUPERSEDED. C'est un vrai travail d'investigation qui explique et justifie la décision de pivot.
- **`tools/cycle_linter.py`** : générique 6502/6507 (somme de cycles entre `WSYNC` à partir du listing DASM), aucune dépendance ARM — reste directement utile, sinon plus, à une architecture 100% 6507. Vérifié par lecture du code au moment du pivot.
- **Les conventions de `backlog.md`** (lanes, cases à cocher, style de documentation honnête) : inchangées, rien d'ARM-spécifique.
- **Toute conception qui ne mentionne pas l'ARM** : détection de collision (registres matériels natifs), moteur audio (AUDC/AUDF/AUDV), kernel de score (NUSIZ), direction artistique et pipeline offline de rastérisation.
- **`chunkypixel.atari-dev-studio`** (extension VS Code, `.vscode/extensions.json` / `.devcontainer/devcontainer.json`) : extension générale DASM/Stella, pas ARM-spécifique — conservée telle quelle.

## 3. Ce que le pivot change dans `backlog.md`

- Lane 0 : Spikes 0.1, 0.1b, 0.2, 0.2b passent de "bloquant" à "résolu par pivot architectural — voir ce document" et ne conditionnent plus Lane 2.
- Porte 0 (sign-off lead dev/CTO sur 0.1/0.2) : remplacée par cette décision de pivot elle-même, actée le 2026-08-31.
- Seul spike réellement ouvert pour la suite : **le mécanisme de bascule FRC** (alternance de tables de teintes en vblank, section 5.3/9.2 pt.4 du cahier des charges) — mécanisme 100% 6507, testable dès maintenant.

## 4. Ce qui reste en attente

La conception détaillée de Lane 2+ (kernels, tables, budgets de cycles précis, choix F6 vs F8 par jeu) **n'a pas été relancée**.

**Mise à jour 2026-08-31 — `cahier_des_charges.md` réécrit par cette session, à la demande explicite de l'utilisateur.** Le brief original recommandait d'attendre la révision en cours côté utilisateur pour éviter deux versions divergentes du document. L'utilisateur a explicitement demandé à cette session de réécrire quand même (question posée, réponse : "Oui, réécris-le maintenant") — le document est donc passé en Draft v8, sections 1, 2, 3(inchangée), 4.1-4.7, 6, 7, 8, 9, 9.1(inchangée), 9.2, 10, 11.1-11.3, 12.1-12.10 revues pour retirer toute référence ARM/DPC+/CDFJ+/bus stuffing. Le playfield asynchrone (chapitre Hugg) devient le seul chemin pour les briques, comme anticipé ici — confirmé par cette réécriture, pas par la révision de l'utilisateur qui reste, à la connaissance de cette session, une source indépendante potentiellement différente. **Si une version de l'utilisateur arrive ensuite, elle prime** — comparer et fusionner plutôt que d'écraser silencieusement l'une par l'autre, exactement le risque de divergence que ce paragraphe signalait à l'origine.
