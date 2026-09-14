# Instructions — Perchoir (fixture)

Ce dossier est une fixture de régression du hub RAG : il simule un
second projet de développement, distinct de Lumen, pour éprouver
l'instanciation multi-projets et l'isolation entre collections.

Travailler en français dans cette fixture. Le corpus reste
minimaliste : il sert la régression, pas la documentation.

## RAG local

Ce projet utilise le hub RAG local.

Collections :
- connaissances : second-project__knowledge
- mémoires : second-project__memories

Recherche de connaissances du projet : exclusivement
second-project__knowledge. Recherche de mémoire du projet :
exclusivement second-project__memories. Aucune collection d'un autre
projet sans demande explicite de l'utilisateur.

Les mémoires durables suivent le workflow du hub : l'agent
propose, l'humain valide, Git trace, puis le memory-indexer.

Réindexation : ~/AI/chroma/index-project.sh <racine du projet>