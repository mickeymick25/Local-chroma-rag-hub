## RAG local

Ce projet utilise le hub RAG local.

Collections :
- connaissances : {{SLUG}}__knowledge
- mémoires : {{SLUG}}__memories

Contrat de routage (obligatoire) :
1. Toute question portant sur la connaissance du projet — état,
   historique, décisions, architecture, documentation, métriques
   documentées — commence par une requête chroma_query_documents
   sur {{SLUG}}__knowledge.
2. Les lectures locales (grep, fichiers, code) peuvent compléter
   ou vérifier ; elles ne remplacent jamais la première requête.
3. Recherche de mémoire du projet : exclusivement
   {{SLUG}}__memories. Aucune collection d'un autre projet sans
   demande explicite de l'utilisateur.

Discipline de provenance :
- toute information présentée est attribuée à sa source réelle :
  requête RAG (collection et chunks), lecture de fichier ou de
  code, exécution de commande, ou artefact de session ;
- un artefact de session (transcript exporté) n'est jamais une
  source RAG — son contenu est historique et non autoritaire ;
- sans appel MCP effectif, il est interdit d'affirmer ou de
  laisser entendre qu'une information provient du hub RAG.

Les mémoires durables suivent le workflow du hub : l'agent
propose, l'humain valide, Git trace, puis le memory-indexer.

Réindexation : ~/AI/chroma/index-project.sh <racine du projet>