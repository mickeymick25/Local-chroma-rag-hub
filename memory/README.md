# Mémoires — source de vérité

La collection `memories` est indexée depuis ces fichiers. Contrairement à
`docs/` (project_knowledge, documents réindexables par chunks), chaque
entrée ici est **atomique** : un fait, une préférence ou une convention
indépendante, remplaçable ou supprimable sans toucher aux autres.

## Format

Un fichier mémoire déclare sa catégorie en tête — **c'est obligatoire** :
tout fichier `.md` sans cette déclaration est ignoré (ce README n'est donc
jamais indexé) — puis liste des entrées délimitées par des titres non
indentés :

    <!-- category: preference -->

    # Préférences

    ## preferences::001
    <!-- created: 2026-09-04 -->
    <!-- updated: 2026-09-04 -->
    Texte de la mémoire, une phrase ou quelques lignes au plus.

- `## <memory_id>` : identifiant stable de l'entrée (fichier::numéro) ;
- `<!-- created: ... -->` / `<!-- updated: ... -->` : dates optionnelles,
  invisibles à la lecture du Markdown ;
- `<!-- category: ... -->` en tête de fichier : **requis**, définit la
  catégorie des entrées de ce fichier ;
- les titres indentés (blocs de code) ne sont jamais des entrées.

## Flux de validation

Aucune écriture automatique : l'agent propose, l'humain valide. Le flux
complet (créer, modifier, supprimer) est spécifié dans
specs/memory-workflow.md de docs/ :

    l'agent propose une mémoire -> validation humaine explicite
    -> l'entrée entre dans le fichier -> docker compose run --rm memory-indexer

Cela évite que la collection devienne un dépotoir de conversations,
d'hypothèses ou d'informations temporaires : une mémoire doit être
durable, atomique et validée.

## Réindexation

    docker compose run --rm memory-indexer

Même idempotence que l'indexeur principal : hash de fichier, upsert,
purge des entrées supprimées. Sans catégorie déclarée, ce fichier n'est
jamais indexé.

## Catégories prévues

- `preference` — préférences de travail ;
- `convention` — règles adoptées pour le projet ;
- `durable_context` — faits stables sur l'environnement ;
- `decision` — décisions à retenir (si distinctes des ADR de project_knowledge).