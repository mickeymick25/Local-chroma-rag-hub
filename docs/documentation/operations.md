# Runbook d'exploitation de la stack Chroma

## Démarrage et supervision

La stack démarre par docker compose up -d. Les deux services persistants,
chroma et chroma-mcp-proxy, se relancent automatiquement grâce à la
politique de redémarrage unless-stopped. Le service indexer n'est jamais
démarré par défaut : il s'exécute à la demande et se termine.

Les journaux du proxy se consultent par docker compose logs suivi du nom
du service. L'état global s'obtient par docker compose ps.

## Vérifications de santé

Le heartbeat Chroma prouve que la base est vivante : un appel curl sur le
port 8000 à l'adresse api/v2/heartbeat renvoie une charge utile horodatée
en nanosecondes.

L'endpoint SSE du proxy, interrogé par curl en flux continu sur le port
8080 à l'adresse sse, renvoie un événement endpoint contenant l'URL de
session : c'est la preuve que le proxy, chroma-mcp et la base forment une
chaîne opérationnelle.

## Test MCP de bout en bout

Le script e2e_mcp_test.py vérifie les deux transports, SSE et Streamable
HTTP : l'initialisation du protocole, la découverte des outils, puis un
appel réel à l'outil de listage des collections. Il s'exécute dans un
conteneur éphémère attaché au réseau chroma-net, sans rien installer sur
la machine hôte.

## Réindexation du corpus

Une réindexation complète se lance par docker compose run --rm indexer.
Après un changement de modèle d'embedding, les dimensions des vecteurs
deviennent incompatibles : la collection doit être reconstruite avec
l'option RESET à vrai, sinon les requêtes échouent.

## Les mémoires

La collection memories est alimentée par un indexer dédié, strictement
séparé du corpus docs/ : les fichiers de memory/ contiennent des entrées
atomiques, une par fait ou préférence, délimitées par des titres et une
catégorie déclarée en tête de fichier. Sans catégorie déclarée, un
fichier n'est pas indexé. La réindexation se lance par compose run sur le
service memory-indexer, avec la même idempotence par hash que l'indexeur
principal. Toute nouvelle mémoire passe d'abord par une validation
explicite : l'agent propose, l'humain valide, puis l'entrée entre dans le
fichier source.

## Points d'attention

La recréation du conteneur proxy invalide la session MCP de Zed : le client
garde un identifiant de session obsolète et reçoit des erreurs 404. Pour
rétablir la connexion, désactiver puis réactiver le serveur chroma dans les
réglages MCP de Zed, ou redémarrer Zed.

Le modèle d'embedding par défaut de Chroma est mis en cache dans le
conteneur proxy, hors volume : après une recréation du conteneur, le
premier appel d'embedding est lent. L'URL d'Ollama vue depuis les
conteneurs est host.docker.internal sur le port 11434. Enfin, les
sources font foi : tout document indexé doit exister dans Git, Chroma
n'est qu'un cache de recherche reconstruisible à tout moment.