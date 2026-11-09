# Taxonomie des tâches sur PC — carte de couverture de weaver

Date : 2026-10-26. Ce document sert de référence pour le principe 1 du README (« toutes les
tâches »). Il sert à trois choses :
- choisir quoi explorer ;
- construire les benchs ;
- décider du signal de prototype.

À mettre à jour à chaque nouvelle mesure.

## 1. Cadre

### Les trois degrés de la fracture numérique
- **1er degré : l'accès** (matériel, connexion). Hors périmètre logiciel.
- **2e degré : les compétences et les usages** (savoir faire).
- **3e degré : les résultats tangibles** qu'on obtient hors ligne grâce au numérique (argent,
  droits, liens sociaux, santé, emploi). Van Deursen et Helsper (2015) montrent que ces gains
  profitent surtout aux plus favorisés, même à usage égal. Les écarts hors ligne peuvent donc
  se creuser.

**Conséquence pour weaver.** Une tâche n'est pas « réussie » parce que les bons clics ont été
faits. Elle l'est quand **le résultat est obtenu** : la démarche aboutie, le remboursement
reçu, la photo arrivée chez le destinataire. Les benchs doivent tester des résultats.

### Ordres de grandeur (pourquoi ça compte)
- France, 2025 : **34 %** des 16-74 ans n'utilisent pas Internet, ou n'ont pas les bases dans
  au moins un des 5 domaines de compétences. **7 %** sont en illectronisme (Insee Focus 376).
- France, 2024 : **31 %** des 60-74 ans renoncent à des démarches en ligne, contre 21 % des
  30-44 ans (Insee, *Économie et société à l'ère du numérique 2025*).
- France : **82 %** des démarches administratives se font en ligne, soit 572 millions par an
  (Banque des Territoires, 2025).
- UE, 2025 :
  - 60,4 % des 16-74 ans ont au moins les compétences numériques de base (objectif 2030 : 80 %) ;
  - parmi les internautes, 87 % utilisent l'e-mail et 74 % la banque en ligne ;
  - 38 % déclarent leurs impôts en ligne (Eurostat).

### Croisement avec les référentiels de compétences
DigComp 3.0 (Commission européenne, novembre 2025) garde 5 domaines et 21 compétences, avec
l'IA intégrée partout :
1. information ;
2. communication et collaboration ;
3. création de contenu ;
4. sécurité, bien-être et usage responsable ;
5. résolution de problèmes.

Pix (France) s'en inspire. Chaque famille de tâches ci-dessous indique les domaines DigComp
qu'elle mobilise (D1 à D5) : ce sont les compétences que weaver doit **rendre inutiles** pour
l'utilisateur.

## 2. Axes de classement

| Axe | Valeurs |
|---|---|
| **Risque** | **R0** lecture seule · **R1** modification réversible (corbeille, instantané) · **R2** destruction ou écrasement local · **R3** **effet hors du PC, irréversible** (envoyer, payer, signer, soumettre un formulaire, publier) |
| **Confidentialité** | **C0** publique · **C1** personnelle · **C2** sensible (identité, santé, finances, documents officiels) |
| **Canal d'action** (du plus simple au plus lourd) | **API** : CLI, bibliothèque, protocole standard (IMAP, CalDAV, CUPS…) · **MCP** : serveur d'outils existant · **A11Y** : arbre d'accessibilité (AT-SPI) · **WEB** : DOM / arbre d'accessibilité du navigateur · **VIS** : capture d'écran + modèle de vision · **REW** : réécrire l'outil pour weaver |
| **Hors ligne** | **oui** / **partiel** / **non** (le service distant est nécessaire, mais l'agent reste local) |

**Constat clé : R3 n'est couvert par aucune protection actuelle.** La corbeille et la
confirmation imposée protègent les *données locales*. Un e-mail envoyé, un paiement ou un
formulaire soumis **ne se mettent pas à la corbeille**. Le verrou de confirmation doit donc
être étendu à toute action R3, avec un récapitulatif rédigé par le verrou et non par le
modèle. Pour l'e-mail, on peut aussi prévoir un délai d'annulation de quelques secondes,
comme le font certains webmails.

## 3. Taxonomie

Les colonnes « Canaux » vont du canal à essayer en premier au repli. « Bench » donne la
couverture actuelle : `—` aucune, `◐` partielle ou simulée, `●` réelle.

### A. Système et maintenance (D5)
| Famille | Exemples de demandes de novice | Risque | Conf. | Canaux | Hors ligne | Bench |
|---|---|---|---|---|---|---|
| Diagnostic | « mon ordi rame », « il fait du bruit », « plus de place » | R0→R1 | C0 | API (`top`, `df`, `journalctl`) | oui | ◐ (état simulé) |
| Réseau | « internet ne marche plus », « connecte-moi au wifi de la box » | R1 | C1 | API (`nmcli`) | partiel | — |
| Son, écran, périphériques | « je n'ai plus de son », « l'écran est trop petit », « ma souris bluetooth » | R1 | C0 | API (`pactl`, `wlr-randr`/`gsettings`, `bluetoothctl`) | oui | — |
| Impression, numérisation | « imprime ça en recto verso », « scanne ce document en PDF » | R0/R1 | C1 | API (CUPS `lp`, SANE `scanimage`) | oui | — |
| Logiciels | « installe un truc pour faire des montages vidéo », « désinstalle ça » | R1 | C0 | API (`flatpak`, `apt`/`dnf`) | non (installation) | — |
| Mises à jour | « fais les mises à jour sans rien casser » | R1 si instantané, sinon R2 | C0 | API + **instantanés système** | non | — |
| Sauvegarde, restauration | « sauvegarde mes photos sur la clé », « j'ai effacé un fichier hier » | R1 | C1 | API (`rsync`, instantanés, corbeille) | oui | ◐ (corbeille) |
| Comptes, mots de passe | « j'ai oublié mon mot de passe Gmail » | R3 | C2 | WEB + gestionnaire de mots de passe | non | — |

### B. Fichiers et organisation (D1, D5)
| Famille | Exemples | Risque | Conf. | Canaux | Hors ligne | Bench |
|---|---|---|---|---|---|---|
| Trouver | « où est la lettre que j'ai écrite à la mairie ? » | R0 | C1 | API (recherche plein texte, index sémantique) | oui | ● |
| Ranger, renommer | « range mes téléchargements » | R1 | C1 | API | oui | ● |
| Convertir | « transforme ça en PDF », « cette photo est trop lourde pour le mail » | R1 | C1 | API (LibreOffice sans interface, ImageMagick, ffmpeg) | oui | — |
| Compresser, partager | « envoie ce dossier à Paul » | R1 / R3 (envoi) | C1 | API + C | partiel | ◐ |
| Supprimer, récupérer | « vide les vieux fichiers », « récupère ce que j'ai effacé » | R2→R1 | C1 | API + corbeille | oui | ● |
| Téléphone ↔ PC | « mets les photos de mon téléphone sur l'ordi » | R1 | C1 | API (MTP/`gio`, KDE Connect) | oui | — |

### C. Communication (D2)
| Famille | Exemples | Risque | Conf. | Canaux | Hors ligne | Bench |
|---|---|---|---|---|---|---|
| E-mail | « réponds à la mairie que je suis d'accord », « mets la facture en pièce jointe » | **R3** (envoi) | C1/C2 | API (IMAP/SMTP) → A11Y (Thunderbird) → WEB (webmail) | partiel (brouillons hors ligne) | — |
| Tri, spam, arnaques | « c'est vrai ce mail de la banque ? » | R0 | C2 | API + jugement du modèle | oui | — |
| Messagerie | « envoie un message à ma fille sur WhatsApp » | R3 | C1 | WEB (WhatsApp Web) → VIS ; API (Signal en CLI) | non | — |
| Appel vidéo | « appelle ma petite-fille en visio », « on ne m'entend pas » | R3 | C1 | WEB / VIS + API (son, caméra) | non | — |
| Agenda, contacts | « rappelle-moi le dentiste », « ajoute ce numéro » | R1 | C1 | API (ICS/CalDAV, vCard) | oui | ◐ (rappels simulés) |

### D. Documents et bureautique (D3)
| Famille | Exemples | Risque | Conf. | Canaux | Hors ligne | Bench |
|---|---|---|---|---|---|---|
| Écrire un courrier, un CV | « écris une lettre de résiliation pour mon assurance » | R1 | C1/C2 | API (génération en ODT/DOCX) → A11Y (LibreOffice) | oui | — |
| Tableur, budget | « fais-moi un tableau de mes dépenses du mois » | R1 | C2 | API (ODS/XLSX) → A11Y | oui | — |
| PDF | « remplis ce formulaire PDF », « signe et renvoie », « fusionne ces scans » | R1 / R3 (envoi) | C2 | API (pypdf, qpdf, ocrmypdf) | oui | — |
| Présentations | « fais 5 diapos pour la réunion du club » | R1 | C1 | API → A11Y | oui | — |

### E. Information et web (D1, D4)
| Famille | Exemples | Risque | Conf. | Canaux | Hors ligne | Bench |
|---|---|---|---|---|---|---|
| Recherche | « quels sont les horaires de la piscine ? » | R0 | C0 | WEB (recherche, lecture de pages) | non | ◐ (simulé) |
| Vérifier une info | « c'est vrai cette histoire sur Facebook ? » | R0 | C0 | WEB + croisement des sources | non | — |
| Résumer, traduire, expliquer | « explique-moi ce courrier des impôts » | R0 | C2 | modèle local | oui | — |

### F. Démarches et services en ligne — le cœur du 3e degré (D1, D2, D4, D5)
| Famille | Exemples | Risque | Conf. | Canaux | Hors ligne | Bench |
|---|---|---|---|---|---|---|
| Administration (impots.gouv, CAF, Ameli, France Travail, ANTS) | « déclare mes revenus », « fais ma demande de prime d'activité », « mon attestation de droits » | **R3** | **C2** | WEB (DOM + accessibilité) → VIS ; FranceConnect | non | — |
| Santé | « prends-moi rendez-vous chez un dentiste jeudi » | R3 | C2 | WEB (Doctolib) | non | — |
| Banque, assurance, énergie | « combien il me reste sur mon compte ? », « envoie mon relevé de compteur » | R0 / **R3** | C2 | WEB → VIS (souvent sur appli mobile) | non | — |
| Colis, transport | « où est mon colis ? », « réserve un train pour Lyon » | R0 / R3 | C1 | WEB | non | — |

Obstacles propres à cette famille :
- identifiants, double authentification et FranceConnect : l'agent ne doit jamais voir un
  mot de passe en clair, il passe par un gestionnaire ;
- CAPTCHA ;
- téléversement de pièces justificatives ;
- sites qui changent sans prévenir ;
- **impossibilité de tester sur les vrais sites.** Il faut des **répliques locales de
  portails fictifs**, comme le fait WebArena.

### G. Commerce et argent (D1, D4)
| Famille | Exemples | Risque | Conf. | Canaux | Hors ligne | Bench |
|---|---|---|---|---|---|---|
| Acheter, comparer | « trouve-moi une bouilloire pas chère et solide » | R0 → **R3** (payer) | C2 (paiement) | WEB | non | — |
| Vendre (Leboncoin…) | « mets mon vélo en vente » | R3 | C1 | WEB | non | — |
| Budget | « combien j'ai dépensé en courses ce mois-ci ? » | R0 | C2 | API (relevés CSV/PDF) | oui | — |

### H. Médias et loisirs (D3)
| Famille | Exemples | Risque | Conf. | Canaux | Hors ligne | Bench |
|---|---|---|---|---|---|---|
| Photos | « trie les photos de Noël », « fais un album pour mamie », « retouche cette photo floue » | R1 | C1 | API (EXIF, ImageMagick) + vision (contenu des photos) | oui | ◐ (archive) |
| Musique, vidéo, streaming | « mets de la musique calme », « regarde ce film sur la télé » | R0 | C0 | API (MPRIS, `mpv`) → WEB | partiel | ◐ (ouvrir une app) |
| Jeux | « installe ce jeu que mon petit-fils veut » | R1 | C0 | API (Steam/Lutris) → VIS | non | — |
| Lecture | « lis-moi ce livre », « agrandis le texte » | R0 | C0 | API (synthèse vocale) | oui | — |

### I. Création (D3)
Retouche (GIMP), montage vidéo (Kdenlive), audio, site web, publication sur les réseaux
sociaux (R3). Canaux : API (ffmpeg, ImageMagick, scripts GIMP) → A11Y → VIS ; c'est le
domaine où **réécrire** (REW) des outils plus simples pilotés par l'agent a le plus de sens.

### J. Travail et métier (les associés)
Code, analyse de données, CRM, facturation, comptabilité. Canaux : API / MCP (riche), WEB pour
les outils SaaS. À préciser selon les métiers des associés.

### K. Sécurité et vie privée (D4) — transversal
| Famille | Exemples | Risque | Conf. | Canaux | Bench |
|---|---|---|---|---|---|
| Arnaques, hameçonnage | « on m'appelle de la part de Microsoft », « ce SMS du colis » | R0 | C2 | modèle + règles | — |
| Injection visant l'agent | contenu piégé dans un fichier ou une page web | — | — | politique + verrou | ● (2 cas) |
| Mots de passe, 2FA | « mets un mot de passe solide partout » | R3 | C2 | gestionnaire (KeePassXC, Bitwarden) | — |
| Contrôle parental, confidentialité | « mon petit-fils ne doit pas aller sur n'importe quoi » | R1 | C1 | API (filtres DNS, comptes) | — |

### L. Apprendre et se faire aider (D1, D5) — transversal
« explique-moi ce que tu viens de faire », « apprends-moi à le faire moi-même »,
accessibilité (zoom, lecture à voix haute, contraste). C'est le levier d'*autonomie* : on
veut supprimer la fracture, pas seulement la contourner.

## 4. Lecture transversale

1. **Linux est un atout pour le canal le plus simple.** Une grande partie de A, B, D et H se
   pilote par **API/CLI standard** (`nmcli`, `pactl`, CUPS, SANE, `flatpak`, LibreOffice
   sans interface, ffmpeg, ImageMagick…), sans modèle de vision. C'est le principe « outil
   simple d'abord » : sous Windows, une bonne part passerait par l'UI.
2. **Le web (F, G, C, E) est le canal le plus important pour le 3e degré**, et le plus risqué
   (R3 + C2). Il demande :
   - un pilotage du navigateur par le DOM et l'accessibilité, avec la vision en repli ;
   - des répliques locales de sites pour tester ;
   - le verrou R3.
3. **La vision d'écran (VIS) est le filet universel**, mais c'est le plus lent et le plus
   fragile. Elle sert pour les jeux, les apps Electron mal accessibles, les apps Windows sous
   Wine. À mesurer *contre* A11Y et WEB sur les mêmes tâches.
4. **La réécriture d'outils (REW)** se justifie là où aucun canal n'est fiable, ou bien là
   où l'outil existant impose une courbe d'apprentissage que l'agent ne peut pas absorber.
   Les candidats naturels : la création (I) et certains usages de D.
5. **Hors ligne.** A, B, D, H, L et l'analyse dans C, E, G fonctionnent entièrement hors
   ligne avec un modèle local. F et G ne peuvent pas, par nature : le service est distant.
   Le cerveau, lui, reste local.

## 5. Couverture actuelle du bench (v3)

Couvert de façon réelle : B (trouver, ranger, supprimer, récupérer), K (injection).
Partiellement, et seulement de façon simulée : A (diagnostic), C (rappels), E (recherche),
H (archive, ouvrir une app).
**Rien** en C (e-mail, messagerie), D, F, G, I, J, ni sur les actions R3.

Les demandes du bench v3 sont formulées comme par un utilisateur qui connaît les chemins
(`~/photos`). **Aucune n'est formulée comme par un novice.**

**Mise à jour du 2026-10-26 — bench novice v3** (`bench/agent/cases_novice.json`, machine
simulée, 18 cas formulés comme par un novice) :
- **A** (diagnostic, son, réseau, impression, numérisation, logiciels, mises à jour,
  affichage, bluetooth) : ◐ simulé.
- **B** (trouver, disque plein) : ◐.
- **D** (PDF, conversion, courrier, image) : ◐.

Meilleur résultat obtenu : **10/18** (Qwen3.5-4B). Aucun modèle ne réussit l'impression recto
verso, l'instantané avant les mises à jour ni le déblocage de l'imprimante : ce sont des
lacunes de connaissance. Les familles C, E à L restent à couvrir.

**Mise à jour du 2026-10-27 — bench novice v4** (`bench/agent/cases_novice_v4.json`) :
22 tâches × 3 formulations (celle de v3, une version tapée vite sans accents, une version
bavarde avec des détails inutiles), soit 66 cas. Quatre tâches nouvelles :
- désinstaller un jeu (A) ;
- expliquer un avis d'impôt fictif (L, ◐ : un document local, sans web) ;
- grossir le pointeur de la souris (A, accessibilité) ;
- reconnaître un faux mail de banque (K, ◐ : le mail est un fichier, il n'y a pas encore de
  vraie messagerie).

Fiabilité du Qwen3.5-4B : **36/66 cas** (dev 20/39, holdout 16/27, soit 59 %, loin du seuil
de 80 % de la section 7).
- 7 tâches sur 22 sont réussies quelle que soit la formulation : réseau, wifi, taille du
  texte, CV en PDF, lettre de résiliation, photo trop lourde, faux mail.
- 9 dépendent de la formulation ; la version tapée vite coûte 1 à 3 cas.
- 6 ne sont jamais réussies : mises à jour sûres, imprimante bloquée, recto verso,
  désinstallation, numérisation, son.
- Par famille : C/K/L (faux mail, explication, lettre) 1,00 ; D (documents) 0,72 ;
  A système 0,42 (son 0,17 ; impression, numérisation, mises à jour 0).
- Ni le 9B, ni l'Arch Wiki hors ligne, ni la doc poussée sur erreur ne font mieux de façon
  mesurable.

## 6. Priorités proposées

Score = besoin (fréquence × douleur de la fracture) × faisabilité sur la machine de dev.

| Priorité | Familles | Pourquoi | Ce qu'il faut construire |
|---|---|---|---|
| 1 | **A** diagnostic, réseau, son, impression · **B** · **D** PDF et courrier | Très fréquent, forte douleur, faisable par API sous Linux, testable hors ligne | Outils API + cas novices ; environnement Linux de test pour le système (conteneur ou VM) |
| 2 | **C** e-mail · **K** arnaques · **verrou R3** | 87 % des internautes utilisent l'e-mail ; l'arnaque est la peur n° 1 des novices ; premier cas R3 | Serveur IMAP/SMTP local fictif ; boîte de test avec des vrais et des faux mails |
| 3 | **F** démarches · **G** achats | Cœur du 3e degré, mais le plus difficile | Répliques locales de portails fictifs (impôts, CAF, Doctolib) ; canal WEB (DOM/accessibilité vs vision) |
| 4 | **H** photos (vision) · **L** expliquer, apprendre | Fréquent et valorisant ; réutilise la vision de Qwen3.5 | Cas avec images |
| 5 | **I**, **J**, jeux | Moins liés à la fracture ; plus lourds | Plus tard |

## 7. Proposition de signal pour le prototype (à discuter)

Monter le prototype quand **toutes** ces conditions sont réunies :
1. Bench novice : au moins 80 % de résultats obtenus dans chaque famille de priorité 1 et 2,
   sur les cas réservés.
2. **Zéro perte de données et zéro action R3 sans accord**, garantis par construction et
   vérifiés par le selftest.
3. Latence acceptable pour un novice : à mesurer, par exemple moins de 10 s par demande
   simple.
4. Comparaison favorable à une **référence humaine** (toi ou des associés, chronométrés sur
   un sous-ensemble).
5. Une configuration matérielle chiffrée (VRAM, RAM) tirée des mesures. Elle servira pour
   l'achat du PC.

## Sources
- [Van Deursen & Helsper (2015), *The third-level digital divide: who benefits most from being online?*](https://researchonline.lse.ac.uk/id/eprint/65143)
- [Scheerder, van Deursen & van Dijk, revue systématique des 2e et 3e degrés](https://research-portal.uu.nl/en/publications/determinants-of-internet-skills-uses-and-outcomes-a-systematic-re/)
- [Insee Focus n°376 — Une personne sur trois manque de compétences numériques (2025)](https://www.insee.fr/fr/statistiques/8739245)
- [Insee — Économie et société à l'ère du numérique, édition 2025](https://www.insee.fr/fr/statistiques/fichier/8616863/NUM25-VE.pdf)
- [Banque des Territoires — dématérialisation et illectronisme (2025)](https://www.banquedesterritoires.fr/dematerialisation-des-services-publics-lillectronisme-nest-pas-voue-disparaitre)
- [Eurostat — Digitalisation in Europe 2026](https://ec.europa.eu/eurostat/web/interactive-publications/digitalisation-2026), [statistiques régionales](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Digital_society_statistics_at_regional_level)
- [JRC — DigComp 3.0 (novembre 2025)](https://joint-research-centre.ec.europa.eu/jrc-news-and-updates/european-commission-updates-its-digital-competence-framework-digcomp-2025-11-27_en), [résumé CEPIS](https://cepis.org/digcomp-3-0-launches/)
- [Windows Agent Arena (ICML 2025)](https://proceedings.mlr.press/v267/bonatti25a.html) ; domaines d'OSWorld (OS, bureautique, navigateur, e-mail, médias, outils pro, flux multi-apps) de mémoire, d'après le papier original de 2024
