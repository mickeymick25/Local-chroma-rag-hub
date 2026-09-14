#!/usr/bin/env python3
"""Indexer : documents -> chunking -> embeddings Ollama -> Chroma.

Plan d'ingestion de la stack (voir docs/specs/indexer.md) :

    documents Git (/docs)
        │  chemin relatif, catégorie, hash SHA-256, chunk_index, lignes
        ▼
    chunks ──> embeddings Ollama (/api/embed) ──> Chroma (upsert)

Indexation incrémentale :
    - content_hash identique  -> fichier ignoré (aucun calcul, aucun embedding) ;
    - fichier modifié         -> re-chunk + re-embed, et suppression des
                                 chunks devenus obsolètes (réduction du
                                 nombre de chunks) ;
    - fichier supprimé        -> tous ses chunks sont retirés de la base.

Idempotent : IDs déterministes "<source>::<chunk_index>".
"""

import hashlib
import os
import sys
import time
from pathlib import Path

import chromadb
import requests
from chromadb.api.collection_configuration import CreateCollectionConfiguration
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

# --- Configuration (environnement) ---
DOCS_DIR = Path(os.environ.get("DOCS_DIR", "/docs"))
CHROMA_HOST = os.environ.get("CHROMA_HOST", "chroma")
CHROMA_PORT = os.environ.get("CHROMA_PORT", "8000")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "bge-m3")
COLLECTION = os.environ.get("COLLECTION", "project_knowledge")
RESET = os.environ.get("RESET", "false").lower() in ("1", "true", "yes")
MAX_CHARS = int(os.environ.get("MAX_CHARS", "1200"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "16"))
EXTENSIONS = {".md", ".txt"}


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def category_for(rel_path: Path) -> str:
    """Catégorie : premier sous-dossier, sinon le nom du fichier.

    docs/specs/api.md -> "specs" ; docs/architecture.md -> "architecture".
    """
    parts = rel_path.parts
    return parts[0] if len(parts) >= 2 else rel_path.stem


def chunk_file(text: str, max_chars: int):
    """Découpe un texte en chunks (paragraphes regroupés, <= max_chars).

    Retourne [(line_start, line_end, chunk_text)], lignes 1-based inclusives.
    """
    lines = text.splitlines()
    n = len(lines)
    chunks, buf = [], []

    def flush():
        if buf:
            chunks.append((buf[0][0], buf[-1][0], "\n".join(l for _, l in buf)))
            buf.clear()

    i = 0
    while i < n:
        if not lines[i].strip():
            i += 1
            continue
        j = i
        while j < n and lines[j].strip():
            j += 1
        para = lines[i:j]
        para_len = sum(len(l) + 1 for l in para)

        if para_len > max_chars:
            # Paragraphe trop long : chunks dédiés, coupés par lignes.
            flush()
            for k, line in enumerate(para):
                cur_len = sum(len(l) + 1 for _, l in buf)
                if buf and cur_len + len(line) + 1 > max_chars:
                    flush()
                buf.append((i + 1 + k, line))
            flush()
        else:
            cur_len = sum(len(l) + 1 for _, l in buf)
            if buf and cur_len + para_len > max_chars:
                flush()
            for k, line in enumerate(para):
                buf.append((i + 1 + k, line))
        i = j

    flush()
    return chunks


def embed_texts(texts, model, url):
    """Embeddings par lot via l'API Ollama. Retourne une liste de vecteurs."""
    resp = requests.post(
        f"{url}/api/embed",
        json={"model": model, "input": texts},
        timeout=300,
    )
    resp.raise_for_status()
    data = resp.json()
    vectors = data.get("embeddings")
    if not vectors or len(vectors) != len(texts):
        raise RuntimeError(f"Réponse Ollama inattendue : {data}")
    return vectors


def scan_files():
    return sorted(
        p for p in DOCS_DIR.rglob("*")
        if p.is_file()
        and p.suffix.lower() in EXTENSIONS
        and not any(part.startswith(".")
                    for part in p.relative_to(DOCS_DIR).parts)
    )


def fetch_existing_by_source(collection):
    """Cartographie l'état courant de la collection : source -> {hash, ids}."""
    existing = {}
    if collection.count() == 0:
        return existing
    result = collection.get(include=["metadatas"])
    for doc_id, meta in zip(result["ids"], result["metadatas"]):
        entry = existing.setdefault(meta["source"], {"hash": None, "ids": set()})
        entry["ids"].add(doc_id)
        if entry["hash"] is None:
            entry["hash"] = meta.get("content_hash")
    return existing


def main():
    started = time.time()
    if not DOCS_DIR.is_dir():
        sys.exit(f"DOCS_DIR introuvable : {DOCS_DIR}")

    files = scan_files()
    if not files:
        sys.exit(f"Aucun document {'/'.join(sorted(EXTENSIONS))} dans {DOCS_DIR}")
    print(f"[scan] {len(files)} document(s) dans {DOCS_DIR}")

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
                "description": "Connaissances du projet, indexées par l'indexer",
                "categories": "architecture,specs,decisions,documentation",
                "embedding_provider": "ollama",
                "embedding_model": EMBED_MODEL,
            },
        )
        print(f"[chroma] collection '{COLLECTION}' créée (EF ollama/{EMBED_MODEL})")

    # État courant de la base (vide si RESET : tout sera considéré nouveau)
    existing = {} if RESET else fetch_existing_by_source(collection)

    corpus_sources = set()
    unchanged, new_files, updated_files, deleted_files = [], [], [], []
    to_upsert, to_delete_ids = [], []

    # --- Fichiers présents dans le corpus ---
    for path in files:
        rel = path.relative_to(DOCS_DIR)
        source = rel.as_posix()
        corpus_sources.add(source)
        raw = path.read_bytes()
        file_hash = sha256_bytes(raw)
        entry = existing.get(source)

        # Incrémental : hash identique -> rien à faire.
        if entry and entry["hash"] == file_hash:
            unchanged.append(source)
            continue

        chunks = chunk_file(raw.decode("utf-8", errors="replace"), MAX_CHARS)
        records = [
            {
                "id": f"{source}::{index}",
                "document": text,
                "metadata": {
                    "source": source,
                    "category": category_for(rel),
                    "content_hash": file_hash,
                    "chunk_index": index,
                    "line_start": start,
                    "line_end": end,
                },
            }
            for index, (start, end, text) in enumerate(chunks)
        ]

        if not records and not entry:
            print(f"[skip] {source} : aucun contenu")
            continue

        if entry:
            # Fichier modifié : re-chunk + re-embed, et purge des chunks
            # devenus obsolètes (cas d'une réduction du nombre de chunks).
            updated_files.append(source)
            to_delete_ids.extend(entry["ids"] - {r["id"] for r in records})
        else:
            new_files.append(source)
        to_upsert.extend(records)
        print(f"[chunk] {source} -> {len(chunks)} chunk(s), "
              f"catégorie '{category_for(rel)}'")

    # --- Fichiers supprimés du corpus mais encore en base ---
    for source, entry in existing.items():
        if source not in corpus_sources:
            deleted_files.append(source)
            to_delete_ids.extend(entry["ids"])

    # --- Suppressions (par lots) ---
    for i in range(0, len(to_delete_ids), BATCH_SIZE):
        collection.delete(ids=to_delete_ids[i:i + BATCH_SIZE])

    # --- Embeddings + écritures (par lots) ---
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
    print(f"[done] {len(to_upsert)} chunk(s) écrit(s), "
          f"{len(to_delete_ids)} chunk(s) obsolète(s) supprimé(s), "
          f"{dims_msg}collection '{COLLECTION}' à {collection.count()} chunks, "
          f"{time.time() - started:.1f}s")


if __name__ == "__main__":
    main()