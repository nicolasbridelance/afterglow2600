> ⚠️ SUPERSEDED — voir [`PIVOT_INSTRUCTIONS.md`](../../PIVOT_INSTRUCTIONS.md). Le projet a abandonné l'architecture ARM/DPC+/CDFJ+ (2026-08-31). Conservé comme preuve de la décision de pivot, ne bloque plus rien.

# Spike 0.1b — construire spike_0_1 en vrai ROM à bus-stuffing réel sous Stella

Investigation, pas un kernel livré. **Résultat : la ROM n'a pas été construite —
la prémisse du plan initial (backlog.md) s'est révélée fausse avant toute
construction, et la corriger ouvre une question de portée qui revient à
l'utilisateur, pas à trancher seul.**

## Ce qui était prévu vs ce qui a été trouvé

Le backlog demandait de construire `spike_0_1` "en vrai ROM CDFJ+" pour vérifier
sous Stella le comportement du bus-stuffing (`STA <TIA reg>`, `A=$FF` préchargé)
face à une écriture native intercalée (`GRP0`). Avant de construire quoi que ce
soit, vérification du mécanisme réellement implémenté par Stella — même méthode
que pour Spike 0.2 (lecture directe du code source, pas de supposition) :
clone `stella-emu/stella` (même commit `0969155`, voir Spike 0.2), lecture de
`CartDPCPlus.cxx`, `CartCDF.cxx`, `CartBUS.cxx`, `System.hxx/.cxx`.

**Deux mécanismes distincts existent dans Stella, et backlog.md les avait confondus :**

1. **"Fast Fetch"** (`CartDPCPlus.cxx`, `CartCDF.cxx` — types `DPC+` et `CDF`/`CDFJ`/`CDFJ+`) :
   substitution sur **lecture**. Stella surveille l'opérande d'une instruction
   `LDA #val` / `LDX #val` / `LDY #val` (peek de l'octet immédiat juste après
   l'opcode `$A9`/`$A2`/`$A0`) et le remplace par un octet de datastream si sa
   valeur tombe dans une plage réservée. **Aucune substitution sur écriture
   (`STA`) n'existe dans ce mécanisme.**
2. **"Bus Stuffing"** (`CartBUS.cxx` — type `BUS` uniquement, marqué
   `EXPERIMENTAL, AND MAY BE REMOVED IN A FUTURE RELEASE` dans le code source
   lui-même) : substitution sur **écriture**, mais déclenchée par l'opcode
   `STY` (`$84`), pas `STA` (`$85`) — vérifié ligne à ligne : Stella détecte le
   fetch de l'opcode `0x84`, mémorise l'adresse zéro-page opérande au fetch
   suivant, puis à l'écriture réelle applique `value &= busOverdrive(address)`
   (ET logique avec l'octet ARM — cohérent avec la technique matérielle réelle
   décrite par Big Mess o' Wires : le bus ne peut être tiré qu'à 0, d'où le
   préchargement à `$FF`, mais avec `Y` pas `A`).

**Conséquence directe** : `CDFJ+` (ce que backlog.md visait) n'implémente
**aucune** substitution sur écriture dans Stella — construire `spike_0_1.asm`
(qui utilise `STA`) en ROM CDFJ+ n'aurait exercé aucun bus-stuffing, quel que
soit le driver ARM embarqué, parce que la logique de substitution est câblée en
C++ natif côté Stella et ne dépend pas du binaire ARM chargé. Le mécanisme que
`spike_0_1.asm` teste réellement (et que l'article Big Mess o' Wires cité en
en-tête décrit) correspond au type `BUS`, pas `CDFJ+`.

## Pourquoi la ROM n'a pas été construite malgré cette correction

Le pipeline prouvé pour Spike 0.2 (bB + wasmtime + `arm-none-eabi-gcc`) ne
couvre pas le type `BUS` :
- `bB` (`out/bin/compilers/bB/includes/` de l'extension `chunkypixel.atari-dev-studio`)
  ne propose que deux noyaux ARM : `DPC+` et un noyau non documenté `PXE`
  (signature `"PXE-ROM"` — ne correspond à aucune chaîne d'auto-détection
  trouvée dans `CartDetector.cxx`, donc probablement non reconnu par Stella
  tel quel ; aucune mention de `PXE` dans le `readme.md`/`changelog.md` de
  l'extension). Aucun noyau `BUS`.
- Aucun driver ARM précompilé pour le type `BUS` n'a été trouvé dans le
  sandbox (contrairement à `DPCplus.arm`, présent et utilisé pour Spike 0.2).
  Les seules ROM `BUS` connues sont ~4 démos techniques 2016-2017
  (`draconian`, `128bus`, `128chronocolour`, `parrot`, `rpg` — noms cités dans
  `CartBUS.cxx`), non présentes ici, de licence/provenance non vérifiée, et le
  type lui-même est explicitement expérimental côté Stella.

Construire une ROM `BUS` demanderait donc soit un vrai driver ARM `BUS`
(à trouver/extraire d'une démo tierce — provenance et réutilisabilité non
vérifiées, pas tenté), soit écrire un driver ARM `BUS` from scratch (hors
budget d'un spike). Ce n'est **pas** "une extension directe de ce qui existe
déjà" comme l'affirmait la note du 2026-08-31 dans backlog.md — cette note
était optimiste à tort, corrigée ici.

## Ce qu'on sait quand même (analyse statique, sans exécution)

Le vrai firmware ARM (désassemblé pour Spike 0.2b, voir `spikes/spike_0_2b/`)
contient une boucle de dispatch continue qui lit l'adresse courante du bus 6507
à chaque cycle et décide quoi servir **par adresse**, pas par position dans une
séquence attendue. Structurellement, ça implique qu'une écriture native
non surveillée (ex. `GRP0`, hors plage `$00`-`$24` pour l'overdrive `BUS`, ou
simplement une adresse que le firmware ne reconnaît pas comme un déclencheur)
devrait être transparente pour le firmware — pas de risque de désynchronisation
d'un "pointeur de séquence" puisqu'il n'y en a pas dans ce qui a été lu. Voir
`spikes/spike_0_2b/README.md` pour le détail et les réserves.

**Ceci reste une lecture statique d'un binaire non documenté, jamais exécutée
ni confirmée dynamiquement — à traiter comme un indice, pas une preuve.**

## Conclusion pour la Porte 0

Spike 0.1b, tel que scopé dans backlog.md, **repose sur une prémisse fausse**
(CDFJ+ ≠ bus-stuffing sur écriture). La corriger fait remonter une vraie
question de portée, pas un simple détail technique :

- **Option A** — abandonner la piste `STA`/bus-stuffing-sur-écriture pour
  Proto 1+ et s'appuyer sur le "fast fetch" `CDFJ+` (`LDA`/`LDX`/`LDY`
  immédiat) à la place, qui LUI est réellement outillé et testable ici. Change
  la technique de rendu prévue pour les briques (implique une réécriture de
  `spike_0_1.asm`, pas juste un rebuild).
- **Option B** — rester sur le vrai bus-stuffing (`STY`, type `BUS`) et
  accepter de sourcer/écrire un driver ARM `BUS`, hors budget spike, à
  chiffrer séparément si retenu.
- **Option C** — traiter Spike 0.1 (mesure structurelle DASM déjà faite) comme
  suffisant pour la Porte 0 et reporter la vérification ARM réelle à une
  session hardware (Lane 1), sans poursuivre Spike 0.1b plus loin.

Pas de recommandation tranchée ici — c'est une décision de possession de
projet (voir CLAUDE.md § Protocole IA), pas un fait vérifiable par le code.
