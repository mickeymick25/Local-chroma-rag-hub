# Benchmark Recall@k des modèles d'embedding

Comparaison reproductible et versionnée des candidats d'embedding pour le
RAG du projet, sur un corpus de référence figé.

## Structure

```
benchmarks/
├── corpus/              # corpus de référence figé (10 documents, 30 chunks)
├── queries.jsonl        # 25 questions + chunks attendus (vérité terrain)
├── chunk_layout.py      # régénère la correspondance source::chunk_index
├── run_benchmark.py     # runner (à construire, voir plus bas)
└── README.md
```

## Protocole

### Corpus de référence

Le corpus contient 10 documents couvrant les sujets de la stack :
architecture, orchestration Docker, protocole MCP, conflit de versions,
persistance, indexeur, décisions, service Ollama, runbook, outils Chroma.
Il produit exactement **30 chunks** avec le chunker réel de l'indexer
(`MAX_CHARS=1200`), soit assez de distracteurs pour rendre le classement
non trivial, sans être immense.

La correspondance `source::chunk_index` est générée par :

    docker run --rm \
      -v "$PWD/benchmarks:/bench:ro" \
      --entrypoint python local/chroma-indexer:latest \
      /bench/chunk_layout.py /bench/corpus

Toute modification du corpus ou du paramètre de découpage invalide la
vérité terrain : régénérer la carte et revérifier `queries.jsonl`.

### Vérité terrain

`queries.jsonl` contient une question par ligne :

```json
{"id": "q01", "topic": "architecture",
 "question": "…", "expected": ["architecture-stack.md::0"]}
```

- 25 questions couvrent : architecture, Docker/réseau, MCP, versions et
  dépendances, persistance, indexation, décisions, outils ;
- 7 questions sont **paraphrasées** sans vocabulaire du corpus (ex. « qui
  consulte la base et qui la remplit ? ») pour mesurer la similarité
  sémantique, pas la correspondance lexicale ;
- 10 questions ont une réponse **répartie sur plusieurs chunks** :
  `expected` liste tous les chunks qui répondent réellement à la question,
  pour ne pas pénaliser un modèle qui remonte une réponse valide
  différente de la première prévue.

### Isolation des modèles

Chaque candidat est indexé dans sa **propre collection Chroma**, pour
qu'aucun modèle ne puisse influencer les résultats d'un autre :

- `project_knowledge_bge_m3` (1024 dimensions)
- `project_knowledge_nomic` (768 dimensions)

Chaque collection est détruite et reconstruite au début de chaque run du
benchmark.

### Protocole par modèle : le pipeline réellement utilisable

Le benchmark mesure le pipeline complet, préfixes inclus :

- **bge-m3** : aucun préfixe. Les documents et les requêtes sont encodés
  tels quels.
- **nomic-embed-text** : les documents sont préfixés par
  `search_document: `, les requêtes par `search_query: `. Sans ces
  préfixes, les vecteurs ne sont pas comparables : le runner les applique
  systématiquement.

Les embeddings sont produits par le service Ollama de l'hôte via
`http://host.docker.internal:11434/api/embed`, par lots.

## Métriques

Pour chaque question et chaque modèle :

- **Recall@k** (k = 1, 3, 5) : proportion de chunks attendus présents dans
  les k premiers résultats. Pour une question à 2 chunks attendus, un
  Recall@3 de 0.5 signifie qu'un seul des deux est dans le top 3. Le score
  final est la moyenne sur les 25 questions.
  **Note méthodologique** : la métrique mesure le rappel des chunks
  pertinents, pas la capacité à récupérer une réponse complète. Pour une
  question à N chunks attendus, un top-1 ne peut au mieux atteindre 1/N —
  c'est le comportement voulu, documenté ici une fois pour toutes.
- **distance du top-1** : distance telle que renvoyée par Chroma pour le
  premier résultat. Indicative seulement, non comparable entre modèles.
- **temps d'embedding** : temps total d'indexation des 30 chunks.
- **temps total de requête** : temps cumulé des 25 requêtes.

## Résultats

Le runner produit un fichier brut horodaté et un `latest.json` :

```
benchmarks/results/
├── benchmark-YYYYMMDD-HHMMSS.json
└── latest.json
```

Chaque question y est décrite avec `query`, `model`, `top_k_results`
(identifiant, distance, catégorie, aperçu), `expected`, `hits`,
`recall@1/3/5`, `embedding_ms` (embedding de la requête) et `query_ms`
(recherche Chroma). Un résultat surprenant s'examine dans le classement
exact, pas seulement dans le score agrégé.

Tableau de synthèse (run du 2026-09-04 17:51, vérité terrain corrigée sur q17 :
`indexer.md::1` ajouté à `expected`, la réponse étant vérifiablement dans ce
chunk — voir `results/benchmark-20260904-175155.json`) :

| Modèle            | Recall@1 | Recall@3 | Recall@5 | Embedding | Requêtes |
| ----------------- | -------- | -------- | -------- | --------- | -------- |
| bge-m3            | 0.380    | **0.740**| **0.840**| 56.6 s    | 651 ms   |
| nomic-embed-text  | **0.400**| 0.640    | 0.780    | 26.1 s    | 608 ms   |

Lecture : bge-m3 domine nettement sur Recall@3 et Recall@5 (la zone où
l'agent consomme réellement les chunks), nomic-embed-text prend une avance
marginale sur Recall@1 et embedde environ deux fois plus vite. Les deux runs
sont strictement reproductibles — classements et distances identiques — seul
le score de q17 a changé après correction, d'exactement +0.5/25 points.

## Reproductibilité

Le corpus et la vérité terrain sont versionnés dans Git. Le runner
construit ses collections à partir du corpus seul, les détruit à la fin,
et n'écrit jamais dans `project_knowledge` : les collections de production
et de benchmark sont étanches. Aucune donnée de la production ne peut
fausser le benchmark, et inversement.

## Runner

    docker run --rm --network chroma-net \
      -v "$PWD/benchmarks:/bench" \
      --entrypoint python local/chroma-indexer:latest \
      /bench/run_benchmark.py

Le runner vérifie d'abord la cohérence de la vérité terrain avec le
 découpage actuel du corpus (tout chunk attendu doit exister), puis pour
chaque candidat : détruit et recrée sa collection dédiée, indexe le corpus
avec le protocole de préfixes du modèle, exécute les 25 requêtes (préfixes
de requête inclus), calcule les métriques, remplit le tableau, détruit la
collection de benchmark et écrit les fichiers résultats. Il n'écrit
jamais dans `project_knowledge`.