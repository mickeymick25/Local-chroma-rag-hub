# Suivi d'implémentation : extension multi-projets, phase 1

## Objet et méthode

Ce document suit l'implémentation de la phase 1 de la spécification
multi-projets. Il est la référence du déroulement : chaque étape est
définie avec ses critères d'acceptation, exécutée une seule à la fois,
puis marquée. Toute anomalie constatée arrête l'exécution et se règle
avant de continuer. Le statut de chaque étape est tenu à jour dans ce
fichier jusqu'à la clôture de la phase.

## Périmètre

Inclus : l'outillage du hub — script d'instanciation et gabarit de
section AGENTS.md —, les ajustements de la spécification, et la
validation complète du protocole sur un projet de test jetable.

Exclus : tout pilote réel, le projet pilote reste en phase 2 ; les autres projets
du portefeuille ; une éventuelle CLI rag, le rag init ou le rag doctor ;
l'automatisation Git de la réindexation ; la mémoire globale ; la
migration des collections du hub, qui reste le laboratoire de référence.

## Livrables

- docs/specs/multi-projets.md, spécification corrigée : terminologie
  multi-collection plutôt que multi-tenant, manifeste versionné sans
  chemin absolu ;
- index-project.sh, script d'instanciation à la racine du hub ;
- templates/AGENTS-rag-section.md, gabarit de section de routage ;
- la fixture de test sous tests/fixtures/multi-project/,
  explicitement identifiable comme fixture — dossier avec docs/,
  memory/ et AGENTS.md ;
- ce document, tenu à jour jusqu'à clôture.

## Le script d'instanciation

Trois responsabilités strictement séparées, dans cet ordre.

1. Identité : lire le manifeste .rag.yaml à la racine du projet s'il
   existe, sinon le créer — version du manifeste et slug dérivé du nom
   de dossier, minuscules, accents translittérés, bornes
   alphanumériques, trois à soixante-trois caractères au total ; refuser
   toute collision de slug entre chemins avec, en proposition de repli,
   le slug déterministe dérivé du chemin canonique — slug, double
   tiret, hachage court du chemin. Si le manifeste existe, le slug
   n'est jamais recalculé depuis le dossier : le script vérifie à
   chaque exécution que le slug du manifeste est syntaxiquement valide
   et que les collections correspondantes sont cohérentes — existantes
   et réutilisées en incrémental, ou créées à l'indexation.
2. Préparation : vérifier le dossier docs, exigé, et le dossier
      memory, proprement ignoré s'il est absent, et insérer la
      section de routage dans le AGENTS.md du projet depuis le gabarit,
      avec le slug substitué, de façon idempotente — la section n'est
      jamais dupliquée.
3. Indexation : lancer l'indexeur de connaissances puis l'indexeur de
   mémoires par docker run direct sur l'image du hub, réseau chroma-net,
   collections slug suivi de knowledge puis slug suivi de memories. Le
   docker run direct est imposé : les services compose du hub montent
   leur propre dossier docs en dur, et les montages de ligne de commande
   s'ajoutent sans remplacer.

La sortie opérationnelle affiche le projet, son chemin, son slug, ses
collections, la présence des dossiers docs et memory, le modèle
d'embedding et sa dimension, puis le déroulement des deux indexations,
et termine par la confirmation d'instanciation.

## Le gabarit de section AGENTS.md

Le gabarit templates/AGENTS-rag-section.md suit le texte de la
spécification : désignation nominative des deux collections,
exclusivité de routage, interdiction des collections d'autres projets
sans demande explicite, rappel du workflow mémoire avec validation
humaine, et commande de réindexation du hub. Le slug y figure comme
variable substituée par le script à l'insertion.

## La fixture de test

La fixture de test vit sous tests/fixtures/multi-project/ au sein du
hub : un dossier explicitement identifiable comme fixture, distinct de
tout projet réel, contenant un corpus docs minimal mais réel — quelques
documents sur des sujets distinctifs —, un dossier memory avec deux ou
trois entrées atomiques au format du hub, et un AGENTS.md. Elle sert de
support aux dix propriétés de validation et reste conservée ensuite
comme fixture de régression.

## Protocole de validation

Dix propriétés, vérifiées dans l'ordre sur la fixture de test, toutes
évaluées dans le même protocole, avec le même état initial et les mêmes
critères. Une propriété non satisfaite bloque la phase. Chaque constat
suit le format : précondition, action, résultat observé, critère PASS
ou FAIL, preuve ou mesure, constat éventuel.

1. Première indexation : les deux collections sont créées et peuplées.
2. Idempotence : une deuxième exécution du script n'écrit rien.
3. Granularité : modifier un seul document ne réindexe que ses chunks —
   identifiants et chunks des autres documents inchangés, vérifiés
   avant et après.
4. Purge : supprimer un document retire tous ses chunks — disparition
   complète vérifiée.
5. Création d'un nouveau projet : l'instanciation d'un second projet
   crée ses collections propres.
6. Isolation entre projets : les deux projets possèdent des collections
   distinctes et leurs contenus ne se mélangent pas.
7. Intégrité de la production : les collections project_knowledge et
   memories du hub ne changent pas d'un seul chunk — comptes et
   identifiants relevés avant et après, comparaison objective.
8. Identité : renommer physiquement le dossier puis réexécuter — le
   slug reste celui du manifeste et le registre suit le chemin canonique
   attendu.
9. Collision : un projet homonyme est refusé nettement avec repli
   canonique déterministe, sans création de collection.
10. Persistance : détruire et recréer uniquement le conteneur de base
    du hub, puis vérifier la présence des collections et leur capacité
    de requête.

## Étapes

- [x] Étape 1 — Ajustements de la spécification : terminologie
      multi-collection, manifeste portable versionné. Validée le
      2026-09-07 avec les corrections éditoriales du document de
      suivi.
- [x] Étape 2 — Script index-project.sh : écriture complète, puis
      exécutions à vide — sans argument, sur un chemin inexistant, sur
      un dossier sans docs — chaque erreur doit être propre et sans
      effet de bord : aucune invocation invalide ne crée de .rag.yaml,
      ne modifie de AGENTS.md, ni ne crée de collection ; le critère
      est vérifié explicitement après chaque échec. Exécutée puis
      validée le 2026-09-07.
- [x] Étape 3 — Gabarit templates/AGENTS-rag-section.md : rédaction et
      relecture contre la spécification. Exécutée puis validée le
      2026-09-07 : rendu avec slug substitué identique au gabarit de la
      spécification, une ligne ajoutée par excès (règle d'or) retirée
      pour conformité stricte.
- [x] Étape 4 — Fixture de test : création du dossier, du corpus, des
      mémoires et du AGENTS.md, puis instanciation complète par le
      script. Exécutée le 2026-09-07 : chaîne complète vérifiée
      (manifeste, identité, section AGENTS.md, registre, deux
      collections) ; deux observations non bloquantes consignées en
      constats, corrigées en correctif validé de l'étape. Exécutée
      puis validée le 2026-09-07.
- [x] Étape 5 — Protocole de validation : les dix propriétés, une par
      une, chaque constat consigné dans ce document. Exécutée du
      2026-09-07 : dix PASS définitifs, deux FAIL historiques
      (propriétés 2 et 8) conservés en trace avec leurs correctifs
      démontrés par re-test.
- [x] Étape 6 — Clôture : synthèse des constats, mise à jour finale
      de ce document, revue Git finale, commit de la phase.

## Constats

Étape 2 — exécutions à vide, 2026-09-07 :

- sans argument : usage affiché, sortie en échec, aucun effet ;
- chemin inexistant : erreur explicite, aucun effet ;
- dossier sans docs/ : slug correctement dérivé, puis erreur explicite
  sur le dossier manquant, aucun effet ;
- vérifications après échec : dossier cible vide, aucun manifeste
  .rag.yaml, aucun AGENTS.md, registre du hub absent — le critère
  d'absence d'effet de bord est satisfait pour les trois cas.

Les constats de l'étape 5 suivent, une entrée par propriété, au format
convenu : précondition, action, résultat observé, critère PASS ou FAIL,
preuve ou mesure, constat éventuel.

Étape 4 — première instanciation réelle, 2026-09-07 :

- une commande unique a enchaîné les trois responsabilités et indexé
  les deux collections (2 chunks knowledge, 2 entrées memories) ;
- manifeste .rag.yaml conforme (manifest_version 1, slug dérivé) ;
- section RAG insérée dans AGENTS.md avec slug substitué ;
- registre du hub peuplé (slug, chemin canonique) ;
- observation 1, non bloquante : la ligne d'état des collections
  n'affiche rien — le docker run du contrôle ne transmet pas son
  entrée standard (drapeau -i manquant) ;
- observation 2, non bloquante : la section AGENTS.md est collée au
  contenu existant sans ligne vide — l'ajout suppose un saut de ligne
  final dans le fichier cible ;
- aucune correction appliquée à ce stade, conformément à la méthode :
  comportement réel observé d'abord, décisions ensuite.

Correctif de l'étape 4, 2026-09-07, validé humain :

- correctif 1 : drapeau -i ajouté au docker run du contrôle d'état ;
- correctif 2 : normalisation minimale avant l'ajout — saut de ligne
  final garanti au fichier existant, puis ligne vide de séparation,
  sans autre réécriture ;
- contrôle ciblé : le contrôle d'état affiche les deux collections,
  existantes avec leurs compteurs ; la jonction AGENTS.md présente
  la séparation attendue, contenu existant puis ligne vide puis
  section ; la deuxième exécution saute l'insertion (section déjà
  présente, et n'écrit rien dans les indexeurs — idempotence
  confirmée sur toute la chaîne.

Propriété 1 — première indexation, 2026-09-07 :

- précondition : état initial propre — collections de la fixture
  supprimées, manifeste .rag.yaml retiré, section RAG retirée du
  AGENTS.md, registre du hub absent ; la base ne contient que les deux
  collections du hub, project_knowledge et memories ;
- action : ./index-project.sh tests/fixtures/multi-project/ ;
- résultat observé : slug dérivé du dossier, contrôle d'état annonçant
  « à créer » pour les deux collections, section AGENTS.md insérée
  avec séparation correcte, manifeste créé, registre peuplé, collection
  knowledge créée avec EF ollama/bge-m3 et 2 chunks écrits en 1024
  dimensions, collection memories créée avec 2 entrées ;
- critère : PASS ;
- preuve : comptes relevés par MCP après exécution —
  multi-project__knowledge à 2, multi-project__memories à 2 ; manifeste
  conforme (manifest_version 1, slug multi-project) ; registre à une
  entrée (slug, chemin canonique) ; jonction AGENTS.md séparée par
  ligne vide ; durées 3,4 s et 2,8 s ;
- constat : la chaîne complète s'exécute en une commande depuis l'état
  vierge ; le contrôle d'état, corrigé à l'étape 4, annonce correctement
  « à créer » avant la création.

Propriété 2 — idempotence, 2026-09-07 :

- précondition : état issu de la propriété 1 — comptes 2 et 2 relevés
  par MCP, empreintes relevées pour le manifeste, le AGENTS.md et le
  registre, section RAG unique dans AGENTS.md (26 lignes, une
  occurrence) ;
- action : deuxième exécution du script sur la fixture ;
- résultat observé : slug repris du manifeste, contrôle d'état
  annonçant les deux collections existantes, section RAG non
  retouchée, aucun chunk ni entrée écrits par les indexeurs (0,1 s
  chacun), manifeste et AGENTS.md aux empreintes identiques — mais
  registre réécrit avec une empreinte différente ;
- critère : FAIL — le registre ne reste pas cohérent ;
- preuve : comparaison des empreintes avant/après — manifeste et
  AGENTS.md identiques, registre changé ; inspection octet par octet :
  le séparateur tabulation du registre a été remplacé par une espace
  lors de la réécriture ; simulation de la recherche de registre : le
  slug n'est plus trouvé, donc toute détection de collision future
  serait silencieusement inopérante ;
- constat : cause identifiée — dans la mise à jour du registre, le
  awk imprime les champs avec le séparateur de sortie par défaut
  (espace) alors que la recherche découpe sur la tabulation ;
  correctif proposé : fixer le séparateur de sortie à la tabulation
  dans la mise à jour du registre, ce qui répare le registre au
  prochain passage. Aucune correction appliquée à ce stade,
  conformément à la méthode — décision humaine attendue.

Correctif de la propriété 2, 2026-09-07, validé humain :

- correctif : BEGIN { OFS = "\t" } ajouté à la mise à jour du registre,
  seule modification autorisée — le séparateur de sortie d'awk rétablit
  l'invariant slug suivi de tabulation suivi de chemin canonique ;
- exécution sur l'état issu du FAIL, puis seconde exécution : registre
  à l'empreinte c298d0b3 après la première exécution, identique après
  la seconde ; manifeste et AGENTS.md aux empreintes d'origine ;
  comptes 2 et 2 inchangés ; zéro écriture des deux indexeurs ; une
  seule section RAG (26 lignes) ;
- observation consignée : la ligne corrompue par le FAIL subsiste en
  résidu inerte — la recherche par tabulation ne la retrouve jamais ;
  elle est éliminée au rejeu depuis précondition propre, qui reconstruit
  le registre par sa voie de création.

Propriété 2 — rejeu depuis précondition propre, 2026-09-07 :

- précondition : état vierge reconstruit — collections supprimées,
  manifeste et registre retirés, AGENTS.md restauré sans section —
  puis instanciation complète par le script corrigé : comptes 2 et 2,
  registre recréé par sa voie de création à l'empreinte d'origine
  1e7558f8, sans résidu ; empreintes relevées pour le manifeste,
  le AGENTS.md et le registre ; section RAG unique ;
- action : nouvelle exécution du script sur cet état ;
- résultat observé : slug repris du manifeste, section RAG déjà
  présente, zéro chunk et zéro entrée écrits par les indexeurs
  (0,5 s chacun) ;
- critère : PASS ;
- preuve : les trois empreintes identiques avant et après — manifeste
  02e5f732, AGENTS.md 82633429, registre 1e7558f8 ; comptes 2 et 2
  inchangés par MCP ; une seule section RAG ; le registre vit au
  format tabulé, sa réécriture laisse le fichier octet pour octet
  intact ;
- constat : la propriété est validée définitivement après correctif ;
  le premier FAIL reste historique dans ce document.

Propriété 3 — granularité d'une modification, 2026-09-07 :

- précondition : état issu de la propriété 2 ; relevé individuel par
  sonde pour chaque élément des deux collections — identifiant,
  empreinte du contenu, empreinte du fichier source — plus les
  empreintes des trois artefacts ;
- action : une phrase ajoutée au seul architecture.md, puis nouvelle
  exécution du script ;
- résultat observé : l'indexeur knowledge signale un fichier modifié
  et un seul, un chunk écrit et un seul ; l'indexeur memories ne
  signale aucun changement ;
- critère : PASS ;
- preuve : partition individuelle avant/après — architecture.md::0
  réécrit (empreinte de chunk 200bb3c7 vers 876013288a46, empreinte
  de fichier 9c4459ae vers e71171b50ac0, identifiant stable) ;
  decisions/0001-synchronisation-wifi.md::0 identique octet pour octet
  (chunk 8f4c1d79f758, fichier 072cb4605213) ; les deux entrées
  mémoire identiques (f02ad0d3d9b1 et bc94957a90f1, fichier
  2b1ee86abd74) ; comptes 2 et 2 inchangés ; manifeste, AGENTS.md et
  registre aux empreintes stables ;
- constat : la granularité est démontrée au niveau du chunk — un seul
  contenu réécrit, l'identifiant déterministe conservé, tout le reste
  strictement intact.

Propriété 4 — purge d'une source supprimée, 2026-09-07 :

- précondition : état issu de la propriété 3, relevé frais par sonde —
  decisions/0001-synchronisation-wifi.md::0 présent (chunk
  8f4c1d79f758, fichier 072cb4605213) ;
- action : suppression du document decisions/0001 du corpus de la
  fixture, puis exécution du script ;
- résultat observé : l'indexeur knowledge signale un fichier supprimé
  et un seul, un chunk obsolète supprimé et un seul ; l'indexeur
  memories ne signale rien ;
- critère : PASS — sur la disparition seule, conformément au cadrage ;
- preuve 1 : présence du chunk cible avant suppression ; preuve 2 :
  après indexation, l'identifiant est absent de la collection, compte
  knowledge à 1, architecture.md::0 et les deux mémoires aux
  empreintes identiques, artefacts stables ; preuve 3, restauration :
  le document réapparaît avec son identifiant déterministe et ses
  empreintes d'origine (chunk 8f4c1d79f758, fichier 072cb4605213),
  compte knowledge de retour à 2, sans autre changement —
  reproductibilité de contenu démontrée ;
- constat : la purge est complète et locale au fichier supprimé ; la
  restauration remet la fixture en état connu pour les propriétés
  suivantes et n'entre pas dans le critère.

Propriété 5 — création d'un nouveau projet, 2026-09-07 :

- précondition : état issu de la propriété 4 ; relevé AVANT — quatre
  collections dans la base (celles du hub et celles du projet 1),
  sonde de référence sur les collections du projet 1 avec leurs
  empreintes ; la fixture second-project créée sur disque, non
  instanciée ;
- action : ./index-project.sh tests/fixtures/second-project/ —
  fixture permanente, projet Perchoir, volontairement distinct du
  projet Lumen ;
- résultat observé : slug second-project dérivé du dossier, contrôle
  d'état annonçant « à créer », collections second-project__knowledge
  et second-project__memories créées avec EF ollama/bge-m3, 2 chunks
  et 2 entrées écrits, section AGENTS.md insérée, manifeste créé ;
- critère : PASS ;
- preuve : la base passe de quatre à six collections ; sonde après
  sur les quatre collections de projets — projet 2 peuplé
  (architecture.md::0 chunk 04580bd19b0f, decisions/0001-catalogue-
  embarque.md::0 chunk d5c40658996d, deux entrées mémoire
  51cbdcba032f et 8b7d54aff128), projet 1 octet pour octet identique
  à la référence (mêmes identifiants, mêmes empreintes, comptes 2 et
  2) ; registre à deux lignes toutes deux tabulées — l'invariant
  tient sur une entrée ajoutée ; manifeste et AGENTS.md du projet 1
  aux empreintes d'origine ; comptes MCP du projet 2 à 2 et 2 ;
- constat : la création du second projet est strictement additive —
  rien du premier projet n'a bougé d'un octet ; note pour la propriété
  suivante : les deux projets partagent des noms d'identifiants
  relatifs identiques (architecture.md::0, preferences::001), ce qui
  en fait le banc d'essai idéal pour l'isolation.

Propriété 6 — isolation entre projets, 2026-09-07 :

- précondition : état issu de la propriété 5 — six collections, les
  deux projets peuplés, identifiants relatifs homonymes connus par
  leurs empreintes (sonde de la propriété 5) ;
- action : batterie de huit requêtes MCP couvrant le routage, la
  contamination adverse, les mémoires et le filtre where sur les
  quatre collections de projets ;
- résultat observé : routage correct dans les deux sens — la question
  wifi sur la collection du projet 1 trouve la décision wifi de Lumen
  (0,369), la question espèces sur la collection du projet 2 trouve la
  décision catalogue de Perchoir (0,410) ; contamination absente — la
  question catalogue sur la collection du projet 1 ne retourne que
  des chunks de Lumen (0,542 et 0,627), la question synchronisation
  sur la collection du projet 2 ne retourne que des chunks de Perchoir
  (0,612 et 0,687) ; mémoires isolées — la même question trouve
  l'entrée Perchoir (0,178) dans les mémoires du projet 2 et ne
  retourne que les entrées Lumen (0,608 et 0,693) dans les mémoires
  du projet 1 ; filtre where — la source catalogue est introuvable
  dans la collection du projet 1 (réponse vide) et trouvée dans celle
  du projet 2 (0,423) ;
- critère : PASS ;
- preuve : les empreintes de contenu identifient sans ambiguïté le
  projet d'appartenance de chaque résultat — les identifiants
  homonymes architecture.md::0 des deux côtés sont correctement
  cloisonnés par collection : même nom, contenus et empreintes
  distincts, jamais croisés ;
- constat : l'isolation est assurée par la collection, pas par le nom
  d'identifiant ; note méthodologique consignée — les huit réponses
  parallèles sont revenues dans un ordre ne respectant pas l'ordre des
  appels, et ce sont les empreintes de la sonde qui ont permis
  d'attribuer chaque réponse à sa requête sans erreur : la méthode
  d'empreintes fait elle-même partie de la preuve.

Propriété 7 — intégrité de la production, 2026-09-07 :

- précondition : relevé AVANT complet — identifiants et empreintes des
  63 éléments des deux collections de production (53 chunks dans
  project_knowledge, 10 entrées dans memories), trié, avec digest
  synthétique 13230fccd3f52a8c2d9f969ea7de839b00f80818c80a83f500ec28afa98c18a0 ;
- action : exécution complète des deux indexations multi-projets —
  ./index-project.sh sur multi-project puis sur second-project ;
- résultat observé : les quatre indexeurs écrivent zéro chunk et
  zéro entrée (états stables des deux projets), aucune écriture vers
  les collections du hub ;
- critère : PASS ;
- preuve : relevé APRÈS identique et diff vide entre les listes
  complètes avant et après — aucun identifiant ajouté, supprimé ni
  modifié, aucune empreinte modifiée, digest inchangé ;
- constat : les collections de production sont strictement hors
  d'atteinte des indexations multi-projets ; liste de référence
  conservée ci-dessous pour tout diagnostic futur.

Liste de référence (identique avant et après, 63 éléments) :

    architecture.md::0 15b0af7ae20a
    architecture.md::1 91b711e1c75e
    architecture.md::2 398c410eea1d
    conventions.md::conventions::001 6beeb1073e4d
    conventions.md::conventions::002 e88a2c0564f4
    conventions.md::conventions::003 493473064ac6
    conventions.md::conventions::004 378cc034a9c9
    decisions/0001-venv-isoles-conteneur-unique.md::0 4578fff79b69
    decisions/0001-venv-isoles-conteneur-unique.md::1 41834dcc6419
    decisions/0002-reseau-chroma-net-compose.md::0 59b730867084
    documentation/operations.md::0 87ffecba4133
    documentation/operations.md::1 96fa5ed28a38
    documentation/operations.md::2 b6d29bdc71fc
    durable-context.md::durable-context::001 6fc377b9655c
    durable-context.md::durable-context::002 55b8d96a661e
    durable-context.md::durable-context::003 39f59145eba5
    preferences.md::preferences::001 5cffd5b0bed2
    preferences.md::preferences::002 5f45ed1a7b79
    preferences.md::preferences::003 6bd0101a8e45
    specs/indexer.md::0 09641692c4b2
    specs/indexer.md::1 ffbe7bee77da
    specs/indexer.md::2 feac4d444706
    specs/memory-workflow.md::0 644bcc7a656a
    specs/memory-workflow.md::1 8d133f0c8e0f
    specs/memory-workflow.md::2 e44e5191550e
    specs/multi-projets-suivi.md::0 dfa396b8bd57
    specs/multi-projets-suivi.md::1 870e55f07247
    specs/multi-projets-suivi.md::10 0dc30baa3dc3
    specs/multi-projets-suivi.md::11 cf719c522b0f
    specs/multi-projets-suivi.md::12 439f7ba45b7c
    specs/multi-projets-suivi.md::13 c54b19dffbbb
    specs/multi-projets-suivi.md::14 deb698178a67
    specs/multi-projets-suivi.md::15 36aea2e43025
    specs/multi-projets-suivi.md::16 9a19a31952b5
    specs/multi-projets-suivi.md::17 0a5fab3d238e
    specs/multi-projets-suivi.md::18 ff9c740b8c19
    specs/multi-projets-suivi.md::19 c4a21a0a2c66
    specs/multi-projets-suivi.md::2 f31e9344756a
    specs/multi-projets-suivi.md::20 5abf98ee1bc1
    specs/multi-projets-suivi.md::21 9c00ba4db0ce
    specs/multi-projets-suivi.md::22 5c7d02270269
    specs/multi-projets-suivi.md::23 62f91e8ac6f4
    specs/multi-projets-suivi.md::24 269b7d3a5fd2
    specs/multi-projets-suivi.md::25 734b4d2ebc67
    specs/multi-projets-suivi.md::26 f864cfc27ba5
    specs/multi-projets-suivi.md::27 e243761dc898
    specs/multi-projets-suivi.md::28 68124cf13639
    specs/multi-projets-suivi.md::3 3cefd90facd1
    specs/multi-projets-suivi.md::4 49b9d15e3e4b
    specs/multi-projets-suivi.md::5 770bdf45355f
    specs/multi-projets-suivi.md::6 7e0c97bcee52
    specs/multi-projets-suivi.md::7 7add18ff18e1
    specs/multi-projets-suivi.md::8 5609f8b354b9
    specs/multi-projets-suivi.md::9 c918a33fd87d
    specs/multi-projets.md::0 bcde72901aaa
    specs/multi-projets.md::1 52df41ada4af
    specs/multi-projets.md::2 5c68ebcd3828
    specs/multi-projets.md::3 a998c5b9c2ea
    specs/multi-projets.md::4 525a84ea5a59
    specs/multi-projets.md::5 73a82f280708
    specs/multi-projets.md::6 8fcff0b59a1a
    specs/multi-projets.md::7 d2ae8b83bc47
    specs/multi-projets.md::8 5656c34ce01b

Propriété 8 — identité par renommage du dossier, 2026-09-07 (première
exécution) :

- précondition : relevé AVANT — registre à deux entrées dont
  multi-project pointé sur le chemin d'origine, six collections,
  manifeste de la fixture à slug multi-project, dossier physique
  renommé en multi-project-renomme ;
- action : exécution du script sur le nouveau chemin ;
- résultat observé : le slug est bien repris du manifeste (« le
  manifeste fait foi ») — l'identité tient — mais l'exécution est
  refusée : le contrôle de collision compare le chemin enregistré au
  chemin courant sans distinguer le propre projet renommé d'un autre
  projet vivant revendiquant le même slug ; refus avec proposition du
  slug canonique multi-project--bf9403 ;
- critère : FAIL — le renommage spécifié est impossible : le registre
  ne peut pas suivre le chemin canonique ;
- preuve : sortie du refus ; effets de bord vérifiés nuls — registre
  inchangé, aucune collection créée (six collections inchangées),
  aucun artefact sous l'ancien nom ; les critères déjà acquises à ce
  stade : slug du manifeste, aucune nouvelle collection, aucune
  écriture ;
- constat : cause identifiée — le contrôle de collision ne teste pas
  l'existence du chemin enregistré ; un projet renommé dont le
  manifeste déclare le slug est son propre historique, pas un tiers ;
  correctif proposé : ne refuser que si le chemin enregistré existe
  encore comme dossier vivant — chemin disparu plus manifeste
  présent égal renommage, le registre suit alors le nouveau chemin ;
  sans manifeste, le refus prudent est conservé. Aucune correction
  appliquée à ce stade — décision humaine attendue.

Correctif de la propriété 8, 2026-09-07, validé humain :

- correctif : le contrôle de collision distingue désormais trois
  branches — chemin enregistré vivant : refus pour collision réelle ;
  chemin enregistré disparu avec manifeste : renommage, le manifeste
  fait foi et le registre suit ; chemin enregistré disparu sans
  manifeste : refus prudent ;

Propriété 8 — re-test depuis l'état renommé, 2026-09-07 :

- précondition : dossier renommé en multi-project-renomme, manifeste
  voyageur à slug multi-project, registre pointant sur l'ancien
  chemin, six collections — précondition propre, le FAIL ayant été
  prouvé sans effet de bord ;
- action : exécution du script corrigé sur le nouveau chemin ;
- résultat observé : slug repris du manifeste, renommage détecté et
  annoncé avec l'ancien chemin, collections multi-project__knowledge
  et multi-project__memories existantes réutilisées, section AGENTS
  déjà présente, zéro chunk et zéro entrée écrits ;
- critère : PASS ;
- preuve : registre avant l'ancien chemin, après le nouveau chemin,
  tabulé, entrée second-project intacte ; empreintes des quatre
  éléments du projet inchangées ; comptes 2 et 2 ; six collections
  inchangées, aucune seconde entrée ni collection ; renommage-retour
  exécuté en vérification complémentaire : registre revenu au chemin
  nominal, zéro écriture, fixture en état connu ;
- constat : l'identité RAG appartient au projet par son manifeste,
  pas à son dossier — le renommage est transparent de bout en bout ;
  le premier FAIL reste historique dans ce document.

Propriété 9 — collision de slug, 2026-09-07 :

- précondition : registre nominal à deux entrées (empreinte
  95602c11), six collections ; sous-fixture jetable créée sous
  tests/fixtures/.tmp-collision/multi-project/ avec docs minimal,
  sans manifeste — même slug candidat multi-project, chemin courant
  différent du chemin enregistré vivant ;
- action : exécution du script sur le chemin collisionnel, deux
  fois ;
- résultat observé : refus net de collision réelle — slug dérivé du
  dossier multi-project, chemin enregistré vivant cité, repli
  déterministe proposé multi-project--b6807e ; les deux exécutions
  produisent des sorties identiques ;
- critère : PASS ;
- preuve : diff vide entre les deux sorties ; effets de bord nuls —
  dossier collisionnel vierge de tout artefact, registre à
  l'empreinte inchangée, six collections inchangées, aucune
  collection de repli créée ; sous-fixture purgée ;
- constat : la collision réelle est refusée proprement, le repli
  déterministe est stable d'une exécution à l'autre.

Test complémentaire — branche 3 (chemin disparu sans manifeste),
2026-09-07 :

- première tentative, erreur de préparation consignée : le dossier
  test était caché (.tmp-fantome) — le slugify retire le point des
  bornes, le slug dérivé tmp-fantome ne correspondait pas à
  l'entrée synthétique fantome, aucune branche de collision ne
  s'est déclenchée et le script a instancié un projet complet
  (collection tmp-fantome__knowledge créée, registre enrichi) —
  comportement correct du script pour un slug réellement libre ;
  récupération complète : collection supprimée, ligne de registre
  retirée, état nominal restauré à l'empreinte exacte 95602c11 ;
- deuxième tentative, correctement configurée : dossier visible
  nommé fantome, entrée synthétique morte injectée au registre ;
- résultat observé : refus prudent explicite — chemin enregistré
  disparu cité, identité non confirmée sans manifeste, consignes
  de sortie données ;
- critère : PASS (complémentaire) ;
- preuve : dossier vierge de tout artefact après le refus, registre
  inchangé, nettoyage complet, état nominal à l'empreinte 95602c11 ;
- constat : observation utile consignée — un nom de dossier caché
  produit un slug sans son point (bornes alphanumériques), quirk du
  slugify sans incidence sur la production mais à connaître pour
  les fixtures futures.

Propriété 10 — persistance après recréation du conteneur de base,
2026-09-07 :

- précondition : relevé AVANT complet des six collections — 83
  éléments, identifiants et empreintes, digest synthétique
  79b03b868d70a7823dece8c8d99d8c7c0b183501489c52ec17f2a1086bbe6183 ;
- action : recréation du seul conteneur de base par compose
  force-recreate — le proxy laissé intact (21 heures d'activité
  continue) ;
- résultat observé : heartbeat vivant après recréation ; les six
  collections présentes avec leurs comptes identiques ; relevé
  APRÈS identique — diff vide sur les 83 éléments, digest inchangé ;
  requêtes sémantiques fonctionnelles via MCP sur les trois types
  de collections ;
- critère : PASS ;
- preuve : comptes avant/après identiques (65, 10, 2, 2, 2, 2) ;
  diff vide, digest 79b03b86 inchangé ; requête production — la
  question de la survie au redémarrage trouve le passage du runbook
  sur la résilience au redémarrage (0,428) ; requête knowledge de
  projet — la question de synchronisation trouve la décision wifi
  de Lumen (0,369) ; requête mémoire de projet — la question des
  textes courts trouve l'entrée correspondante (0,296) ;
- constat : la persistance est démontrée au-delà de la présence du
  fichier — chaque identifiant, chaque empreinte et la capacité de
  requête ont survécu ; le bind mount ./data fait exactement son
  travail, et le proxy n'a pas été affecté.

## Décisions validées

- Validée : le script insère automatiquement la section AGENTS.md
  depuis le gabarit, de façon idempotente — l'instanciation reste une
  opération atomique du point de vue de l'utilisateur.
- Validée : la fixture de test est conservée comme fixture de
  régression, sous tests/fixtures/multi-project/ pour être
  explicitement identifiable, plutôt que sous un chemin ressemblant à
  un projet réel.

## Synthèse de clôture

Phase 1 closee le 2026-09-07. Le protocole des dix propriétés est
validé sur toute la ligne : première indexation, idempotence,
granularité, purge, création d'un second projet, isolation,
intégrité de la production, identité par renommage, collision
déterministe, persistance après recréation du conteneur de base.

Le protocole a rempli sa fonction de détection : deux FAIL réels,
conservés en trace sans requalification. La propriété 2 a révélé la
corruption du séparateur du registre à chaque réécriture — l'empreinte
octet par octet l'a attrapée là où la sortie du script semblait
normale ; correctif d'une ligne, le séparateur de sortie d'awk. La
propriété 8 a révélé la confusion entre renommage légitime et
collision — le manifeste établit la continuité d'identité ; correctif
en trois branches. Deux incidents de préparation de test, non
imputables au code, sont consignés avec leur récupération complète et
vérifiée à l'empreinte exacte.

La méthode a fait ses preuves : mesure objective avant tout verdict,
FAIL historique conservé, correctif minimal validé par l'humain,
re-test depuis précondition propre. L'état final de la stack : deux
fixtures permanentes instanciées et vérifiées, six collections
opérationnelles, un script d'instanciation robuste et idempotent, un
gabarit de routage strictement conforme à la spécification, et un
protocole rejouable pour toute évolution future.

Exclusions de périmètre rappelées, inchangées : pas de pilote réel
(le projet pilote reste en phase 2), pas de CLI rag, pas de rag init ni rag
doctor, pas d'automatisation Git de la réindexation, pas de mémoire
globale, pas de migration des collections du hub. L'instance actuelle
reste le laboratoire de référence.

## Statut

Phase 1 closee le 2026-09-07 — document validé, étapes 1 à 6
exécutées, protocole des dix propriétés PASS avec deux FAIL
historiques conservés (propriétés 2 et 8) et leurs correctifs
démontrés par re-test. Le commit de la phase conclut le cycle ; la
suite appartient à la phase 2.