# Veille modèles — candidats au cerveau (octobre 2026)

Date : 2026-10-27 (nuit). Méthode : recherche web uniquement, **aucun téléchargement**.
Étiquettes de fiabilité comme dans `state-of-the-art.md` :
- **[P]** source primaire ;
- **[S]** secondaire concordante ;
- **[?]** source unique ou douteuse.

Contexte : le cerveau actuel est Qwen3.5-4B Q4_K_M (3,1 Go de VRAM). Le Qwen3.5-9B Q4_K_M
(même génération, 2× plus gros) n'a apporté aucun gain mesurable sur le banc novice. Un
candidat n'a donc d'intérêt que s'il change vraiment d'échelle ou de génération, dans
6 Go de VRAM et 10 Go de RAM par test.

## 1. Bonsai 2 27B (PrismML), base Qwen3.8-27B — **écarté le 2026-10-28 (trop lent)**
- **Mesuré (2026-10-28)** : cohérent sur la b11887. Sur ce PC, il génère 3,5 à 4,5 tok/s
  (4,2 Go de VRAM, 7,7 Go de RSS). En vérificateur, 132 s par cas, pour 38/66 contre 41 avec
  le Qwen 9B. Le propriétaire l'écarte, comme vérificateur et comme cerveau. Détails :
  `llm/bonsai-2-27b/NOTES.md`.
- Modèle 27B dense, poids ternaires ({−1, 0, +1}, environ 1,7 bit par poids) [P].
- Base : Qwen3.8-27B, une génération plus récente que notre Qwen3.5 [P].
- PrismML annonce qu'il garde 98,2 % de la moyenne de benchmarks du modèle FP16 [P, auto-déclaré].
  Aucun score agent ou appel d'outils publié.
- Fichiers GGUF :
  - `Q2_0`, environ 7,6 Go, dépôt `prism-ml/Ternary-Bonsai-2-27B-gguf-dev`. C'est le seul
    format qui tourne sur le llama.cpp officiel, à partir de la **b11555** d'après la doc
    PrismML [P]. Nous avons la b11887.
  - `PQ2_0` (7,2 Go) et `PTQ1_0` (6,0 Go) : ils demandent les binaires de PrismML (fork) [P].
- Contradiction : la fiche Hugging Face du dépôt `-dev` dit encore que le llama.cpp officiel
  « produit du charabia sans avertissement ». Elle semble antérieure au support upstream
  (PR llama.cpp #29600), mais **il faut le vérifier à l'exécution** : un premier test de
  cohérence des réponses avant tout bench.
- Faisabilité sur notre machine (estimation, non mesurée) :
  - 7,6 Go ne tiennent pas dans 6 Go de VRAM, donc déchargement partiel (environ 60 à 70 %
    des couches sur le GPU, le reste en RAM) ;
  - RSS attendue de l'ordre de 4 à 5 Go, sous la limite de 10 Go ;
  - vitesse inconnue, probablement plusieurs fois plus lent que le 4B ;
  - cache KV FP16 : 64 Kio par jeton, soit 0,5 Go pour notre contexte de 8192.
- Coût : **7,6 Go de budget de téléchargement** (> 2 Go : accord du propriétaire requis).
- Pourquoi c'est la seule piste sérieuse : c'est le premier candidat qui change à la fois
  d'échelle (27B) et de génération (Qwen3.8) tout en restant dans notre matériel.

## 2. Bonsai 2 4B / 9B / 2B (PrismML), base Qwen3.5 — peu d'intérêt pour la qualité
- Mêmes modèles de base que les nôtres, compressés plus fort (4B : 0,95 à 1,15 Go) [P].
- Au mieux une qualité égale à celle de nos Q4_K_M, pour moins de VRAM. Intéressant plus tard
  pour le PC dédié (place pour un second modèle), pas pour la qualité aujourd'hui.

## 3. Bonsai-8B 1 bit (génération 1) — écarté
- 1,15 Go, format Q1_0 [S]. Les sources se contredisent sur le support upstream : plusieurs
  guides disent qu'il faut le fork PrismML [S].
- Sa base n'est pas indiquée dans la doc actuelle. Il est remplacé par Bonsai 2.

## 4. « Qwen3.8-4B-Distill » (empero-ai) — non retenu
- Distillation tierce du grand Qwen3.8 dans l'architecture Qwen3.5-4B ; Q4_K_M environ 2,8 Go [?].
- Chiffres non vérifiés ; la fiche montre un recul sur GSM8K. Il n'existe pas de Qwen3.8
  officiel sous 27B [S].

## 5. Autres
- Agents-A1-4B (juillet 2026), modèle agent dense de 4B [?]. Les poids ne sont publiés qu'au
  format Transformers, sans GGUF officiel ; une conversion serait à faire.
- Aucune autre sortie officielle de petit modèle (≤ 9B) trouvée pour septembre et octobre 2026.

## Mise à jour après la nuit du 27 au 28 octobre
La meilleure configuration mesurée est « le 4B agit, le 9B vérifie et termine » (+2,25 cas
sur 66, p = 0,039). Le rôle de vérificateur change la question : il faut un modèle plus fort
que le 4B, mais il ne sert qu'une fois par tâche.
- Bonsai 2 9B, ternaire, base Qwen3.5-9B, environ 2 à 2,5 Go. Il tiendrait **à côté du 4B**
  dans 6 Go de VRAM, sans échange de modèle. À tester : ne perd-il pas l'avantage du 9B en
  Q4_K_M ? La taille exacte du fichier Q2_0 est à vérifier ; s'il dépasse 2 Go, l'accord du
  propriétaire est nécessaire.
- Bonsai 2 27B comme vérificateur : la lenteur due au déchargement partiel ne pèse que sur le
  tour de vérification.

## Proposition
Test de Bonsai 2 27B en `Q2_0` sur le llama.cpp actuel, en trois étapes, chacune bloquante :
1. contrôle de cohérence (quelques questions, pas de charabia) ;
2. mesure de VRAM, de RSS et de latence avec déchargement partiel ;
3. banc novice v4 sur 3 ordres de cas, comparé au 4B.
Coût : 7,6 Go de budget, sans nouvelle dépendance.

## Liste à tester — tour Hugging Face du 2026-10-30
Méthode : API Hugging Face, sans aucun téléchargement de poids. Deux passes :
- les modèles en tendance ;
- les plus aimés par tâche (génération de texte, vision, ASR, TTS, embeddings, omni), créés
  entre 2025-10 et 2026-10.

Classement du plus récent au plus ancien dans chaque rôle. Les variantes « uncensored » et
« abliterated » et les modèles de plus de 12B sont écartés d'office : ils ne tiennent pas
dans 6 Go. Les scores cités sont **auto-déclarés** par les fiches [P], et aucun n'est mesuré
ici. Tailles des fichiers : arbre du dépôt GGUF, au 2026-10-30.

### A. Cerveau ou vérificateur (le banc novice v4 les départage)
| Priorité | Modèle (date) | GGUF Q4_K_M | llama.cpp | Pourquoi |
|---|---|---|---|---|
| 1 | ~~**Spark-X2.6-4B**~~ (XHToken, 2026-10-19) — **mesuré le 2026-10-30 : 12,5 contre 34,5/66 pour le 4B, écarté** (`llm/spark-x2.6-4b/NOTES.md`) | 3,54 Go, dépôt officiel | upstream ≥ b10828 (nous : b11887) | 4B « agent sur appareil », génération plus récente que Qwen3.5. La fiche dit qu'il égale des 9B en appel d'outils et en planification. Remplaçant direct du 4B à tester. Il fait 0,8 Go de plus que notre 4B : la cohabitation avec Bonsai 2 9B (5804 / 6144 Mio) est douteuse. |
| 2 | **Ornith-1.5-9B** (ornith-ai, 2026-08-18) — **mesuré les 30 et 31/10 : écarté comme vérificateur** (37,5 contre 37,2/66 pour Bonsai 2 9B, mais 1,6× plus lent et souvent sans réponse) ; **en cerveau seul, 37,8 contre 34,5/66 pour le 4B sur 4 ordres, non significatif** (p = 0,65), avec un net gain sur les tâches de connaissance, à 3,2× la latence (`llm/ornith-1.5-9b/NOTES.md`) | 5,78 Go, dépôt officiel | indiqué sur la fiche | Base Qwen3.5 / Gemma 4 + RL agentique. La fiche annonce Terminal-Bench 2.1 46,2 contre 21,3 pour Qwen3.5-9B, et MCP-Atlas 54,2 contre 46,8. Candidat **vérificateur** à la place du Qwen 9B, même empreinte (pas de cohabitation avec le 4B). |
| 3 | **Nanbeige4.2-3B** (2026-07-21) | 2,68 Go (bartowski) | **fork** `Nanbeige/llama.cpp`, branche `nanbeige42` (Looped Transformer) ; support upstream non vérifié | La fiche le place devant Qwen3.5-9B sur les bancs agents : Claw-Eval 52,2 contre 47,1, Terminal-Bench 2.0 44,1 contre 29,2. Petit, donc il pourrait tenir à côté d'un vérificateur. Bloquant : il faut compiler le fork, donc installer le toolkit CUDA (dépendance lourde, accord requis). |
| 4 | Nemotron-3.5-Bolt-E4B (NVIDIA, 2026-10-05) | 6,18 Go (fichier « -4GB ») | conteneur llama.cpp b11459 cité | Post-entraînement de Gemma 4 E4B, qui n'a fait que 16/66 ici. Sa propre table le met **sous** Qwen3.5-4B Q4 en Tau2 (52,3 contre 61,7) et en BFCL (67,3 contre 70,6). Faible priorité. |
| 5 | LFM3-1.7B (Liquid, 2026-10-23) | 1,10 Go | GGUF officiel | Entraîné pour les harnais d'agents, 256K de contexte. La fiche le déconseille elle-même pour le raisonnement multi-étapes. Piste de routeur ou de petit modèle co-résident, pas de cerveau. |

Coût pour les priorités 1 à 3 : 12,0 Go sur les ~20,7 Go restants. Chacun dépasse 2 Go,
donc accord à demander un par un.

### B. Recherche de connaissances et de fichiers (piste n° 3 : lacunes de connaissance)
- **EmbeddingGemma 2** (Google, sorti le 2026-10-06, Apache 2.0). **Mesuré le 2026-10-30, en recherche seule** : hit@10 de 0,44 contre 0,17 pour BM25 sur les demandes novices ; écart non significatif ; le corpus manque de doc Ubuntu (`bench/retrieval/NOTES.md`).
  - 740M paramètres, dont un cœur texte de 270M ; un seul espace pour texte, code, images,
    vidéo et audio ;
  - 768 dimensions (Matryoshka 512 / 256 / 128), 8K de contexte, plus de 100 langues ;
  - MTEB multilingue 61,36 contre 61,15 pour la v1, MTEB code 78,68 contre 68,76 [P].
  - GGUF : `ggml-org/embeddinggemma-2-GGUF` Q8_0, **0,31 Go** pour le texte ; le mmproj des
    autres modalités fait 0,55 Go en plus.
  - llama.cpp : `llama-server --embeddings --pooling mean`, texte et code seulement. Le
    support (PR #30054) a été fusionné le 2026-10-06 et notre b11887 date du 2026-10-25 :
    **il est inclus** (vérifié via l'API GitHub, pas encore à l'exécution).
  - Test proposé, par étapes :
    1. mesurer la recherche seule (BM25 de `docsearch.py` contre recherche hybride) sur des
       requêtes de novice, sur CPU, sans toucher à la VRAM ;
    2. si la recherche progresse nettement, banc novice v4.
  - Garde-fou : les leviers docs (`docs_err`, Arch Wiki) n'ont rien donné. Rien ne dit que
    la qualité de recherche était le goulot.
- Comparateurs du même rôle, à mesurer avec les mêmes requêtes :
  - Qwen3-VL-Embedding-2B (2026-01-07, Apache 2.0) ;
  - WeMM-Embedding-2B (Tencent, 2026-08-25, licence « other »).
- needle3 (Cactus, 2026-09-16, 8 à 29 Mo) : appel d'outils, extraction et embedding sur
  microcontrôleur. Runtime propre (`.cact`), pas llama.cpp. Curiosité, pas prioritaire.

### C. Documents scannés et courriers (cas `scan_to_pdf`, `explain_letter`, `h_find_letter`)
Le banc actuel donne les documents en texte. Ces outils demandent un futur banc avec de
vraies images.
- MiniCPM-OCR-1.0 (OpenBMB, 2026-10-21, Apache 2.0) : 1,3B ; GGUF Q4_K_M 0,53 Go, plus un
  mmproj de 0,90 Go.
- Unlimited-OCR-2 (Baidu, 2026-10-26, MIT) : 3,3B ; GGUF communautaires seulement.
- Nemotron-3.5-Parse (NVIDIA, 2026-09-03) : 0,63B, analyse de mise en page.
- Plus anciens, en référence : PaddleOCR-VL-1.6 (2026-05), DeepSeek-OCR-2 (2026-01),
  LightOnOCR-2-1B (2026-01).

### D. Voix (novices, accessibilité ; aucun banc pour l'instant)
- Reconnaissance vocale :
  - whistle (Cactus, 2026-09-30, 16,9 Mo, 7 langues) ;
  - nemotron-3.5-asr-streaming-0.6b (2026-05) ;
  - Qwen3-ASR-0.6B (2026-01) ;
  - granite-speech-5.0-2b (2026-10-07).
- Synthèse vocale :
  - kitten-tts-2 (2026-09-30) ;
  - supertonic-3 (2026-05) ;
  - phonon-40m-multilingual (2026-10-19, licence **CC-BY-NC**).
- Voix vers voix : LFM3-Omni-2B (2026-10-21, licence LFM) ; licence à vérifier pour un
  produit.

### E. Canal écran (piste « arbre d'accessibilité contre vision de l'écran »)
- WeVisOne-VL-4B (Tencent, 2026-10-22, Apache 2.0) : GGUF communautaires.
- LocateAnything-3B (NVIDIA, 2026-03-02) : localiser un élément d'interface.
- Fara-7B (Microsoft, 2025-10-30, MIT) : agent qui pilote l'ordinateur ; 8,3B, juste en 6 Go.

### F. Vus et écartés
- Trop gros pour 6 Go : Sage-A1.5 (36B MoE, le successeur d'Agents-A1), MemT-1.0-Nano (35B),
  Raon-1-mini (29B), Qwen3.8-Flash-Next et les autres MoE de plus de 30B.
- Hors sujet ou démonstrations :
  - Qwen-Drive-1.0-4B (conduite autonome) ;
  - Qwenputer (calcul exact uniquement) ;
  - HobbyLM-1B computer use (Mac / MLX seulement).
- Plus ancien, le même rôle déjà couvert : functiongemma-270m (2025-10, accès manuel) ;
  il fait doublon avec LFM3-1.7B et needle3.

## Sources
- Tour HF 2026-10-30 : `https://huggingface.co/api/models?sort=trendingScore` et
  `?sort=likes&pipeline_tag=…`, plus les fiches de :
  - https://huggingface.co/google/embeddinggemma-2
  - https://huggingface.co/ggml-org/embeddinggemma-2-GGUF
  - https://unsloth.ai/docs/models/embeddinggemma-2
  - https://huggingface.co/XHToken/Spark-X2.6-4B
  - https://huggingface.co/ornith-ai/Ornith-1.5-9B
  - https://huggingface.co/Nanbeige/Nanbeige4.2-3B
  - https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-4GB
  - https://huggingface.co/LiquidAI/LFM3-1.7B
  - https://huggingface.co/openbmb/MiniCPM-OCR-1.0
  - https://huggingface.co/baidu/Unlimited-OCR-2
  - https://huggingface.co/Cactus-Compute/needle3
- https://docs.prismml.com/models/bonsai-8b (lignée Bonsai 2, tailles, bases)
- https://docs.prismml.com/run/llamacpp (b11555 et plus, Q2_0 sur l'officiel)
- https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf-dev (Q2_0, 7,63 Go, avertissement)
- https://github.com/ggml-org/llama.cpp/pull/29600 (support runtime upstream)
- https://huggingface.co/prism-ml/Bonsai-8B-gguf, https://github.com/Mintplex-Labs/prism-ml-llama.cpp
- https://huggingface.co/empero-ai/Qwen3.8-4B-Distill-GGUF, https://unsloth.ai/docs/models/qwen3.8
- https://huggingface.co/InternScience/Agents-A1-4B-Q4_K_M-GGUF
