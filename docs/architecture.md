# Architecture de la stack Chroma

## Vue d'ensemble

Cette infrastructure fournit une mémoire vectorielle persistante à l'agent de
Zed, sans dépendance à un service cloud. Tous les composants tournent
localement, orchestrés par Docker Compose, et les connaissances sont stockées
dans ChromaDB, une base vectorielle open source.

Le projet suit une séparation stricte entre deux plans : le plan de contrôle,
où l'agent Zed consulte la base via les outils Chroma exposés par le protocole
Model Context Protocol ; et le plan d'ingestion, où un indexeur batch
transforme les documents Git en vecteurs, indépendamment de l'agent.

## Flux de requête : de l'agent vers les connaissances

L'agent de Zed dialogue avec la base via un serveur MCP distant. Zed se
connecte en Streamable HTTP à l'endpoint http://localhost:8080/mcp. Le
mcp-proxy reçoit les requêtes MCP et relaie le protocole sur stdio vers
chroma-mcp, qui exécute les outils Chroma : collections, documents,
requêtes sémantiques.

chroma-mcp se connecte au serveur ChromaDB en HTTP sur le port 8000. Les
données persistent dans le fichier data/chroma.sqlite3 monté depuis l'hôte,
ce qui garantit que la base survit aux recréations de conteneurs.

## Flux d'ingestion : des documents vers les vecteurs

L'indexeur Dockerisé est le seul mécanisme d'écriture massive. Les documents
sources vivent dans Git, jamais dans Chroma : la base n'est qu'un cache de
recherche. L'indexer découpe chaque fichier en chunks en conservant le
chemin relatif, la catégorie, le hash SHA-256 du fichier, l'index du chunk
et les bornes de lignes.

Les embeddings sont calculés par Ollama avec le modèle bge-m3, choisi pour
sa qualité multilingue en français. Ce modèle d'embedding est totalement
indépendant du modèle LLM utilisé par Zed : changer de LLM ne provoque
aucune réindexation de la base.

## Isolation des environnements Python

Un seul conteneur héberge deux environnements Python étanches. Le proxy
utilise le SDK MCP 1.27.x tandis que chroma-mcp est verrouillé sur MCP 1.6.0.
La frontière entre les deux mondes est le protocole stdio, jamais l'API
Python : aucune version ne peut contaminer l'autre.

## Réseau et persistance

Les services partagent le réseau Docker chroma-net, géré par Compose. Le DNS
interne résout le nom chroma pour tous les conteneurs du réseau, et aucune
commande manuelle n'est nécessaire pour reconstruire la stack après un
arrêt complet.