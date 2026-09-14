# Architecture de la mémoire vectorielle du projet

## Vue d'ensemble et objectifs

La stack fournit une mémoire vectorielle persistante et entièrement locale à
l'agent de Zed. Elle repose sur ChromaDB comme stockage de vecteurs, sur le
protocole Model Context Protocol comme interface d'outils, et sur Docker
Compose comme orchestrateur. Aucune donnée ne quitte la machine : les
requêtes de l'agent, les embeddings et le stockage restent locaux.

L'architecture sépare strictement deux plans. Le plan de contrôle gère la
consultation : l'agent Zed interroge la base via les outils Chroma exposés
sur MCP. Le plan d'ingestion gère l'écriture : un indexeur batch transforme
les documents stockés dans Git en vecteurs. Aucun des deux plans n'empiète
sur l'autre.

Cette découpe a une conséquence directe : l'agent ne peut pas casser
l'indexation, et l'indexeur n'interfère pas avec les conversations de
l'agent. Les écritures massives passent par l'indexeur, les lectures passent
par le MCP, et Chroma arbitre les deux.

## Le flux de requête, de l'agent jusqu'à la base

Une requête de l'agent traverse cinq maillons. Zed se connecte en Streamable
HTTP au endpoint du proxy sur le port 8080. Le proxy relaie le protocole sur
stdio vers le processus chroma-mcp. Celui-ci exécute l'outil demandé, par
exemple une requête sémantique.

Pour une requête sémantique, chroma-mcp calcule d'abord l'embedding du texte
de recherche avec le modèle configuré sur la collection, puis envoie le
vecteur au serveur ChromaDB. Le serveur compare ce vecteur à l'index HNSW et
retourne les chunks les plus proches avec leurs métadonnées. La réponse
remonte enfin la chaîne jusqu'à l'agent.

Chaque maillon a été validé individuellement : les transports, la négociation
de protocole, l'embedding des requêtes et la recherche approximative. Le
test de bout en bout rejoue l'ensemble dans les deux transports et sert de
garde-fou après toute modification de la stack.

## Le flux d'ingestion, des documents vers les vecteurs

L'ingestion commence toujours par le dépôt Git : les documents sources
vivent dans le dépôt, jamais dans Chroma, qui n'est qu'un cache de recherche
reconstruisible. L'indexeur parcourt le corpus, découpe chaque fichier en
chunks en respectant les paragraphes, et calcule un hash du fichier complet.

Les chunks sont ensuite embeddés par lot par Ollama, puis écrits dans la
collection par un upsert aux identifiants déterministes. Les métadonnées de
chaque chunk conservent le chemin relatif, la catégorie, le hash du fichier,
l'index du chunk et les bornes de lignes, ce qui permet de retrouver le
passage original dans le dépôt.

L'incrémental rend l'opération quotidienne : les fichiers inchangés sont
ignorés en comparant leur hash, les fichiers modifiés sont redécoupés et
réembeddés, les fichiers supprimés du corpus entraînent la purge de leurs
chunks.

## Le découplage des modèles

Le modèle de langage utilisé par l'agent et le modèle d'embedding utilisé
par l'indexeur sont volontairement indépendants. Changer de modèle de
langage ne provoque aucune réindexation, car les vecteurs ne dépendent que
du modèle d'embedding. Inversement, changer de modèle d'embedding impose
une reconstruction complète de la collection, les dimensions des vecteurs
devant rester homogènes.

Ce découplage permet de faire évoluer la conversation sans toucher à la
mémoire, et la mémoire sans interrompre la conversation. C'est la condition
de la maintenabilité à long terme de la base.

Le conteneur du proxy héberge enfin deux environnements Python étanches :
le système porte le proxy et une version récente du SDK MCP, le venv dédié
porte chroma-mcp et une version ancienne verrouillée. La frontière est le
protocole stdio, jamais l'API Python, et les détails de ce conflit font
l'objet du document dédié aux versions.