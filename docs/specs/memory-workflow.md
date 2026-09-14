# Spécification du workflow mémoire V2

## Principe

L'agent peut proposer des mémoires ; seul l'humain les valide. La règle
d'architecture est stricte : l'agent n'écrit jamais dans Chroma, ni par
les outils MCP, ni par le client direct. La seule surface d'écriture de
l'agent est le fichier Markdown source, dans l'arbre de travail Git,
jamais committé par lui.

## Surfaces et responsabilités

- l'agent détecte une information durable et rédige la proposition en
  éditant le fichier source ;
- l'humain examine le diff, corrige ou refuse, commite, lance l'indexer ;
- memory-indexer applique le fichier validé à la collection memories,
  avec l'idempotence par hash et la purge des entrées retirées.

## Critères d'admission d'une mémoire

Une proposition n'est recevable que si l'information est :

- durable : vraie indépendamment de la conversation en cours ;
- atomique : un fait, une préférence ou une convention unique ;
- non dérivable : une connaissance du projet appartient à docs/, pas à
  memory/ ;
- utile : sa restitution changerait un comportement futur.

Les conversations, les hypothèses temporaires et les informations
d'exécution ne sont jamais des mémoires.

## Format d'une proposition (identique au format indexé V1)

L'entrée est ajoutée dans le fichier de sa catégorie, à la suite des
entrées existantes :

    ## preferences::010
    <!-- created: 2026-09-04 -->
    <!-- updated: 2026-09-04 -->
    Le benchmark Recall@k doit précéder tout changement de modèle
    d'embedding en production.

Règles de conformité :

- les clés des commentaires sont `created` et `updated` — pas
  `created_at` ni `updated_at`, que l'indexer ignore silencieusement ;
- la catégorie vient de l'en-tête du fichier, `<!-- category: ... -->` ;
  aucune catégorie par entrée n'existe ;
- l'identifiant suit la convention fichier::numéro, en numérotation à
  trois chiffres, libre au moment de la proposition : l'agent lit le
  fichier et prend le numéro suivant ;
- un titre indenté (bloc de code) n'est jamais une entrée ;
- le texte tient en une phrase ou quelques lignes.

## Les trois opérations

### Créer

1. L'agent identifie une information durable et choisit le fichier de la
   catégorie adaptée.
2. Il lit le fichier, prend le prochain numéro libre, ajoute l'entrée en
   fin de fichier conformément au format.
3. Il s'arrête là et invite l'humain à relire le diff.

### Modifier

1. L'agent retrouve la mémoire concernée : requête sémantique sur la
   collection memories, ou lecture directe du fichier source.
2. Il propose le remplacement dans le fichier : texte réécrit, `created`
   conservé, `updated` mis au jour.
3. Il s'arrête et laisse l'humain relire le diff.

### Supprimer

1. L'agent identifie la mémoire obsolète et la retire du fichier source.
2. Il s'arrête. La validation humaine vaut décision : au réindexage
   suivant, l'indexer purge l'entrée retirée par la mécanique V1 des
   orphelins — aucun code spécifique n'est nécessaire.

## Ce que l'agent ne fait jamais

- écrire dans Chroma par quelque moyen que ce soit ;
- committer ou annuler des changements Git ;
- lancer l'indexer sans demande explicite post-validation ;
- créer un nouveau fichier de catégorie sans validation : les catégories
  existantes sont preferences, conventions, durable-context.

## Boucle complète

    proposition : fichier édité, non committé
      -> diff humain : correction ou refus
      -> commit
      -> docker compose run --rm memory-indexer
      -> collection memories à jour