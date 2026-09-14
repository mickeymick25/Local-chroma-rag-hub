#!/usr/bin/env python3
"""Benchmark Recall@k des modèles d'embedding Ollama sur le corpus de référence.

Pour chaque candidat :
    1. détruit puis recrée sa collection dédiée (étanche à la production) ;
    2. indexe le corpus avec le protocole de préfixes du modèle ;
    3. exécute les requêtes de queries.jsonl (préfixes de requête inclus) ;
    4. calcule Recall@1/3/5 par question et en moyenne, distances et temps ;
    5. détruit la collection de benchmark à la fin.

Aucun contact avec project_knowledge ni avec l'indexer de production :
les collections utilisées sont project_knowledge_bge_m3 et
project_knowledge_nomic.

Usage (conteneur indexer, benchmarks/ monté en lecture-écriture) :

    docker run --rm --network chroma-net \
      -v "$PWD/benchmarks:/bench" \
      --entrypoint python local/chroma-indexer:latest \
      /bench/run_benchmark.py
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import chromadb
import requests

sys.path.insert(0, "/app")  # indexer.py (chunker réel) est baké dans l'image

from indexer import MAX_CHARS, category_for, chunk_file  # noqa: E402

BENCH_DIR = Path(os.environ.get("BENCH_DIR", "/bench"))
CORPUS_DIR = Path(os.environ.get("CORPUS_DIR", "/bench/corpus"))
QUERIES_FILE = BENCH_DIR / "queries.jsonl"
RESULTS_DIR = BENCH_DIR / "results"

CHROMA_HOST = os.environ.get("CHROMA_HOST", "chroma")
CHROMA_PORT = os.environ.get("CHROMA_PORT", "8000")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434")

TOP_K = 5
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "16"))

MODELS = [
    {
        "name": "bge-m3",
        "collection": "project_knowledge_bge_m3",
        "doc_prefix": "",
        "query_prefix": "",
    },
    {
        "name": "nomic-embed-text",
        "collection": "project_knowledge_nomic",
        "doc_prefix": "search_document: ",
        "query_prefix": "search_query: ",
    },
]


def load_queries():
    queries = []
    for line in QUERIES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            queries.append(json.loads(line))
    return queries


def embed_texts(texts, model):
    """Embeddings par lot via l'API Ollama (préfixes déjà appliqués)."""
    resp = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": model, "input": texts},
        timeout=600,
    )
    resp.raise_for_status()
    vectors = resp.json()["embeddings"]
    if len(vectors) != len(texts):
        raise RuntimeError("Réponse Ollama incohérente")
    return vectors


def build_records():
    """Chunks du corpus selon le chunker réel de l'indexer."""
    records = []
    for path in sorted(CORPUS_DIR.rglob("*.md")):
        rel = path.relative_to(CORPUS_DIR)
        text = path.read_text(encoding="utf-8")
        for index, (start, end, chunk) in enumerate(chunk_file(text, MAX_CHARS)):
            records.append({
                "id": f"{rel.as_posix()}::{index}",
                "document": chunk,
                "metadata": {
                    "source": rel.as_posix(),
                    "category": category_for(rel),
                    "chunk_index": index,
                    "line_start": start,
                    "line_end": end,
                },
            })
    return records


def run_model(client, model, records, queries):
    print(f"\n=== Modèle : {model['name']} "
          f"(collection '{model['collection']}') ===")

    # Collection dédiée : destruction puis recréation propre.
    try:
        client.delete_collection(model["collection"])
        print(f"[chroma] collection '{model['collection']}' détruite")
    except Exception:
        pass
    collection = client.create_collection(
        name=model["collection"],
        metadata={"benchmark": "true", "embedding_model": model["name"]},
    )

    # Indexation (préfixes documents inclus).
    t0 = time.perf_counter()
    dims = None
    for offset in range(0, len(records), BATCH_SIZE):
        batch = records[offset:offset + BATCH_SIZE]
        vectors = embed_texts(
            [model["doc_prefix"] + r["document"] for r in batch],
            model["name"],
        )
        if dims is None:
            dims = len(vectors[0])
        collection.upsert(
            ids=[r["id"] for r in batch],
            embeddings=vectors,
            documents=[r["document"] for r in batch],
            metadatas=[r["metadata"] for r in batch],
        )
    corpus_embedding_ms = (time.perf_counter() - t0) * 1000
    print(f"[index] {len(records)} chunks, {dims} dims, "
          f"{corpus_embedding_ms / 1000:.1f}s "
          f"(préfixe doc '{model['doc_prefix'] or 'aucun'}')")

    # Requêtes (préfixes requête inclus).
    per_question = []
    for q in queries:
        expected = q["expected"]

        t0 = time.perf_counter()
        vectors = embed_texts([model["query_prefix"] + q["question"]],
                              model["name"])
        embedding_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        res = collection.query(
            query_embeddings=vectors,
            n_results=TOP_K,
            include=["documents", "metadatas", "distances"],
        )
        query_ms = (time.perf_counter() - t0) * 1000

        ids = res["ids"][0]
        distances = res["distances"][0]
        metadatas = res["metadatas"][0]

        def recall(k):
            return len([e for e in expected if e in ids[:k]]) / len(expected)

        per_question.append({
            "id": q["id"],
            "topic": q["topic"],
            "query": q["question"],
            "model": model["name"],
            "top_k_results": [
                {
                    "id": doc_id,
                    "distance": round(distance, 6),
                    "category": meta["category"],
                    "preview": " ".join(doc.split())[:80],
                }
                for doc_id, distance, meta, doc
                in zip(ids, distances, metadatas, res["documents"][0])
            ],
            "expected": expected,
            "hits": [e for e in expected if e in ids],
            "recall@1": recall(1),
            "recall@3": recall(3),
            "recall@5": recall(5),
            "top1_distance": round(distances[0], 6),
            "embedding_ms": round(embedding_ms, 1),
            "query_ms": round(query_ms, 1),
        })

    # Nettoyage : les collections de benchmark ne sont pas conservées.
    client.delete_collection(model["collection"])

    count = len(per_question)
    summary = {
        "model": model["name"],
        "collection": model["collection"],
        "doc_prefix": model["doc_prefix"],
        "query_prefix": model["query_prefix"],
        "chunks": len(records),
        "dims": dims,
        "corpus_embedding_ms": round(corpus_embedding_ms, 1),
        "total_query_ms": round(
            sum(p["query_ms"] for p in per_question), 1),
        "mean_top1_distance": round(
            sum(p["top1_distance"] for p in per_question) / count, 6),
        "recall@1": round(
            sum(p["recall@1"] for p in per_question) / count, 4),
        "recall@3": round(
            sum(p["recall@3"] for p in per_question) / count, 4),
        "recall@5": round(
            sum(p["recall@5"] for p in per_question) / count, 4),
        "per_question": per_question,
    }
    return summary


def main():
    queries = load_queries()
    records = build_records()
    print(f"[bench] corpus : {len(records)} chunks, "
          f"{len(queries)} questions")

    # Cohérence de la vérité terrain : tout chunk attendu doit exister
    # dans le découpage actuel du corpus.
    all_ids = {r["id"] for r in records}
    for q in queries:
        for expected_id in q["expected"]:
            if expected_id not in all_ids:
                sys.exit(f"Vérité terrain incohérente : '{expected_id}' "
                         f"attendu par {q['id']} mais absent du découpage "
                         f"du corpus — régénérer chunk_layout.py et "
                         f"corriger queries.jsonl")

    client = chromadb.HttpClient(host=CHROMA_HOST, port=int(CHROMA_PORT))

    summaries = []
    for model in MODELS:
        summaries.append(run_model(client, model, records, queries))

    # Tableau comparatif
    print("\n" + "=" * 74)
    print(f"{'Modèle':<18} {'R@1':>6} {'R@3':>6} {'R@5':>6} "
          f"{'top-1':>8} {'embed(s)':>9} {'requêtes(ms)':>13}")
    print("-" * 74)
    for s in summaries:
        print(f"{s['model']:<18} {s['recall@1']:>6.3f} {s['recall@3']:>6.3f} "
              f"{s['recall@5']:>6.3f} {s['mean_top1_distance']:>8.3f} "
              f"{s['corpus_embedding_ms'] / 1000:>9.1f} "
              f"{s['total_query_ms']:>13.0f}")
    print("=" * 74)

    # Fichiers résultats : horodaté + latest
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    payload = {
        "timestamp": stamp,
        "corpus_chunks": len(records),
        "questions": len(queries),
        "top_k": TOP_K,
        "note": ("Recall@k mesure la proportion de chunks attendus présents "
                 "dans le top-k : c'est le rappel des chunks pertinents, "
                 "pas la capacité à récupérer une réponse complète. Pour "
                 "une question à N chunks attendus, un top-1 ne peut au "
                 "mieux atteindre 1/N."),
        "models": summaries,
    }
    raw = json.dumps(payload, ensure_ascii=False, indent=2)
    (RESULTS_DIR / f"benchmark-{stamp}.json").write_text(raw, encoding="utf-8")
    (RESULTS_DIR / "latest.json").write_text(raw, encoding="utf-8")
    print(f"\n[done] résultats : results/benchmark-{stamp}.json "
          f"et results/latest.json")


if __name__ == "__main__":
    main()