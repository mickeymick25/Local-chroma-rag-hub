# Spécification de l'indexer

## Contrat de données

Chaque chunk inséré dans la collection project_knowledge porte les
métadonnées suivantes : source, le chemin relatif du fichier dans le
corpus ; category, la catégorie dérivée du premier sous-dossier, sinon du
nom du fichier ; content_hash, le SHA-256 du fichier source complet au
format sha256 hexadécimal ; chunk_index, la position du chunk dans le
fichier en numérotation partant de zéro ; et les bornes de lignes
line_start et line_end, en numérotation un-based inclusive.

Les identifiants sont déterministes : source suivi du séparateur double
deux-points et du chunk_index. Un upsert rend donc chaque exécution
idempotente : relancer l'indexer ne duplique jamais les chunks.

## Pipeline

L'indexer parcourt récursivement le répertoire monté, retient les fichiers
markdown et texte, et ignore les fichiers cachés. Chaque fichier est
découpé en chunks par regroupement de paragraphes, avec une cible de mille
deux cents caractères par chunk.

Les embeddings sont calculés par lot via l'API Ollama sur le point d'accès
api/embed, puis écrits dans Chroma via un upsert qui transporte les
identifiants, les vecteurs, les documents et les métadonnées.

## Configuration

Les variables d'environnement pilotent tout le comportement : DOCS_DIR pour
le répertoire du corpus, EMBED_MODEL pour le modèle d'embedding Ollama,
COLLECTION pour la collection cible, CHROMA_HOST et CHROMA_PORT pour le
serveur de base, OLLAMA_URL pour le service d'embedding.

La variable RESET supprime et recrée la collection : elle est obligatoire
après un changement de modèle d'embedding, car les dimensions des vecteurs
doivent rester homogènes au sein d'une collection. Passer de bge-m3 en mille
vingt-quatre dimensions à un autre modèle impose donc une reconstruction.

## Exécution

Une réindexation complète se lance par docker compose run --rm indexer.
Après un changement de modèle d'embedding, on ajoute l'option RESET à
vrai pour reconstruire la collection depuis zéro.

## Indexation incrémentale

L'indexer est incrémental : le hash SHA-256 de chaque fichier est comparé
au content_hash stocké dans les métadonnées de la collection. Un fichier
inchangé est ignoré sans aucun calcul ni embedding. Un fichier modifié est
redécoupé et réembeddé, et les chunks devenus obsolètes sont supprimés,
y compris lorsqu'une réduction du nombre de chunks laisse des identifiants
orphelins. Un fichier supprimé du corpus entraîne la suppression de tous
ses chunks. Une exécution sans changement n'écrit donc rien et coûte
moins d'une seconde.

## Évolutions prévues

Un benchmark Recall@k entre modèles d'embedding Ollama sera mené sur un
corpus français représentatif avant de figer le choix du modèle définitif.