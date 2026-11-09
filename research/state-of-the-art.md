# État de l'art — OS IA (octobre 2026)

Date : 2026-10-25. Méthode : recherche web (≈25 requêtes) + API Hugging Face/GitHub.

**Fiabilité.** Une grande partie de la couverture 2026 vient de blogs secondaires, parfois
SEO, qui se contredisent sur les dates et les chiffres. Chaque affirmation porte une étiquette :
- **[P]** source primaire (papier, blog officiel, spec) ;
- **[S]** secondaire concordante ;
- **[?]** source unique ou douteuse, à vérifier avant de s'appuyer dessus.
Les scores de benchmark annoncés par les éditeurs restent auto-déclarés.

---

## 0. Synthèse en 8 points

1. **Les OS grand public deviennent « agentiques » par couches, pas par refonte.**
   - Windows ajoute MCP natif, un *Agent Workspace* isolé et des identités d'agent.
   - Apple reconstruit Siri au niveau système.
   - Google fusionne ChromeOS dans Android (Aluminium OS) avec Gemini qui agit entre les apps.
   - Le noyau et le modèle d'apps restent classiques. L'IA est une couche d'orchestration au-dessus.
2. **La convergence technique : des actions structurées d'abord, le pilotage d'interface (GUI) en dernier recours.**
   - Côté actions structurées : MCP chez Windows et partout, App Intents chez Apple, AppFunctions chez Android.
   - Les meilleurs agents GUI mélangent clics et commandes CLI (Qwen-UI-Agent).
   - Le pixel est le chemin universel mais lent et fragile. L'API est rapide et fiable.
3. **Le computer use a dépassé l'humain sur OSWorld-Verified, mais pas sur les tâches longues.**
   - OSWorld-Verified : ~85 % auto-déclarés, contre 72 % pour l'humain.
   - OSWorld 2.0, avec des workflows longs : ~20 % de complétion seulement.
   - Le problème ouvert n'est plus « cliquer juste », c'est la **fiabilité sur un horizon long**.
4. **L'« OS halluciné » est sorti du gadget, mais reste de la recherche.**
   - Pixels générés : NeuralOS (ICLR 2026), Runway Solaris (sept. 2026).
   - UI générée en code (HTML/widgets) : Google Generative UI, A2UI, Imagine with Claude.
   - Seule la seconde famille est exploitable aujourd'hui, et sur notre machine.
5. **Le petit modèle local devient crédible pour appeler des outils.**
   - BFCL v4 : MiniCPM5-2B 66,6 % [?], Granite 4.2 3B 52,4 % [S].
   - La famille Qwen3.5 4B/9B est annoncée forte sur τ²-bench [S].
   - Des modèles GUI compacts sont ouverts : Fara-7B, MAI-UI-2B/8B, avec des GGUF disponibles.
6. **Les protocoles se sont stabilisés.**
   - MCP est passé sous gouvernance neutre (Agentic AI Foundation, Linux Foundation, déc. 2025).
   - Spec 2026-07-28 *stateless* ; A2A rejoint la même fondation (août 2026) [S].
   - Construire sur MCP n'est plus un pari.
7. **La sécurité est le frein n°1, et elle se mesure.**
   - L'injection de prompt (visuelle ou en plusieurs étapes) reste efficace : StepJack mesure 31 à 37 % de taux de succès d'attaque [P].
   - Une tâche bénigne peut aussi pousser l'agent à violer une contrainte (OSGuard) [P].
   - Le rejet de Windows « agentic OS » par les utilisateurs porte sur la vie privée et le contrôle [S].
8. **Les benchmarks sont eux-mêmes fragiles.**
   - Le score dépend fortement de l'échafaudage autour du modèle (scaffold).
   - ~11 % des échecs audités sont des faux négatifs de l'évaluateur [P].
   - Leçon pour nous : figer l'environnement, publier le scaffold, et diagnostiquer chaque échec plutôt que de se fier au seul pourcentage.

---

## 1. OS conventionnels : ce qui est nouveau

### Windows 11 : « agentic OS » (Ignite, nov. 2025 → 2026)
- **MCP natif** en preview, avec des connecteurs système (Explorateur de fichiers, Paramètres) [P].
- **Agent Workspace** : session isolée et gouvernée par des politiques, où les agents travaillent en parallèle sans prendre la main sur la session utilisateur [P].
- **Copilot Actions** : l'agent clique et tape dans les apps, via Copilot Labs et Insiders [P].
- **Agent IDs** : chaque agent a une identité propre, et ses actions sont journalisées et attribuées [S].
- Point d'entrée : « Ask Copilot » dans la barre des tâches. Accueil hostile : vie privée, bloat, exigence de matériel Copilot+ [S].
- **À retenir** : isolation de l'agent, identité, journal d'audit, et l'OS comme fournisseur de serveurs MCP.

### Apple : macOS 27 / iOS 27 (WWDC juin 2026, sortie sept. 2026)
- **Nouveau Siri** basé sur les Apple Foundation Models et la technologie Gemini [P : page Apple].
  - Il agit au niveau OS : Mail, Messages, Photos, contenu à l'écran.
  - Il gère des commandes en plusieurs étapes et s'intègre à Spotlight et au clic droit sur un fichier [S].
- **Raccourcis générés en langage naturel**, veille de pages dans Safari, changement automatique des mots de passe compromis [S].
- **Chatbots tiers** (Claude, Gemini) intégrables à Siri : rumeur pré-WWDC [?].
- Socle hérité de 2024-2025, de mémoire et à vérifier :
  - **App Intents** : les apps exposent leurs actions de façon sémantique ;
  - framework **Foundation Models** : les développeurs accèdent au modèle local d'environ 3B.
- **À retenir** : l'agent n'agit pas par pixels, il agit via des intentions déclarées par les apps, plus le contexte de l'écran.

### Google : Android 17 / Aluminium OS (annonce mai 2026, appareils automne 2026)
- Android devient un OS desktop (« Googlebook »), ChromeOS y est absorbé [S].
- Gemini comme couche transverse : il comprend l'écran, passe d'une app à l'autre et enchaîne des actions [S]. *Magic Pointer* : IA contextuelle au curseur [?].
- Fonctions de base en local, avec Gemini Nano sur le NPU. Exigence de 12 Go de RAM minimum [?].
- Chrome *auto browse* (Gemini 3), en janvier 2026 sur desktop et en juin 2026 sur Android, réservé aux abonnements payants [S].
- **À retenir** : modèle hybride, petit modèle local et gros modèle cloud. Le navigateur sert de premier terrain d'action.

### Huawei : HarmonyOS 6 → 7
- HMAF (Harmony Agent Framework) en 2025 : les agents coopèrent avec les apps, les services et les appareils [S].
- HarmonyOS 7 (bêta développeurs 2026) : HMAF 2.0 avec plus de 20 capacités IA système, dont le pilotage GUI. Plus de 90 % de réussite annoncée sur des tâches complexes [?, chiffre maison].

### Linux desktop
- Pas d'initiative officielle forte de GNOME, de KDE ou de Canonical [S].
- Écosystème d'apps tierces : Newelle 1.0 (GNOME, avec mémoire et exécution de commandes shell), Moose, Alpaca, une plasmoïde KDE Assistant. Toutes reposent sur Ollama ou LM Studio [S].
- **Omarchy** (DHH, créateur de Ruby on Rails ; ajouté 2026-11-03) : Arch Linux + Hyprland + Quickshell préconfigurés, opinionnés, licence MIT. Le site se présente comme « the malleable OS for the age of agents » [P]. Au premier démarrage on choisit et on connecte un agent **cloud** (Claude Code, Codex, Copilot CLI…) ; il sert à diagnostiquer les plantages (clic sur la notification) et à créer applis, plugins et thèmes via des « skills » intégrées [P].
  - Ce qui est intéressant : une distribution reproductible et scriptable, pensée pour être modifiée par un agent.
  - Limites par rapport à notre cible : orienté développeur (tiling, clavier, terminal), agent ajouté par-dessus et dépendant du cloud, pas de garanties de sécurité appliquées en code ni de mode hors-ligne, aucune mesure de fiabilité publiée à notre connaissance. Certains critiques estiment que ce n'est pas une vraie distribution mais Arch plus les dotfiles de DHH [S].
  - [?] Des sources secondaires de 2026 parlent d'une fondation (« Omacom ») financée à hauteur de 8 M$, de la version « Quattro » et de controverses autour de DHH : non vérifié.
- **À retenir** : il n'y a toujours pas de « couche agent système » **locale, sûre et pensée pour des non-développeurs** sur le desktop Linux, et c'est le créneau d'un prototype comme weaver. Omarchy est le plus proche en esprit (OS modifiable par agent) mais vise un autre public et un autre modèle (cloud).

### Navigateurs agentiques (le « second OS »)
- OpenAI a **retiré Atlas** (juillet-août 2026) et replié l'agent dans l'app desktop, une extension Chrome et Codex [S].
- Perplexity Comet est devenu gratuit et multiplateforme. Edge a absorbé « Copilot Mode » [S].
- **Tendance** : le navigateur IA autonome recule. L'agent s'intègre dans l'existant.

---

## 2. OS et appareils « pilotés par IA »

| Projet | Nature | Statut 2026 | Enseignement |
|---|---|---|---|
| Rabbit R1 / rabbitOS (Large Action Model) | Appareil dédié | Antérieur à la vague 2026 [S] | Échec produit initial : l'agent GUI n'était pas fiable |
| Humane AI Pin | Appareil sans écran | Abandonné (2025) | La forme seule ne suffit pas sans fiabilité |
| OpenAI × io (Jony Ive) | Enceinte portable sans écran « GPT-Live » | Annonce possible fin 2026, sortie 2027 [?] | Pari sur la voix d'abord |
| Doubao Phone (ByteDance) | Téléphone avec agent GUI système | Bloqué par WeChat, Taobao, Meituan [?] | Les apps tierces peuvent **refuser l'agent** : risque de plateforme |
| Zhipu AutoGLM / Open-AutoGLM | Agent téléphone via ADB et un modèle de vision | Open source (déc. 2025), modèle AutoGLM-Phone-9B [S] | Architecture de référence ouverte pour le mobile |
| Warmwind OS 1.0 | Bureau Linux cloud piloté par agents | Août 2026 [?] | « OS » au sens marketing : un employé virtuel |
| AIOS (Rutgers) | « Noyau » pour agents : ordonnanceur, mémoire, contexte, contrôle d'accès | Recherche, papier révisé [P] | Formalise les services OS pour agents ; jusqu'à 2,1× plus rapide |
| Microsoft UFO / Agent S, etc. | Frameworks d'agents desktop | Recherche et open source | Hybride API + GUI |

**Constat** : en 2026, aucun « OS IA » grand public généraliste n'existe hors des trois grands. Les produits indépendants sont des appareils dédiés, des clouds verticaux ou des frameworks. Les échecs (Rabbit, Humane) viennent tous de la **fiabilité de l'action**, pas de l'interface.

---

## 3. OS « hallucinés » et interfaces génératives

Ces approches forment un spectre, de la plus concrète à la plus radicale.

| Niveau | Ce qui est généré | Exemples | Faisable chez nous ? |
|---|---|---|---|
| A. Composants | Choix et paramétrage de widgets dans un catalogue | Google **A2UI v0.9** (standard agnostique) [P], Flutter GenUI, Vercel AI SDK | Oui, très léger |
| B. App complète en code | HTML/CSS/JS générés à la volée | Google **Generative UI** (le LLM comme générateur d'app full-stack) [P], *Generative Interfaces for LMs* [P], **Imagine with Claude** (aperçu de recherche, 2025) [S] | Oui, avec un LLM local de 4 à 9B (qualité à mesurer) |
| C. OS simulé par LLM | Chaque écran est régénéré par le LLM à chaque action | Démo Google « neural OS » avec Gemini 2.5 Flash-Lite (juin 2025) : prompt système fixe et JSON de la dernière action, UI en flux, graphe d'état en mémoire [P] | Oui, c'est une variante du niveau B ; la latence est le critère clé |
| D. Pixels générés (world model d'interface) | Les frames de l'écran elles-mêmes | **NeuralOS** (ICLR 2026) : un RNN d'état et un rendu par diffusion, entraîné sur Ubuntu XFCE, ~18 FPS sur H100 [P/?] ; **Runway Solaris** (sept. 2026) : génération image par image conditionnée par la souris, et un LLM séparé qui interprète l'intention [P] | Non, pas sur 6 Go en temps réel |
| E. Mondes interactifs | Environnements 3D | Genie 3 (DeepMind, 720p 24 fps, cohérent quelques minutes) [P] | Non, réservé au cloud |

- **Limites connues** de la génération de pixels :
  - texte lisible, ancrage de confiance (comment savoir que l'action a vraiment eu lieu), cohérence sur une longue session, accessibilité (lecteur d'écran), selon Runway [S] ;
  - saisie clavier fine, selon NeuralOS [P].
- **Évaluation utilisée** : préférence humaine par paires. Solaris rapporte 61 % contre 24 % sur le suivi d'instructions face à des interfaces codées [S, étude maison].
- **Pour nous** : l'idée exploitable est que **l'état reste réel et structuré, seule la vue est générée**. On génère l'UI (niveaux A à C) au-dessus d'un état vérifiable. Une UI qui « hallucine » l'état d'un fichier est inacceptable pour un OS.

---

## 4. LLM agentiques

### Modèles frontière (cloud, référence haute)
- Leaders OSWorld-Verified, auto-déclarés : Qwen3.8-Max (86,1 %), Claude Mythos Preview, Mythos 5 et Fable 5 (~85 %), Opus 4.8 (83,4 %), MiMo-V2.6-Pro (82 %) [S : leaderboard Steel].
- OSWorld 2.0 (108 workflows longs) : Opus 4.8 en réflexion maximale atteint 20,6 % de complétion et 54,8 % de score partiel ; GPT-5.5 plafonne vers 13 % [P].

### Petits modèles ouverts compatibles avec 6 Go de VRAM

| Modèle | Rôle | Taille GGUF Q4 | Signal |
|---|---|---|---|
| Qwen3.5-2B / 4B / 9B | Cerveau (outils), vision native | 1,3 / 2,7 / 5,7 Go | 4B : τ²-bench 79,9 [S, éditeur] |
| Granite 4.2 3B / 8B | Cerveau (outils), Apache 2.0 | 2,2 / 5,4 Go | BFCL v4 : 52,4 (3B) [S] |
| Gemma 4 E4B | Cerveau embarqué, multimodal | 5,0 Go | Appels de fonctions natifs [S] |
| MiniCPM5-2B | Cerveau léger | ? | BFCL v4 66,6 [?] |
| LFM2.5 (Liquid) 1.2B / 2.6B / 8B-A1B | Cerveau embarqué, MoE | ~1 à 5 Go | BFCL v4 49,7 (8B-A1B) [S] |
| **Fara-7B** (Microsoft) | Agent GUI : capture d'écran → coordonnées | ~4,7 Go | SOTA de sa taille sur le web [P] |
| **MAI-UI-2B / 8B** (Alibaba Tongyi) | Agent GUI | GGUF communautaires | Open source (déc. 2025) [vérifié sur HF] |
| UI-TARS-1.5-7B | Agent GUI | ~4,5 Go | Base de nombreux travaux de grounding [P] |
| AutoGLM-Phone-9B | Agent mobile | ~5,5 Go | Open source [S] |

- **Qwen-UI-Agent** (Alibaba, juillet 2026) : variantes 4B, 27B et 35B-A3B.
  - Scores annoncés : OSWorld-Verified 79,5 %, ScreenSpot-Pro 81,5 %, avec actions GUI et CLI mélangées [P].
  - **Aucun poids public trouvé sur HF** pour l'instant. À surveiller : la variante 4B serait idéale pour nous.

### Protocoles et interopérabilité
- **MCP** sous l'Agentic AI Foundation (Linux Foundation, déc. 2025, avec Anthropic, Block et OpenAI) [S].
  - Spec 2026-07-28 : sans état, découverte via `server/discover`, extensions formalisées, Tasks et MCP Apps.
  - Roots, Sampling et Logging sont dépréciés [P : blog AAIF].
- **A2A** (agent à agent) a rejoint l'AAIF le 20 août 2026 [S].
- **Pour nous** : exposer les outils de weaver en serveurs MCP rend la couche réutilisable. Un client MCP est facile à brancher sur llama-server.

### Mémoire
- Benchmarks : LongMemEval et sa V2 (2026), LoCoMo, StreamMemBench (assistance anticipée), Personalize-then-Store [P].
- Les scores des éditeurs (Mem0 ~93 %, Zep 90 %) sont contredits par un test indépendant : Mem0 en open source à 32 % [?].
- *MemDelta* (2026) pointe des biais cachés dans ces évaluations [P].
- **Pour nous** : mesurer nous-mêmes. Une base SQLite + embeddings simple peut égaler un framework lourd.

### Voix
- Modèles full-duplex ouverts :
  - Moshi (Kyutai, ~200 ms annoncés, CC-BY) ;
  - PersonaPlex-7B (NVIDIA, licence restreinte) ;
  - **NemotronLabs VoiceChat 11B** avec appels d'outils (sept. 2026) [P] ;
  - MiniCPM-o 4.5.
- Benchmark : Full-Duplex-Bench-v3, qui teste l'usage d'outils avec les disfluences de la parole réelle [P].
- **Pour nous** : 11B dépasse 6 Go. Il faudra comparer une chaîne STT → LLM → TTS en cascade avec un petit modèle full-duplex.

---

## 5. Critères et benchmarks utilisés par le domaine

### Ce que mesurent ceux qui font la même chose

| Critère | Benchmarks de référence | Ordre de grandeur actuel | Pertinence pour weaver |
|---|---|---|---|
| **Réussite de tâches desktop** | OSWorld-Verified, OSWorld 2.0, Windows Agent Arena | 85 % (vérifié) / 20 % (horizon long) | Haute : c'est notre cœur |
| **Réussite mobile** | AndroidWorld, MobileWorld, AndroidDaily | 82 à 97 % annoncés [P] | Faible pour l'instant |
| **Web** | WebArena, Mind2Web, WebTailBench | 74 % sur WebArena [P] | Moyenne |
| **Appels d'outils** | BFCL v4, τ²-bench, MCP-Bench / MCPMark | Petits modèles entre 50 et 67 % sur BFCL v4 | **Immédiate** (bench v1 → v2) |
| **Grounding GUI** (cliquer au bon endroit) | ScreenSpot-v2, ScreenSpot-Pro | 3B ~88 % sur ScreenSpot-v2 [P] ; 52 à 81 % sur Pro | Plus tard (couche GUI) |
| **Efficacité** | OSWorld-Human : étapes de l'agent vs trajectoire humaine, latence par étape | Les agents font bien plus d'étapes que l'humain ; la latence vient surtout des appels LLM de planification [P, de mémoire] | **Haute** : critère clé en local |
| **Sécurité / injection** | OS-Harm, RiOSWorld, VPI-Bench, StepJack, OSGuard, AgentDojo | Taux d'attaque réussie de 31 à 37 % en plusieurs étapes [P] | **Haute** : un OS doit refuser et confirmer |
| **Mémoire long terme** | LongMemEval(-V2), LoCoMo, StreamMemBench | Résultats contestés | Moyenne (brique 3) |
| **Voix** | Full-Duplex-Bench-v3, latence de bout en bout | ~200 ms annoncés (Moshi) | Plus tard (brique 4) |
| **UI générative** | Préférence humaine par paires, suivi d'instructions, cohérence | Solaris 61 % contre 24 % [S] | Exploratoire |
| **Coût et ressources** | Tokens par tâche, latence, VRAM/RAM, énergie | Rarement publié | **Notre critère différenciant** |

### Leçons méthodologiques du domaine (à appliquer)
1. **Figer et publier** l'image de l'OS, les versions des apps et les paquets du scaffold. Le même modèle change de score selon l'échafaudage [P, 2607.28367].
2. **L'évaluateur doit tester exactement ce que la tâche déclare.** Sinon, ~11 % de faux négatifs. *Notre cas `zip_photos` en v1 illustre ce piège* : `list_dir` d'abord est une stratégie valide qu'un test en un seul tour rejette.
3. **Un taux de réussite seul ne suffit pas.** Il faut un diagnostic par échec, avec une catégorie : mauvais outil, mauvais argument, refus, boucle, dépassement de délai.
4. **Le score partiel compte** sur les tâches longues (OSWorld 2.0 publie complétion binaire + score partiel).
5. **Efficacité = critère de premier rang** : nombre d'étapes, latence par étape, tokens.
6. **La sécurité se mesure à part** : injections dans le contenu lu (fichiers, pages), actions destructrices, respect des contraintes même sur une tâche bénigne.

---

## 6. Implications pour weaver (propositions, à valider)

1. **Architecture cible** : action structurée d'abord (outils et MCP), GUI en dernier recours. C'est le consensus Windows / Apple / Qwen-UI-Agent.
   - La brique « perception écran » passe derrière la brique « outils réels ».
2. **Bench toolcall v2**, nourri par les critères ci-dessus :
   - multi-tours avec de vrais outils en bac à sable ;
   - score partiel et diagnostic par échec ;
   - cas de sécurité : commande destructrice → confirmation exigée ; injection cachée dans un fichier lu ;
   - efficacité : nombre d'étapes et latence par étape ;
   - résolution de dates.
3. **Candidats à ajouter** pour plus tard :
   - couche GUI : MAI-UI-2B (léger), Fara-7B ;
   - à surveiller : Qwen-UI-Agent 4B si ses poids sont publiés.
4. **Axe « OS halluciné » réaliste sur 6 Go** : comparer une UI générée en HTML (niveau B/C) par le même LLM local avec une UI fixe.
   - Critères : latence au premier rendu, cohérence entre deux actions, fidélité à l'état réel.
   - La génération de pixels (niveau D) est écartée pour le matériel, mais reste suivie en veille.
5. **Créneau** : le desktop Linux n'a pas de couche agent système. weaver peut viser ce trou avec :
   - de l'inférence 100 % locale ;
   - des agents isolés ;
   - un journal d'audit (comme l'Agent ID de Windows) ;
   - un réglage du niveau d'autonomie, l'« autonomy slider » de Karpathy [S].

---

## Sources

Fiabilité : [P] primaire · [S] secondaire · [?] à vérifier.

**OS conventionnels**
- [P] Microsoft — [Experimental agentic features](https://support.microsoft.com/en-us/windows/ai/ai-features/experimental-agentic-features), [Ignite 2025 Windows](https://techcommunity.microsoft.com/blog/windows-itpro-blog/evolving-windows-new-copilot-and-ai-experiences-at-ignite-2025/4469466)
- [S] [InfoWorld — building blocks of an agentic Windows](https://www.infoworld.com/article/4100474/the-first-building-blocks-of-an-agentic-windows-os.html), [Windows Forum — governance](https://windowsforum.com/news/windows-goes-agentic-microsofts-ai-agents-and-the-governance-challenge.390158/), [Windows Forum — backlash](https://windowsforum.com/threads/windows-agentic-os-on-device-ai-mcp-and-copilot-vision-explained.389171/)
- [P] [Apple Intelligence](https://www.apple.com/apple-intelligence/) · [S] [Digital Trends WWDC 2026](https://www.digitaltrends.com/computing/wwdc-2026-ios-27-siri-ai-apple-intelligence-upgrades-and-everything-else-apple-announced/), [Macworld macOS 27](https://www.macworld.com/article/3139330/macos-27-mac-features-siri-apple-intelligence-release-date-compatibility.html), [MacRumors (pré-WWDC)](https://www.macrumors.com/guide/wwdc-2026-what-to-expect/), [Lushbinary](https://lushbinary.com/blog/wwdc-2026-announcements-ios-27-siri-developer-guide/)
- [S] [Aluminium OS (Wikipedia)](https://en.wikipedia.org/wiki/Aluminium_OS), [Android Authority](https://www.androidauthority.com/aluminium-os-android-for-pcs-3619092/), [ChromebookFixes mai 2026](https://chromebookfixes.com/news/googlebook-aluminium-os-2026/)
- [S] [Gizchina HarmonyOS 6](https://www.gizchina.com/huawei/huawei-introduces-harmonyos-6-with-intelligent-agent-framework-and-developer-beta) · [?] [tbreak HarmonyOS 7](https://tbreak.com/huawei-harmonyos-7-system-level-ai-agents/)
- [S] [OMG! Ubuntu — Newelle](https://www.omgubuntu.co.uk/2025/08/newelle-ai-assistant-ubuntu-linux-desktop), [Phoronix — Moose](https://www.phoronix.com/news/GNOME-Moose-Local-AI), [KDE Assistant](https://github.com/hadealahmad/KDE-Assisstant)
- [P] [Omarchy](https://omarchy.org) · [S] [The New Stack — Omarchy et 37signals](https://thenewstack.io/what-is-omarchy-linux-and-why-is-37signals-moving-to-it/), [StarryHope](https://www.starryhope.com/linux/what-is-omarchy/), [feedbagel — « not a distro »](https://feedbagel.com/post/omarchy-is-not-a-distro), [Next — fondation et débats](https://next.ink/254383/omarchy-une-distribution-qui-seduit-un-createur-et-une-fondation-qui-divisent/)
- [S] [Navigateurs agentiques 2026](https://nohacks.co/blog/agentic-browser-landscape-2026), [Atlas vs Comet vs Gemini](https://browserbash.com/blog/chatgpt-atlas-vs-perplexity-comet-vs-gemini-in-chrome)

**OS et appareils IA**
- [?] [OpenAI device (Built In)](https://builtin.com/articles/openai-device), [techpillow](https://www.techpillow.co/blog/openai-io-speaker-jony-ive-gpt-live-companion)
- [S] [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM/blob/main/README_en.md), [AutoGLM](https://xiao9905.github.io/AutoGLM/)
- [?] [Warmwind OS](https://www.explainx.ai/blog/warmwind-os-ai-operating-system-1-0-launch-august-2026), [CortexPrism landscape](https://cortexprism.io/blog/open-source-ai-agent-os-2026-landscape)
- [P] [AIOS: LLM Agent Operating System](https://arxiv.org/html/2403.16971v4)

**OS hallucinés et UI générative**
- [P] [NeuralOS (arXiv 2507.08800)](https://arxiv.org/abs/2507.08800), [code](https://github.com/yuntian-group/neural-os)
- [P] [Runway Solaris (arXiv 2609.00776)](https://arxiv.org/pdf/2609.00776) · [S] [The New Stack](https://thenewstack.io/runway-solaris-generated-interfaces/), [CMSWire](https://www.cmswire.com/ai-platforms/runways-solaris-generates-software-interfaces-in-real-time-with-no-code-underneath/)
- [P] [Google — neural OS with Gemini 2.5 Flash-Lite](https://developers.googleblog.com/simulating-a-neural-operating-system-with-gemini-2-5-flash-lite/), [A2UI v0.9](https://developers.googleblog.com/a2ui-v0-9-generative-ui/)
- [P] [Generative UI: LLMs are Effective UI Generators](https://www.alphaxiv.org/abs/2604.09577), [Generative Interfaces for LMs](https://arxiv.org/pdf/2508.19227), [Maru](https://arxiv.org/pdf/2608.25565)
- [S] [Imagine with Claude (DataCamp)](https://datacamp.com/tutorial/imagine-with-claude)
- [P] [Genie 3 (DeepMind)](https://deepmind.google/blog/genie-3-a-new-frontier-for-world-models/)
- [S] [Karpathy Software 3.0 (Latent Space)](https://www.latent.space/p/s3)

**LLM agentiques, protocoles, mémoire, voix**
- [S] [OSWorld leaderboard (Steel)](https://leaderboard.steel.dev/leaderboards/osworld/), [Pointer SOTA](https://www.pointer.ai/blog/sota)
- [P] [OSWorld 2.0 (arXiv 2606.29537)](https://huggingface.co/papers/2606.29537), [OSWorld-Human](https://arxiv.org/pdf/2506.16042), [How Benchmarks Mis-Score CUAs](https://arxiv.org/pdf/2607.28367)
- [P] [Qwen-UI-Agent (arXiv 2607.28227)](https://arxiv.org/pdf/2607.28227), [Fara-7B](https://www.microsoft.com/en-us/research/blog/fara-7b-an-efficient-agentic-model-for-computer-use/), [UI-TARS](https://arxiv.org/pdf/2501.12326)
- [P] [ScreenSpot-Pro](https://arxiv.org/abs/2504.07981), [GUI-Eyes](https://arxiv.org/pdf/2601.09770), [GUI-Spotlight](https://arxiv.org/pdf/2510.04039)
- [S] [BFCL v4 (llm-stats)](https://llm-stats.com/benchmarks/bfcl-v4), [BFCL v4 (BenchLM, sept. 2026)](https://benchlm.ai/benchmarks/bfcl-v4)
- [S] [vdf.ai — local LLMs for tool calling](https://vdf.ai/blog/best-local-llm-for-agents-tool-calling/), [promptquorum](https://www.promptquorum.com/local-llms/small-local-llm-models)
- [P] [AAIF — MCP 2026-07-28](https://aaif.io/blog/mcp-2026-07-28-whats-changing-and-how-to-migrate), [MCP is growing up](https://aaif.io/blog/mcp-is-growing-up) · [S] [Protocoles MCP/A2A/ACP](https://zylos.ai/research/2026-03-26-agent-interoperability-protocols-mcp-a2a-acp-convergence/)
- [P] [LongMemEval-V2](https://arxiv.org/pdf/2605.12493), [StreamMemBench](https://arxiv.org/pdf/2606.14571), [MemDelta](https://arxiv.org/pdf/2606.29914) · [S] [Mem0 state of memory](https://mem0.ai/blog/state-of-ai-agent-memory-2026) · [?] [test indépendant](https://dev.to/everest_an/-i-benchmarked-ai-agent-memory-in-2026-and-the-numbers-tell-a-different-story-than-the-marketing-2ae4)
- [P] [NemotronLabs VoiceChat](https://arxiv.org/pdf/2609.21967), [Full-Duplex-Bench-v3](https://arxiv.org/pdf/2604.04847) · [S] [Inworld S2S](https://inworld.ai/resources/best-speech-to-speech-model)

**Sécurité**
- [P] [VPI-Bench](https://arxiv.org/abs/2506.02456), [StepJack](https://arxiv.org/html/2608.06477), [OSGuard](https://arxiv.org/html/2606.15034v1), [Blind spot of agent safety](https://arxiv.org/pdf/2604.10577), [Securing CUAs](https://arxiv.org/pdf/2605.07110)
