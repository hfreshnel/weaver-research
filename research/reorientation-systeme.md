# Proposition de réorientation : de l'agent seul vers la couche système (2026-11-03)

Statut : **proposition**, à valider par le porteur du projet. Rien n'est mesuré ici sauf
mention contraire. Les chiffres du banc viennent de `CLAUDE.md` et `bench/agent/NOTES.md`.

## 1. Constat : ce que nos mesures couvrent

Presque tout le travail porte sur le cerveau et sa boucle d'agent :
- modèles : Qwen3.5 4B / 9B, Bonsai 2, Ornith, Spark (écartés ou retenus sur mesures) ;
- politique d'agent : confirmation dure, corbeille invisible, pipes sûrs, vérification ;
- un **simulateur** de machine Ubuntu (pas une vraie machine), canal d'action unique : shell + fichiers.

Les derniers gains sont petits (+0,25 à +3 cas sur 66, souvent non significatifs). Le plafond
restant vient de lacunes de connaissances (`print_duplex`, `safe_updates` à 0).

## 2. Ce que la vision exige et qu'on n'a pas encore testé

| Principe | Exigence | État |
|---|---|---|
| 4. Sans crainte de casse | snapshots, base immuable, retour arrière au niveau système | hypothèse « Linux natif » posée, **rien d'essayé** ; seule la corbeille existe |
| 1. Toutes les tâches | plusieurs canaux : API/MCP, arbre d'accessibilité, pixels, web | **un seul canal mesuré** (shell/fichiers) |
| 2. Mieux qu'un humain lambda | référence humaine | **aucune mesure** |
| 5. Pas de verrou | absorber les changements de version d'outils | non testé |

Preuve que la garde par commande ne suffit pas : un `pdfunite` simulé a écrasé son entrée
(voir « Methodology lessons » dans `CLAUDE.md`).

## 3. Note de comparaison : Omarchy

Source : omarchy.org et presse (voir plus bas). Faits vérifiés sur le site ; les éléments de
2026 sur la fondation et « Quattro » viennent de sources secondaires, **non vérifiés**.

- Arch Linux + Hyprland + Quickshell, préconfiguré et opinionné, créé par DHH, licence MIT.
- Se présente comme « the malleable OS for the age of agents » : au premier démarrage on
  choisit un agent cloud (Claude Code, Codex, Copilot CLI…), qui sert à diagnostiquer les
  plantages et à créer applis, plugins et thèmes via des « skills ».
- Ce qui nous intéresse : une distribution **reproductible et scriptable**, modifiable par un agent.
- Ce qui ne correspond pas à notre cible : orienté développeur (clavier, tiling, terminal),
  agent cloud ajouté par-dessus, pas de mode hors-ligne, pas de garanties de sécurité
  appliquées en code, aucune mesure de fiabilité publiée à notre connaissance.

Conclusion : à suivre comme exemple de distribution « modifiable par agent », pas comme base.

## 4. Pistes proposées (par ordre recommandé)

1. **Snapshots avant chaque action + retour arrière réel**, testés sur une vraie machine
   Linux (VM) : Btrfs/Timeshift ou équivalent. Objectif : rendre le principe 4 *vérifiable*
   (un cas d'échec injecté, restauration complète, métrique de perte de données à zéro).
   Coût : une VM (QEMU) et une image Ubuntu. **Demande d'accord préalable, tailles à donner.**
2. **Un premier canal non-shell** : arbre d'accessibilité (AT-SPI sous Linux, UI Automation
   sur l'hôte Windows) sur une tâche d'application graphique, comparé au shell sur la même tâche.
3. **Une référence humaine** même petite (quelques personnes, quelques tâches du banc novice).
4. En parallèle, sans lourdeur : garder la configuration actuelle du cerveau, ne plus empiler de modèles
   sans nouvelle hypothèse.

## 5. Décisions demandées
- Valider ou amender l'ordre ci-dessus.
- Accord pour préparer la piste 1 (je listerai tailles et dépendances avant tout téléchargement).
- Dire si les notes Omarchy vont dans `state-of-the-art.md` ou restent ici.

## Sources
- https://omarchy.org
- https://thenewstack.io/what-is-omarchy-linux-and-why-is-37signals-moving-to-it/
- https://www.starryhope.com/linux/what-is-omarchy/
- https://feedbagel.com/post/omarchy-is-not-a-distro
- https://next.ink/254383/omarchy-une-distribution-qui-seduit-un-createur-et-une-fondation-qui-divisent/
