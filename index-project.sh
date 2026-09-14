#!/usr/bin/env bash
#
# index-project.sh — instanciation RAG d'un projet sur le hub.
#
# Trois responsabilités, dans cet ordre (docs/specs/multi-projets-suivi.md) :
#   1. Identité     : manifeste .rag.yaml — le slug n'y est jamais recalculé
#                    une fois le manifeste créé ; refus déterministe des
#                    collisions de slug entre chemins ;
#   2. Préparation  : docs/ exigé, memory/ optionnel, insertion idempotente
#                    de la section de routage AGENTS.md depuis le gabarit ;
#   3. Indexation   : docker run des indexeurs du hub, réseau chroma-net.
#
# Registre machine-local : .rag-projects.list (slug <TAB> chemin canonique),
# hors Git. Toute invocation invalide échoue AVANT toute écriture : aucun
# manifeste créé, aucun AGENTS.md modifié, aucune collection.
#
# Usage :
#   ./index-project.sh /chemin/du/projet

set -euo pipefail

HUB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGISTRY_FILE="${HUB_DIR}/.rag-projects.list"
TEMPLATE_FILE="${HUB_DIR}/templates/AGENTS-rag-section.md"
IMAGE="local/chroma-indexer:latest"
NETWORK="chroma-net"
SECTION_MARKER="## RAG local"

usage() {
    cat >&2 <<'USAGE'
Usage : index-project.sh /chemin/du/projet

Instancie ou met à jour les collections RAG du projet sur le hub :
  <slug>__knowledge   indexée depuis docs/ du projet
  <slug>__memories    indexée depuis memory/ du projet (optionnel)
USAGE
    exit 1
}

fail() {
    echo "ERREUR : $1" >&2
    exit 1
}

# --- Slug ----------------------------------------------------------------

slug_valid() {
    # Bornes alphanumériques, [a-z0-9_-], 3 à 63 caractères (contraintes Chroma).
    local s="$1"
    [[ "$s" =~ ^[a-z0-9][a-z0-9_-]*[a-z0-9]$ ]] \
        && [ "${#s}" -ge 3 ] && [ "${#s}" -le 63 ]
}

slug_from_folder() {
    # Minuscules, accents translittérés, caractères valides uniquement,
    # tirets répétés condensés, bornes alphanumériques.
    local s
    s="$(basename "$1" | tr '[:upper:]' '[:lower:]')"
    s="$(printf '%s' "$s" | iconv -f UTF-8 -t 'ASCII//TRANSLIT')"
    s="$(printf '%s' "$s" | tr -c 'a-z0-9_-' '-')"
    s="$(printf '%s' "$s" | sed -e 's/--*/-/g' -e 's/^[-_]*//' -e 's/[-_]*$//')"
    printf '%s' "$s"
}

canonical_slug() {
    # Slug déterministe dérivé du chemin canonique : slug--<hash court>.
    local hash
    hash="$(printf '%s' "$1" | shasum -a 256 | cut -c1-6)"
    printf '%s--%s' "$2" "$hash"
}

# --- Registre machine-local ----------------------------------------------

registry_lookup() {
    # Chemin enregistré pour ce slug, vide si aucun.
    [ -f "$REGISTRY_FILE" ] || return 0
    awk -F'\t' -v s="$1" '$1 == s { print $2; exit }' "$REGISTRY_FILE"
}

registry_upsert() {
    local slug="$1" path="$2" tmp="${REGISTRY_FILE}.tmp"
    if [ -f "$REGISTRY_FILE" ]; then
        awk -F'\t' -v s="$slug" -v p="$path" '
            BEGIN { OFS = "\t" }
            $1 == s { print s, p; found = 1; next }
            { print }
            END { if (!found) print s, p }
        ' "$REGISTRY_FILE" > "$tmp"
    else
        printf '%s\t%s\n' "$slug" "$path" > "$tmp"
    fi
    mv "$tmp" "$REGISTRY_FILE"
}

# --- État des collections (lecture seule) --------------------------------

collections_state() {
    docker run --rm -i --network "$NETWORK" --entrypoint python \
        -e COL_K="$1" -e COL_M="$2" "$IMAGE" - <<'PY'
import os
import chromadb

client = chromadb.HttpClient(host="chroma", port=8000)
for name in (os.environ.get("COL_K", ""), os.environ.get("COL_M", "")):
    if not name:
        continue
    try:
        col = client.get_collection(name)
        print(f"    {name} : existante, {col.count()} entree(s)")
    except Exception:
        print(f"    {name} : a creer")
PY
}

# --- Déroulement ----------------------------------------------------------

main() {
    [ "$#" -eq 1 ] || usage
    target="$1"
    [ -d "$target" ] || fail "chemin inexistant ou non dossier : $target"
    root="$(cd "$target" && pwd -P)"

    echo "Projet        : $(basename "$root")"
    echo "Chemin        : $root"

    # ---------- 1. Identité ----------
    manifest="$root/.rag.yaml"
    if [ -f "$manifest" ]; then
        slug="$(sed -n 's/^[[:space:]]*slug:[[:space:]]*//p' "$manifest" | head -n 1)"
        [ -n "$slug" ] || fail "manifeste .rag.yaml sans champ slug exploitable"
        slug_valid "$slug" \
            || fail "slug du manifeste syntaxiquement invalide : $slug"
        echo "Slug          : $slug (le manifeste fait foi)"
    else
        slug="$(slug_from_folder "$root")"
        slug_valid "$slug" \
            || fail "nom de dossier non convertible en slug valide : $(basename "$root")"
        echo "Slug          : $slug (dérivé du dossier)"
    fi

    # Collision : le slug ne doit jamais être associé à un autre chemin
    # vivant. Le manifeste établit la continuité d'identité : un chemin
    # enregistré disparu avec manifeste présent est un renommage, pas
    # une collision.
    registered="$(registry_lookup "$slug")"
    if [ -n "$registered" ] && [ "$registered" != "$root" ]; then
        if [ -d "$registered" ]; then
            # Branche 1 : chemin enregistré vivant — collision réelle.
            proposal="$(canonical_slug "$root" "$slug")"
            if slug_valid "$proposal"; then
                fail "slug « $slug » déjà associé à un autre chemin :
    $registered
Slug déterministe dérivé du chemin canonique : $proposal
(ajustez le manifeste .rag.yaml du projet à instancier avec ce slug)"
            else
                fail "slug « $slug » déjà associé à un autre chemin :
    $registered
(et le slug canonique dépasserait la limite de 63 caractères —
renommez le projet ou ajustez son manifeste)"
            fi
        elif [ ! -f "$manifest" ]; then
            # Branche 3 : chemin enregistré disparu, sans manifeste —
            # identité non confirmée, refus prudent.
            fail "slug « $slug » enregistré pour un chemin disparu :
    $registered
et aucun manifeste .rag.yaml ne confirme l'identité — nettoyez le
registre du hub ou utilisez le slug canonique"
        fi
        # Branche 2 : chemin enregistré disparu + manifeste présent —
        # renommage du même projet, le manifeste fait foi : on procède,
        # la mise à jour du registre suivra le nouveau chemin canonique.
        echo "Registre      : renommage détecté (ancien : $registered)"
        echo "                le manifeste fait foi, le registre suivra le nouveau chemin"
    fi

    # ---------- 2. Préparation ----------
    docs_dir="$root/docs"
    memory_dir="$root/memory"
    [ -d "$docs_dir" ] || fail "dossier docs/ introuvable dans $root (requis)"
    if [ -d "$memory_dir" ]; then
        echo "docs/         : trouvé"
        echo "memory/       : trouvé"
    else
        echo "docs/         : trouvé"
        echo "memory/       : absent — mémoires ignorées"
    fi

    knowledge="${slug}__knowledge"
    memories_col="${slug}__memories"
    echo "Knowledge     : $knowledge"
    echo "Memories      : $memories_col"
    echo "Embedding     : bge-m3 / 1024d"

    [ -f "$TEMPLATE_FILE" ] \
        || fail "gabarit introuvable : $TEMPLATE_FILE (attendu à la racine du hub)"

    echo "Collections   :"
    collections_state "$knowledge" "$([ -d "$memory_dir" ] && echo "$memories_col" || echo "")"

    # Écritures — uniquement après toutes les validations ci-dessus.
    agents_file="$root/AGENTS.md"
    if [ -f "$agents_file" ] && grep -qF -- "$SECTION_MARKER" "$agents_file"; then
        echo "AGENTS.md     : section RAG déjà présente"
    else
        if [ -f "$agents_file" ]; then
            # Normalisation minimale : si le fichier existant est non
            # vide, garantir un saut de ligne final puis une ligne
            # vide de séparation — sans toucher au reste de la mise
            # en forme.
            if [ -s "$agents_file" ]; then
                if [ -n "$(tail -c 1 "$agents_file")" ]; then
                    echo >> "$agents_file"
                fi
                echo "" >> "$agents_file"
            fi
            sed "s/{{SLUG}}/$slug/g" "$TEMPLATE_FILE" >> "$agents_file"
        else
            sed "s/{{SLUG}}/$slug/g" "$TEMPLATE_FILE" > "$agents_file"
        fi
        echo "AGENTS.md     : section RAG insérée"
    fi

    if [ ! -f "$manifest" ]; then
        cat > "$manifest" <<EOF
project:
  manifest_version: 1
  slug: $slug
EOF
        echo "Manifeste     : .rag.yaml créé"
    fi
    registry_upsert "$slug" "$root"

    # ---------- 3. Indexation ----------
    echo "→ indexation knowledge ($knowledge)"
    docker run --rm --network "$NETWORK" \
        -v "$docs_dir:/docs:ro" -e COLLECTION="$knowledge" "$IMAGE"

    if [ -d "$memory_dir" ]; then
        echo "→ indexation memories ($memories_col)"
        docker run --rm --network "$NETWORK" \
            -v "$memory_dir:/memory:ro" -e COLLECTION="$memories_col" \
            --entrypoint python "$IMAGE" memory_indexer.py
    fi

    echo "✓ projet indexé : $slug"
}

main "$@"