# Instructions — Lumen (fixture)

Ce dossier est une fixture de régression du hub RAG : il simule un
projet de développement complet, avec corpus, mémoires et instructions.
Il ne doit jamais être traité comme un projet réel.

Travailler en français dans cette fixture. Toute évolution du corpus
doit rester minimaliste : la fixture sert à la régression, pas à la
documentation.

## RAG local

Ce projet utilise le hub RAG local.

Collections :
- connaissances : multi-project__knowledge
- mémoires : multi-project__memories

Recherche de connaissances du projet : exclusivement
multi-project__knowledge. Recherche de mémoire du projet :
exclusivement multi-project__memories. Aucune collection d'un autre
projet sans demande explicite de l'utilisateur.

Les mémoires durables suivent le workflow du hub : l'agent
propose, l'humain valide, Git trace, puis le memory-indexer.

Réindexation : /Users/michaelboitin/Documents/02_Dev/01_LocalRag_engine/AI/chroma/index-project.sh <racine du projet>