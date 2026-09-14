# Le fonctionnement de l'indexeur

## Le pipeline

L'indexeur parcourt récursivement le répertoire du corpus, retient les
fichiers markdown et texte, ignore les fichiers cachés, et trie les
résultats pour garantir des identifiants stables. Chaque fichier est lu,
son contenu est découpé en chunks, puis les chunks sont embeddés par lot
et écrits dans la collection.

Le découpage respecte la structure du document : les paragraphes sont
regroupés jusqu'à une cible de mille deux cents caractères, sans jamais
couper un paragraphe en deux, sauf si un paragraphe isolé dépasse la
cible, auquel cas il est découpé par lignes. Les bornes de lignes de
chaque chunk sont conservées en métadonnées.

Les embeddings sont calculés par lot auprès du service Ollama par un appel
unique par lot, ce qui réduit le nombre d'allers-retours. Les écritures
dans Chroma utilisent un upsert : identifiants, vecteurs, documents et
métadonnées partent ensemble, par lots.

## Le contrat de métadonnées

Chaque chunk porte cinq métadonnées. Le chemin relatif du fichier source,
avec son extension. La catégorie, dérivée du premier sous-dossier ou du
nom du fichier à la racine. Le hash SHA-256 du fichier complet au format
texte. L'index du chunk dans son fichier, compté à partir de zéro. Les
bornes de lignes, en numérotation partant de un, inclusives.

Les identifiants sont déterministes : le chemin du fichier suivi de
l'index du chunk. Cette règle rend l'indexation idempotente, car relancer
l'indexeur ne duplique jamais rien, et permet de retrouver un chunk à
partir de sa seule mention.

## Le mode incrémental

À chaque exécution, l'indexeur cartographie la collection : pour chaque
fichier source déjà en base, il relève le hash enregistré et la liste des
identifiants de ses chunks. Puis il compare avec le corpus courant. Un
fichier dont le hash est identique est ignoré sans aucun calcul : ni
découpage, ni embedding, ni écriture.

Un fichier modifié est redécoupé et réembeddé intégralement ; ses anciens
identifiants absents du nouveau découpage sont supprimés, ce qui purge les
chunks orphelins quand un fichier rétrécit. Un fichier supprimé du corpus
entraîne la suppression de tous ses chunks en base.

Le coût d'une exécution sans changement est quasi nul : une lecture des
métadonnées, aucune écriture, quelques dixièmes de seconde. Une
exécution complète à froid reste disponible pour les changements de
modèle d'embedding, qui imposent de reconstruire la collection car les
dimensions des vecteurs doivent rester homogènes.