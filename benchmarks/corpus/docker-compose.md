# Orchestration Docker Compose de la stack

## Les trois services

Le fichier compose définit trois services. Le service chroma exécute le
serveur ChromaDB officiel, expose le port 8000 et monte le répertoire de
données de l'hôte. Le service chroma-mcp-proxy construit l'image du proxy à
partir du Dockerfile dédié, expose le port 8080 et se connecte au serveur
de base par son nom réseau.

Le troisième service, l'indexeur, n'est jamais démarré automatiquement :
il appartient au profil tools et s'exécute à la demande par un compose run,
puis se termine. Ce choix évite un processus permanent inutile pour une
tâche ponctuelle.

Les deux services persistants adoptent la politique de redémarrage
unless-stopped : après un redémarrage de la machine hôte, ils reviennent
seuls, sans intervention humaine.

## Le réseau chroma-net

Tous les services partagent le réseau chroma-net, déclaré external dans le
fichier compose. Ce statut signifie que Compose gère les attachements des
services mais pas le cycle de vie du réseau : un compose down ne le
supprime jamais, et il peut exister indépendamment de la stack.

Le DNS interne du réseau résout les noms des services : le nom chroma
désigne la base, le nom chroma-mcp-proxy désigne le serveur MCP. Aucun
service ne connaît d'adresse IP : les conteneurs peuvent changer d'adresse
à chaque recréation sans casser la chaîne.

Historiquement, l'attachement du conteneur de base au réseau était fait par
une commande manuelle de type network connect. Cette pratique a été
abandonnée au profit d'une déclaration explicite dans le compose, après un
incident où la recréation du conteneur perdait silencieusement le
raccordement réseau et faisait tomber la stack.

## Les volumes et la persistance des données

Le service chroma monte le répertoire data de l'hôte vers le répertoire de
travail du conteneur. La base SQLite et les segments vivent donc sur le
disque de la machine hôte, hors de la couche conteneur éphémère. Recréer le
conteneur ne touche pas aux données : seuls le moteur et sa configuration
sont reconstruits.

C'est la garantie centrale de la persistance : le conteneur est jetable,
le répertoire de données ne l'est pas. Sauvegarder la base revient donc à
copier le répertoire data de l'hôte, à chaud ou à froid, sans arrêter la
stack pour une simple copie.

En revanche, ce qui n'est pas monté en volume est perdu à chaque
recréation : c'est le cas notamment du cache du modèle d'embedding par
défaut dans le conteneur du proxy, dont le premier appel est lent après
chaque recréation.

## Les ports exposés et les services externes

Deux ports sont publiés sur la machine hôte. Le port 8000 donne accès
direct à l'API de ChromaDB, utile pour les vérifications de santé comme le
heartbeat et pour les clients directs. Le port 8080 donne accès au serveur
MCP derrière le proxy, utilisé par l'agent de Zed.

L'indexeur ne publie aucun port : il n'écoute rien, il se connecte vers la
base et vers Ollama puis se termine. Le service Ollama lui-même n'est pas
conteneurisé dans cette stack : il tourne sur la machine hôte et est joint
depuis les conteneurs par l'adresse spéciale host.docker.internal sur le
port 11434.