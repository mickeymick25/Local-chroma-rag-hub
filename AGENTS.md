# Instructions agent — stack Chroma

Ce dépôt héberge une stack locale de mémoire vectorielle : ChromaDB
(docker compose, port 8000), un proxy MCP exposant chroma-mcp (port 8080),
et deux indexers batch — docs/ vers project_knowledge, memory/ vers
memories. Les collections s'interrogent via les outils MCP chroma_*.
Embedding : bge-m3 via Ollama, unique et validé par benchmark — ne jamais
changer de modèle sans re-benchmark et reconstruction RESET.

## Commandes utiles

- Réindexer les connaissances : `docker compose run --rm indexer`
- Réindexer les mémoires : `docker compose run --rm memory-indexer`
- Test MCP bout en bout : commande dans l'en-tête de `e2e_mcp_test.py`
- Après une recréation du conteneur proxy : réactiver le serveur chroma
  dans les réglages MCP de Zed (sessions invalidées, erreurs 404).

## Workflow mémoire V2 — règle stricte

L'agent PROPOSE des mémoires ; seul l'humain les valide.

Interdits absolus :

- écrire dans Chroma/memories par un outil MCP ou autre moyen ;
- committer ou annuler des changements Git ;
- lancer memory-indexer sans validation humaine explicite ;
- proposer une information temporaire, conversationnelle, ou dérivable de
  docs/ (celle-là va dans docs/, pas dans memory/).

Pour proposer une création :

1. Vérifier que l'information est durable, atomique, non dérivable.
2. Lire le fichier catégorie concerné (memory/preferences.md,
   memory/conventions.md, memory/durable-context.md) et prendre le
   prochain numéro libre.
3. Ajouter l'entrée en fin de fichier, au format exact :

       ## preferences::010
       <!-- created: 2026-09-04 -->
       <!-- updated: 2026-09-04 -->
       Une phrase, un seul fait.

   Clés `created`/`updated` (pas `created_at`) ; la catégorie vient de
   l'en-tête du fichier ; jamais de titre `##` indenté.
4. S'arrêter, inviter l'humain à relire le diff, corriger au besoin ;
   le commit et le lancement de memory-indexer lui appartiennent.

Pour modifier : remplacer le texte de l'entrée, conserver `created`,
mettre `updated` au jour. Pour supprimer : retirer l'entrée du fichier.
Toujours s'arrêter pour validation humaine avant tout commit.

Spécification complète : `docs/specs/memory-workflow.md`.
Format et catégories : `memory/README.md`.