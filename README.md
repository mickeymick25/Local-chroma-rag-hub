# chroma-rag-hub — Hub RAG local multi-projets

Stack locale de mémoire vectorielle pour le portefeuille de projets :
**ChromaDB** (docker compose, port 8000), un **proxy MCP** exposant
chroma-mcp (port 8080), et deux **indexers batch** — `docs/` vers
`project_knowledge`, `memory/` vers `memories`. Les collections
s'interrogent via les outils MCP `chroma_*`.

Embedding : **bge-m3** via Ollama, unique et validé par benchmark —
ne jamais changer de modèle sans re-benchmark et reconstruction RESET.

## Architecture

    ChromaDB (:8000)  ── volume ./data (non versionné)
        ▲
        │  MCP streamable-HTTP
    chroma-mcp-proxy (:8080) ── Zed (serveur MCP « chroma »)
        ▲
        │  embeddings
    Ollama (:11434) — bge-m3, 1024 dimensions

Indexation incrémentale par hash de contenu : `indexer.py`
(docs/ → project_knowledge) et `memory_indexer.py` (memory/ →
memories), lancés via `docker compose run --rm indexer` /
`memory-indexer`.

## Démarrage rapide

```bash
docker network create chroma-net   # réseau externe partagé
docker compose up -d               # chroma + proxy MCP
./index-project.sh <racine du projet>   # instancier/indexer un projet
```

`index-project.sh` crée pour chaque projet : manifeste `.rag.yaml`
(slug canonique), section RAG dans `AGENTS.md` (gabarit
`templates/AGENTS-rag-section.md`), registre machine-local
`.rag-projects.list` (non versionné), et les collections
`<slug>__knowledge` / `<slug>__memories`.

## Collections

- `project_knowledge` — connaissances du hub (`docs/`)
- `memories` — mémoires durables du hub (`memory/`)
- `<slug>__knowledge` / `<slug>__memories` — par projet instancié

## Workflow mémoire

L'agent **propose** les mémoires ; seul l'humain les valide :
modification de `memory/*.md`, relecture du diff, commit, puis
`docker compose run --rm memory-indexer`. Jamais d'écriture directe
dans Chroma/memories par un agent.

## Documentation

- `docs/architecture.md`, `docs/decisions/` — architecture de la
  stack et décisions d'architecture (ADR)
- `docs/specs/indexer.md` — plan d'ingestion de la stack (indexation
  incrémentale par hash)
- `docs/specs/memory-workflow.md` — workflow mémoire V2 (agent
  propose, humain valide)
- `docs/specs/multi-projets.md` — extension multi-projets :
  instanciation, isolation, protocole de validation ; suivi dans
  `multi-projets-suivi.md`

Les chroniques de validation par projet (pilotes, qualifications)
restent locales, hors dépôt public.

## Notes d'exploitation

- après recréation du conteneur proxy (redémarrage machine) :
  **réactiver le serveur chroma dans les réglages MCP de Zed**
  (sessions invalidées, erreurs 404) ;
- après changement d'embedding : re-benchmark obligatoire puis
  reconstruction RESET des collections ;
- `data/` et `.rag-projects.list` sont machine-locals : jamais
  versionnés, `data/` est reconstruisable par réindexation.