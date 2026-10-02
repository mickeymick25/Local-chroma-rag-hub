<!-- category: convention -->

# Conventions

## conventions::001
<!-- created: 2026-09-04 -->
Les documents Git sont la source de vérité ; Chroma est un index dérivé,
reconstruisible à tout moment.

## conventions::002
<!-- created: 2026-09-04 -->
Une collection plate avec la catégorie en métadonnée plutôt que des
sous-collections.

## conventions::003
<!-- created: 2026-09-04 -->
bge-m3 est le modèle d'embedding unique de toutes les collections,
validé par le benchmark Recall@k du 2026-09-04.

## conventions::004
<!-- created: 2026-09-04 -->
<!-- updated: 2026-09-04 -->
Le benchmark Recall@k doit précéder tout changement de modèle d'embedding
en production.

## conventions::005
<!-- created: 2026-09-30 -->
Un projet n'est instancié dans le hub RAG que lorsque son dossier docs/
contient au moins un document à indexer.