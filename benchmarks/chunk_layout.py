"""Affiche le découpage en chunks du corpus de benchmark.

Utilise le chunker réel de l'indexer (baké dans l'image au build) pour
produire la correspondance source::chunk_index <-> lignes, sur laquelle la
vérité terrain de queries.jsonl est figée.

Usage (conteneur indexer, aucune écriture) :

    docker run --rm \
      -v "$PWD/benchmarks:/bench:ro" \
      --entrypoint python local/chroma-indexer:latest \
      /bench/chunk_layout.py /bench/corpus
"""

import sys
from pathlib import Path

sys.path.insert(0, "/app")  # indexer.py est baké dans l'image au build

from indexer import MAX_CHARS, category_for, chunk_file  # noqa: E402

docs = Path(sys.argv[1] if len(sys.argv) > 1 else "/bench/corpus")

total = 0
for path in sorted(docs.rglob("*.md")):
    rel = path.relative_to(docs)
    text = path.read_text(encoding="utf-8")
    chunks = chunk_file(text, MAX_CHARS)
    print(f"\n=== {rel.as_posix()} ({len(chunks)} chunks, "
          f"categorie '{category_for(rel)}')")
    for index, (start, end, chunk) in enumerate(chunks):
        preview = " ".join(chunk.split())[:70]
        print(f"  {rel.as_posix()}::{index}  lignes {start:>3}-{end:<3} "
              f"[{preview}...]")
    total += len(chunks)

print(f"\nTOTAL : {total} chunks (MAX_CHARS={MAX_CHARS})")