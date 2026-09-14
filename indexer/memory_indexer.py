#!/usr/bin/env python3
"""Indexer des mémoires : memory/*.md -> entrées atomiques -> Chroma.

Variante de l'indexer principal (docs/ -> chunks), pour la collection
memories. Différences fondamentales :

    - une entrée = un fait ou une préférence indépendant : pas de chunking ;
    - les entrées sont délimitées par des titres '## <memory_id>' ;
    - created_at / updated_at se lisent dans des commentaires HTML
      <!-- created: AAAA-MM-JJ --> / <!-- updated: AAAA-MM-JJ -->,
      invisibles à la lecture du Markdown ;
    - la catégorie du fichier se déclare par <!-- category: ... --> en tête
      de fichier (défaut : nom du fichier, tirets remplacés par _) ;
    - même mécanique d'idempotence que l'indexer principal : hash de
      fichier, upsert aux IDs déterministes, purge des entrées supprimées
      ou devenues orphelines.

Les fichiers mémoire sont la source de vérité ; ils ne sont jamais mélangés
au corpus docs/ de project_knowledge.

Usage :
    docker compose run --rm memory-indexer
"""

import os
import re
import sys
import time
from pathlib import Path

import chromadb

from indexer import (  # noqa: E402  (baké dans l'image au même endroit)
    BATCH_SIZE,
    CHROMA_HOST,
    CHROMA_PORT,
    CreateCollectionConfiguration,
    EMBED_MODEL,
    OLLAMA_URL,
    OllamaEmbeddingFunction,
    embed_texts,
    fetch_existing_by_source,
    sha256_bytes,
)

MEMORY_DIR = Path(os.environ.get("MEMORY_DIR", "/memory"))
COLLECTION = os.environ.get("COLLECTION", "memories")
RESET = os.environ.get("RESET", "false").lower() in ("1", "true", "yes")

COMMENT_RE = re.compile(r"<!--\s*(created|updated|category)\s*:\s*(.+?)\s*-->")


def parse_memory_file(text):
    """Découpe un fichier mémoire en entrées atomiques.

    Format :

        <!-- category: preference -->       <- en-tête de fichier (optionnel)
        # Titre                             <- ignoré (hors des entrées)
        ## preferences::001                 <- début d'entrée : memory_id
        <!-- created: 2026-09-04 -->        <- métadonnées (optionnelles)
        <!-- updated: 2026-09-05 -->
        Texte de l'entrée, jusqu'au titre suivant.

    Retourne (category, [ {memory_id, created, updated, content} ]).
    """
    file_category = None
    entries = []
    current = None

    def close():
        nonlocal current
        if current is not None:
            content = "\n".join(current.pop("lines")).strip()
            if content:
                current["content"] = content
                entries.append(current)
            current = None

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if raw_line.startswith("## "):
            close()
            current = {"memory_id": raw_line[3:].strip(), "lines": [],
                       "created": "", "updated": ""}
            continue

        if line.startswith("<!--") and line.endswith("-->"):
            match = COMMENT_RE.fullmatch(line)
            if match:
                key, value = match.group(1), match.group(2)
                if current is None and key == "category":
                    file_category = value
                elif current is not None:
                    current[key] = value
            continue

        if current is not None:
            current["lines"].append(raw_line)

    close()
    return file_category, entries


def main():
    started = time.time()
    if not MEMORY_DIR.is_dir():
        sys.exit(f"MEMORY_DIR introuvable : {MEMORY_DIR}")

    files = sorted(
        p for p in MEMORY_DIR.rglob("*.md")
        if p.is_file()
        and not any(part.startswith(".")
                    for part in p.relative_to(MEMORY_DIR).parts)
    )
    if not files:
        sys.exit(f"Aucun fichier .md dans {MEMORY_DIR}")
    print(f"[scan] {len(files)} fichier(s) mémoire dans {MEMORY_DIR}")

    client = chromadb.HttpClient(host=CHROMA_HOST, port=int(CHROMA_PORT))

    if RESET:
        try:
            client.delete_collection(COLLECTION)
            print(f"[reset] collection '{COLLECTION}' supprimée")
        except Exception:
            print(f"[reset] collection '{COLLECTION}' absente, rien à supprimer")

    try:
        collection = client.get_collection(COLLECTION)
        print(f"[chroma] collection existante réutilisée : '{COLLECTION}'")
    except Exception:
        embedding_function = OllamaEmbeddingFunction(
            url=OLLAMA_URL, model_name=EMBED_MODEL
        )
        collection = client.create_collection(
            name=COLLECTION,
            configuration=CreateCollectionConfiguration(
                embedding_function=embedding_function
            ),
            metadata={
                "description": "Mémoires persistantes : préférences, "
                               "conventions, contexte durable",
                "categories": "preference,convention,durable_context,decision",
                "embedding_provider": "ollama",
                "embedding_model": EMBED_MODEL,
            },
        )
        print(f"[chroma] collection '{COLLECTION}' créée "
              f"(EF ollama/{EMBED_MODEL})")

    existing = {} if RESET else fetch_existing_by_source(collection)

    corpus_sources = set()
    unchanged, new_files, updated_files, deleted_files = [], [], [], []
    to_upsert, to_delete_ids = [], []

    for path in files:
        rel = path.relative_to(MEMORY_DIR)
        source = rel.as_posix()
        corpus_sources.add(source)
        raw = path.read_bytes()
        file_hash = sha256_bytes(raw)
        entry = existing.get(source)

        if entry and entry["hash"] == file_hash:
            unchanged.append(source)
            continue

        file_category, mem_entries = parse_memory_file(
            raw.decode("utf-8", errors="replace")
        )

        if file_category is None:
            # Fichier sans catégorie déclarée : ce n'est pas un fichier
            # mémoire (ex. README). S'il était indexé par le passé, on
            # purge toutes ses entrées.
            if entry:
                to_delete_ids.extend(entry["ids"])
                print(f"[purge] {source} : pas de catégorie déclarée, "
                      f"{len(entry['ids'])} entrée(s) retirée(s)")
            else:
                print(f"[skip] {source} : pas de catégorie déclarée "
                      f"(fichier documentation ?)")
            continue

        category = file_category
        records = [
            {
                "id": f"{source}::{mem['memory_id']}",
                "document": mem["content"],
                "metadata": {
                    "source": source,
                    "category": category,
                    "content_hash": file_hash,
                    "memory_id": mem["memory_id"],
                    "created_at": mem["created"],
                    "updated_at": mem["updated"],
                },
            }
            for mem in mem_entries
        ]

        if not records and not entry:
            print(f"[skip] {source} : aucune entrée")
            continue

        if entry:
            # Fichier modifié : réécriture des entrées + purge des
            # entrées supprimées du fichier (logique orphelins).
            updated_files.append(source)
            to_delete_ids.extend(entry["ids"] - {r["id"] for r in records})
        else:
            new_files.append(source)
        to_upsert.extend(records)
        print(f"[memo] {source} -> {len(records)} entrée(s), "
              f"catégorie '{category}'")

    # Fichiers supprimés du corpus mais encore en base.
    for source, entry in existing.items():
        if source not in corpus_sources:
            deleted_files.append(source)
            to_delete_ids.extend(entry["ids"])

    for i in range(0, len(to_delete_ids), BATCH_SIZE):
        collection.delete(ids=to_delete_ids[i:i + BATCH_SIZE])

    dims = None
    for offset in range(0, len(to_upsert), BATCH_SIZE):
        batch = to_upsert[offset:offset + BATCH_SIZE]
        vectors = embed_texts(
            [r["document"] for r in batch], EMBED_MODEL, OLLAMA_URL
        )
        if dims is None:
            dims = len(vectors[0])
        collection.upsert(
            ids=[r["id"] for r in batch],
            embeddings=vectors,
            documents=[r["document"] for r in batch],
            metadatas=[r["metadata"] for r in batch],
        )

    print(f"[diff] inchangés={len(unchanged)} nouveaux={len(new_files)} "
          f"modifiés={len(updated_files)} supprimés={len(deleted_files)}")
    dims_msg = f"{dims} dimensions, " if dims else ""
    print(f"[done] {len(to_upsert)} entrée(s) écrite(s), "
          f"{len(to_delete_ids)} supprimée(s), {dims_msg}"
          f"collection '{COLLECTION}' à {collection.count()} entrées, "
          f"{time.time() - started:.1f}s")


if __name__ == "__main__":
    main()