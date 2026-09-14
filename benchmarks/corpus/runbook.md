# Le runbook d'exploitation

## Démarrage et supervision

La stack démarre par la commande compose up en mode détaché. Les deux
services persistants reviennent automatiquement après un redémarrage de la
machine grâce à la politique de redémarrage. L'état global se consulte par
compose ps, les journaux du proxy par compose logs.

L'indexeur ne démarre jamais avec la stack : il s'exécute à la demande par
compose run sur le service du profil tools, traite le corpus, puis se
termine. Son exécution est idempotente et incrémentale.

## Les vérifications de santé

Le heartbeat de la base prouve que le serveur ChromaDB est vivant : un
appel GET sur le port 8000 à l'adresse api/v2/heartbeat renvoie une charge
horodatée en nanosecondes. C'est la première vérification après tout
incident.

L'endpoint SSE du proxy, interrogé par un GET en flux continu sur le port
8080 à l'adresse sse, renvoie un événement endpoint contenant l'URL de
session : c'est la preuve que le proxy, son serveur aval et la base forment
une chaîne opérationnelle complète.

Le test de bout en bout va plus loin : il initialise le protocole, liste
les outils et appelle un outil réel, dans les deux transports, depuis un
conteneur éphémère attaché au réseau interne. Rien n'est installé sur la
machine hôte pour ce test.

## Réindexation du corpus

Une réindexation complète se lance par compose run sur le service indexer.
Grâce au mode incrémental, seuls les fichiers modifiés depuis la dernière
exécution sont redécoupés, réembeddés et réécrits ; les fichiers inchangés
coûtent une simple comparaison de hash, et les fichiers supprimés du corpus
entraînent la purge de leurs chunks.

Après un changement de modèle d'embedding, les dimensions des vecteurs
deviennent incompatibles : la collection doit être reconstruite par
l'option RESET, qui supprime la collection et la recrée avant d'indexer
l'intégralité du corpus. Cette opération est la seule qui coûte un
réembedding complet.

## Les points d'attention connus

La recréation du conteneur proxy invalide la session MCP de l'éditeur :
le client garde un identifiant obsolète et reçoit des erreurs 404. La
récupération se fait en désactivant puis réactivant le serveur dans les
réglages MCP de l'éditeur, ou en redémarrant l'éditeur.

Le cache du modèle d'embedding par défaut vit dans le conteneur proxy, hors
volume : après une recréation, le premier calcul est lent et peut dépasser
le délai d'attente du client. Enfin, l'URL d'Ollama vue depuis les
conteneurs est l'adresse spéciale host.docker.internal sur le port 11434 :
toute configuration qui l'oublie casse silencieusement les requêtes
sémantiques.